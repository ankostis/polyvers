#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Suppress or ignore  exceptions collected in a nested contexts. """

from functools import partial
from typing import Any, Dict, Union, Callable  # noqa: F401 @UnusedImport
from typing import List, Tuple, Optional
import contextlib
import logging

import textwrap as tw

from . import cmdlets
from ._vendor import traitlets as trt
from ._vendor.traitlets.traitlets import (
    List as ListTrait, Type as TypeTrait, Union as UnionTrait, Callable as CallableTrait
)  # @UnresolvedImport
from ._vendor.traitlets.traitlets import Bool, CBool, Unicode, Instance


log = logging.getLogger(__name__)


def _idstr(obj):
    if obj is None:
        return ''
    return ('%x' % id(obj))[-5:]


def _exstr(err):
    if err is None:
        return ''

    exstr = str(err)
    if exstr:
        exstr = "%s: %s" % (type(err).__name__, exstr)
    else:
        exstr = type(err).__name__

    return exstr


class _ErrNode(trt.HasTraits):
    """
    The basic element of a *recursive* "stack" of.

    ::

        node :=   (doing, is_forced, err, [node, ...])

    Cannot store textualized exception in the first place because
    this is only known after all its children have been born (if any),
    or an error has been captured

    :ivar err:
        any collected error on ``__exit__()`` (forced or not).
        Note that any non-collected errors buble-up as normal exceptions,
        until handled by :class:`ErrLog`'s *root* node.
    """
    doing = Unicode(default_value=None, allow_none=True)
    is_forced = Bool(default_value=None, allow_none=True)
    err = Instance(Exception, default_value=None, allow_none=True)
    cnodes = ListTrait()  # eventful=True)
    #cnodes._trait = Instance('polyvers.errlog._ErrNode')

    def new_cnode(self, doing, is_forced):
        assert self.err is None, repr(self)

        child = _ErrNode(doing=doing or '',
                         is_forced=bool(is_forced))
        self.cnodes.append(child)

        return child

    def node_coordinates(self, node):
        ## TODO: FIX node coordinates!
        coords = []
        self._cnode_coords_recurse(node, coords)

        return coords[::-1]

    def _cnode_coords_recurse(self, node, coords: List[int]):
        """
        Append the 1st index of my `cnodes` subtree containing `node`, recursively.

        Indices appended eventually in reverse order.
        """
        if self is node:
            return True

        for i, cn in enumerate(self.cnodes):
            if cn._cnode_coords_recurse(node, coords):
                coords.append(i)

                return True

    def count_error_tree(self) -> Tuple[int, int]:
        """
        :return:
            a 2-tuple(total errors, how many of them are "forced")
        """
        nerrors = nforced = 0
        if self.err:
            nerrors += 1
            if self.is_forced:
                nforced += 1

        for cn in self.cnodes:
            cn_nerrors, cn_nforced = cn.count_error_tree()
            nerrors += cn_nerrors
            nforced += cn_nforced

        return nerrors, nforced

    def _node_repr(self, print_cnodes):
        props = (self.doing, self.is_forced, self.err)
        ## Avoid recursion using `is_empty()`.
        is_empty = all(i is None for i in props) and not self.cnodes
        if is_empty:
            return 'ELN@%s' % _idstr(self)
        fields = []
        if self.doing:
            fields.append('%r' % self.doing)
        if self.is_forced is not None:
            fields.append('F' if self.is_forced else 'NF')
        if self.err:
            fields.append(repr(self.err))
        if self.cnodes:
            if print_cnodes:
                fields.append(repr(self.cnodes))
            else:
                fields.append('+')
        return 'ELN<%s>@%s' % (', '.join(fields), _idstr(self))

    def __str__(self):
        return self._node_repr(print_cnodes=False)

    def __repr__(self):
        return self._node_repr(print_cnodes=True)

    def tree_text(self):
        ## Prepare child-text.
        #
        cnodes_msg = None
        indent = '  '
        c_errs = [cn.tree_text() for cn in self.cnodes]
        c_errs = [msg for msg in c_errs if msg]
        if c_errs:
            cnodes_msg = ''.join('\n- %s' % t for t in c_errs)
            cnodes_msg = tw.indent(cnodes_msg, indent)
        elif not self.err:
            return

        ## Prepare text for my exception.
        #
        msg_parts = ['while %s:' % (self.doing or '??')]

        if cnodes_msg:
            msg_parts.append(cnodes_msg)
        if self.err:
            errtype = 'ignored' if self.is_forced else 'delayed'
            msg_parts.append("\n  %s: %s" % (errtype, _exstr(self.err)))

        return ''.join(msg_parts)


## TODO: decouple `force` from `ErrLog`.
class ErrLog(cmdlets.Replaceable, trt.HasTraits):
    """
    Collects errors in "stacked" contexts and delays or ignores ("forces") them.

    - Unknown errors (not in `exceptions`) always bubble up immediately.
    - Any "forced" errors are collected and logged in `warn_log` on context-exit,
      forcing is enabled when the `token` given exists in `spec`'s ``force`` attribute.
    - Non-"forced" errors are either `raise_immediately`, or raised collectively
      in a :class:`CollectedErrors`, on context-exit.
    - Collected are always logged on DEBUG immediately.
    - Instances of this class are callable, and the call will return a *clone*
      with provided properties updated.
    - A *clone* is also returned when acquiring the context in a `with`
      statement.

    :ivar spec:
        the spec instance to search in its :attr:`Spec.force` for the token
    :ivar exceptions:
        the exceptions to delay or forced; others are left to bubble immediately
    :ivar token:
        the :attr:`force` token to respect, like :meth:`Spec.is_force()`,
        with possible values:
          - false: (default) completely ignore `force` trait
             collected are just delayed);
          - <a string>: "force" if this token is in `force` trait;
          - `True`: "force" if `True` is in :attr:`force``force`.
    :ivar doing:
        A description of the running activity for the current stacked-context,
        in present continuous tense, e.g. "readind X-files".

        Assuming `doing = "having fun"`, it may generate
        one of those 3 error messages::

            Failed having fun due to: EX
            ...and collected 21 errors (3 ignored):
                - Err 1: ...

            Collected 21 errors (3 ignored) while having fun:
                - Err 1: ...

            LOG: Ignored 9 errors while having fun:
                - Err 1: ...

    :ivar raise_immediately:
        if not forced, do not wait for `report()` call to raise them;
        suggested use when a function decorator.  Also when --debug.
    :ivar warn_log:
        the logging method to report forced errors; if none given,
        use searched the log ov the `parent` or falls back to this's modules log.
        Note that all failures are always reported immediately on DEBUG.
    :ivar info_log:
        the logging method to report completed "doing" tasks; if none given
        does not report them.

    PRIVATE FIELDS:

    :ivar _root_node:
        The root of the tree of nodes, populated when entering contexts recursively.
    :ivar _active_node:
         the child-node created on :meth:`__enter__()`

    Example of using this method for multiple actions in a loop::

        with ErrLog(enforeceable, IOError,
                    doing="loading X-files",
                    token='fread') as errlog:
            for fpath in file_paths:
                with errlog(doing="reading '%s'" % fpath) as erl2:
                    fbytes.append(fpath.read_bytes())

        # Any errors collected will raise/WARN here (root-context exit).

    """
    class ErrLogException(Exception):
        """A pass-through for critical ErrLog, e.g. context re-enter. """
        pass

    class CollectedErrors(cmdlets.CmdException):
        pass

    ## TODO: weakref(ErrLog.parent), see `BaseDescriptor._property`.
    parent = Instance(cmdlets.Forceable)
    exceptions = ListTrait(TypeTrait(Exception))
    token = UnionTrait((Unicode(), Bool()), allow_none=True)
    doing = Unicode(allow_none=True)
    raise_immediately = CBool()
    warn_log = CallableTrait(allow_none=True)
    info_log = CallableTrait(allow_none=True)

    _root_node: _ErrNode = Instance(_ErrNode,   # type: ignore
                                    default_value=None, allow_none=True)
    _active_node: _ErrNode = Instance(_ErrNode,      # type: ignore
                                      default_value=None, allow_none=True)

    @property
    def plog(self) -> logging.Logger:
        """Search `log` property in `parent`, or use this module's logger."""
        return getattr(self.parent, 'log', log)

    def logw(self, *args, **kwds):
        log = self.warn_log or partial(self.plog.log, logging.INFO)
        log(*args, **kwds)

    @property
    def pdebug(self) -> logging.Logger:
        """Search `debug` property in `parent`, or False."""
        return getattr(self.parent, 'debug', False)

    @property
    def is_forced(self):
        """Try `force` in `parent` first."""
        ## TODO: decouple `force` from `ErrLog`.
        return getattr(self.parent, 'is_forced')(token=self.token)

    @property
    def is_root(self):
        """Return true regardless if armed."""
        return self._active_node is self._root_node

    @property
    def is_armed(self):
        """Is context ``__enter__()`` currently under process? """
        return self._active_node is not None

    @property
    def is_good(self):
        """
        An errlog is "good" if its anchor has not captured any exception yet.

        If it does, it cannot be used anymore.
        """
        return not self._active_node or not bool(self._active_node.err)

    @property
    def coords(self) -> List[int]:
        """Return the coordinate-indices from the root or [] if root. """
        if self._root_node and self._active_node:
            return self._root_node.node_coordinates(self._active_node)
        return []

    def __init__(self,
                 parent: cmdlets.Forceable,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,  # Start as collecting only
                 doing=None,
                 raise_immediately=None,
                 warn_log: Callable = None,
                 info_log: Callable = None,
                 ) -> None:
        """Root created only in constructor - the rest in __call__()/__enter__()."""
        if not isinstance(parent, cmdlets.Forceable):
            raise trt.TraitError("Parent '%s' is not Forceable!" % parent)
        super().__init__(parent=parent, exceptions=exceptions,
                         token=token, doing=doing,
                         raise_immediately=raise_immediately,
                         warn_log=warn_log,
                         info_log=info_log,
                         )

    def __repr__(self):
        return '%s<rot=%r, crd=%s, act=%s>@%s' % (
            type(self).__name__,
            self._root_node,
            ', '.join(str(i) for i in self.coords),
            self._active_node,
            _idstr(self))

    def _scream_on_faulted_reuse(self):
        ## TODO: test _scream_on_faulted_reuse
        if not self.is_good:
            raise ErrLog.ErrLogException('Cannot re-use faulted %r!' % self)

    def __call__(self,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,
                 doing=None,
                 raise_immediately=None,
                 warn_log: Callable = None,
                 info_log: Callable = None,
                 ) -> 'ErrLog':
        """Reconfigure a new errlog on the same stack-level."""
        self._scream_on_faulted_reuse()
        changes = {}  # to gather replaced fields
        fields = zip('token doing raise_immediately warn_log info_log'.split(),
                     [token, doing, raise_immediately, warn_log, info_log])
        for k, v in fields:
            if v is not None:
                changes[k] = v
        if exceptions:  # None-check futile
            changes['exceptions'] = exceptions  # type: ignore

        ## Note etuples-root & children always shared (not deepcopy).

        clone = self.replace(**changes)

        return clone

    def __enter__(self) -> 'ErrLog':
        """Return `self` upon entering the runtime context."""
        self._scream_on_faulted_reuse()
        if self.is_armed:
            raise ErrLog.ErrLogException("Cannot re-enter context of %r!" % self)

        if self._root_node is None:
            assert not self._active_node, self

            new_root = _ErrNode()
            changes = {
                '_root_node': new_root,
                '_active_node': new_root.new_cnode(self.doing,
                                                   self.is_forced)}
        else:
            assert self._active_node, self

            changes = {
                '_active_node': self._active_node.new_cnode(self.doing,
                                                            self.is_forced)}

        return self.replace(**changes)

    def _report_completion(self) -> None:
        assert self._root_node and self._active_node, self

        if self.info_log:
            doing = ' %s' % self.doing if self.doing else ''

            coords = '.'.join(str(i + 1) for i in self.coords)
            if coords:
                coords += '. '

            nsubs = len(self._active_node.cnodes)
            subtasks = ''
            if nsubs:
                subtasks = '%i subtasks' % nsubs
                nforced = sum(1 for cn in self._active_node.cnodes
                              if cn.err)
                ignored = ''
                if nforced:
                    ignored = ', %i errors ignored' % nforced

                subtasks = ' (%s%s)' % (subtasks, ignored)
            self.info_log("%sFinished%s%s." %
                          (coords, doing, subtasks))

    def __exit__(self, exctype, ex, _exctb):
        ## A 3-state flag:
        #  - None: no exc
        #  - False: raising
        #  - True: suppressing raised ex
        suppressed_ex = None
        if exctype is None:
            self._report_completion()
        else:
            suppressed_ex = False

            if issubclass(exctype, tuple(self.exceptions)) and (
                    self.is_forced or not self.raise_immediately):
                #ex = ex.with_traceback(exctb)  Ex already has it!
                self._collect_error(ex)
                suppressed_ex = True

        try:
                return suppressed_ex
        finally:
                if self.is_root:
                    assert not (self._root_node or self._active_node)
                    self.report(None if suppressed_ex else ex)

    def _collect_error(self, ex):
        assert self.is_armed, self

        self._active_node.err = ex

        log = self.plog
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Collecting %s.", _exstr(ex), exc_info=ex)

    def report(self, ex_raised) -> Optional['ErrLog.CollectedErrors']:
        """
        :param ex_raised:
            any exception captured in tree (if any), unless `ex_raised` given
        :return:
            a :class:`ErrLog.CollectedErrors` in case catured errors contain
            non-forced errors BUT `ex_raised` given.
        :raise ErrLog.CollectedErrors:
            any non-forced exceptions captured in tree (if any),
            unless `ex_raised` given
        """
        assert self.is_armed, self

        node = self._active_node
        nerrors, nforced = node.count_error_tree()
        assert nerrors >= nforced >= 0, (nerrors, nforced, self)
        if nerrors == 0:
            return None

        is_all_forced = nerrors == nforced
        if is_all_forced:
            count_msg = "ignored %i errors" % nerrors
        elif nforced > 0:
            count_msg = "collected %i errors (%i ignored)" % (nerrors, nforced)
        else:
            count_msg = "collected %i errors" % nerrors

        msg = ' '.join((count_msg.capitalize(), node.tree_text()))

        if is_all_forced or ex_raised:
            self.logw(msg)

            if is_all_forced:
                return None

        errors = ErrLog.CollectedErrors(msg)
        if ex_raised:
            return errors
        else:
            raise errors


def errlogged(*errlog_args, **errlog_kw):
    """
    Decorate functions/methods with a :class:`ErrLog` instance.

    The errlog-contextman is attached on the wrapped function/method
    as the `errlog` attribute.
    """
    def decorate(func):
        @contextlib.wraps(func)
        def inner(forceable, *args, **kw):
            errlog = ErrLog(forceable, *errlog_args, **errlog_kw)
            inner.errlog = errlog
            with errlog(*errlog_args, **errlog_kw):
                return func(forceable, *args, **kw)

        return inner

    return decorate
