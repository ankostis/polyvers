#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Suppress or ignore  exceptions collected in a nested contexts.

To get a "nested" :class:`ErrLog` instance either use :func:`nesterrlog()`, or
call :meth:`ErrLog.__call__()` on the enclosing one.

FIXME: possible to have different node-hierarchies in contextvars-nesting!!
       (unless :meth:`ErrLog()` constructor is never called)
"""

from functools import partial
from typing import Any, Dict, Union, Callable  # noqa: F401 @UnusedImport
from typing import List, Tuple, Optional
import contextlib
import logging

import contextvars

import textwrap as tw

from . import cmdlets
from .._vendor import traitlets as trt
from .._vendor.traitlets.traitlets import (
    List as ListTrait, Type as TypeTrait, Union as UnionTrait, Callable as CallableTrait
)
from .._vendor.traitlets.traitlets import Bool, CBool, Unicode, Instance


log = logging.getLogger(__name__)


#: The thread-local :class:`ErrLog` used to nest elogs.
_nesting_errlog = contextvars.ContextVar('errlog', default=None)


def nesterrlog(parent,
               *exceptions,
               token: Union[bool, str] = None,
               doing=None,
               raise_immediately=None,
               warn_log: Callable = None,
               info_log: Callable = None):
    """
    To nest errlogs, prefer this function instead of this :class:`ErrLog()` constructor,
    or else you must keep a reference on the last enclosing errlog and
    explicitly call :meth:`ErrLog.__call__()` on it.
    """

    #: `mypy` has genericized `ContextVar` in the `typeshed
    #: <https://www.python.org/dev/peps/pep-0484/#typeshed)>`_:
    #: https://github.com/python/typeshed/blob/master/stdlib/3.7/contextvars.pyi
    enclosing_elog = _nesting_errlog.get()  # type: ignore
    if enclosing_elog is None:
        elog = ErrLog(
            parent,
            *exceptions,
            token=token, doing=doing,
            raise_immediately=raise_immediately,
            warn_log=warn_log,
            info_log=info_log,
        )
    else:
        elog = enclosing_elog(
            *exceptions,
            parent=parent,
            token=token, doing=doing,
            raise_immediately=raise_immediately,
            warn_log=warn_log,
            info_log=info_log,
        )

    return elog


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
    token = UnionTrait((Bool(), Unicode()),
                       default_value=None, allow_none=True)
    err = Instance(Exception, default_value=None, allow_none=True)
    cnodes = ListTrait()  # eventful=True)
    #cnodes._trait = Instance('polyvers.errlog._ErrNode')

    def new_cnode(self, doing, is_forced, token):
        assert self.err is None, repr(self)

        child = _ErrNode(doing=doing or '',
                         is_forced=bool(is_forced),
                         token=token)
        self.cnodes.append(child)

        return child

    def node_coordinates(self, node):
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
        props = (self.doing, self.is_forced, self.err)  # token might be `None`
        ## Avoid recursion using `is_empty()`.
        is_empty = all(i is None for i in props) and not self.cnodes
        if is_empty:
            return 'ELN@%s' % _idstr(self)
        fields = []
        if self.doing:
            fields.append('%r' % self.doing)
        if self.is_forced is not None:
            fields.append('F' if self.is_forced else 'NF')
        if self.token is not None:
            fields.append('%r' % self.token)
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
            force_msg = '' if self.token is None else ' (--force=%s)' % self.token
            msg_parts.append("\n  %s%s: %s" % (
                errtype, force_msg, _exstr(self.err)))

        return ''.join(msg_parts)


#: delimetSentinel to detect values given in a :meth:`ErrLog.__call__()`.
_no_value = object()


class CollectedErrors(cmdlets.CmdException):
    pass


## TODO: decouple `force` from `ErrLog`.
class ErrLog(cmdlets.Replaceable, trt.HasTraits):
    """
    Collects errors in "stacked" contexts and delays or ignores ("forces") them.

    .. NOTE::
        To nest errlogs, prefer :func:`nesterrlog()` instead of this constructor,
        or else you must keep a reference on the last enclosing errlog and
        explicitly call :meth:`ErrLog.__call__()` on it.

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
        If none given, :class:`Exception` is assumed.
    :ivar token:
        the :attr:`force` token to respect, like :meth:`Spec.is_forced()`.
        Resets on each new instance from :meth:`__call__()`.
        Possible values:

          - false: (default) completely ignore `force` trait
             collected are just delayed);
          - <a string>: "force" if this token is in `force` trait;
          - `True`: "force" if `True` is in :attr:`force``force`.
    :ivar doing:
        A description of the running activity for the current stacked-context,
        in present continuous tense, e.g. "readind X-files".

        Resets on each new instance from :meth:`__call__()`.
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
        Resets on each new instance from :meth:`__call__()`.
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
    :ivar _anchor:
         the parent node in the tree where on :meth:`__enter__()` a new `_active`
         child-node is attached, and the tree grows.
    :ivar _active:
         the node created in `_anchor`

    Example of using this method for multiple actions in a loop::

        with ErrLog(enforeceable, OSError,
                    doing="loading X-files",
                    token='fread') as erl1:
            for fpath in file_paths:
                with erl1(doing="reading '%s'" % fpath) as erl2:
                    fbytes.append(fpath.read_bytes())

        # Any errors collected will raise/WARN here (root-context exit).

    """
    class ErrLogException(Exception):
        """A pass-through for critical ErrLog, e.g. context re-enter. """
        pass

    ## TODO: weakref(ErrLog.parent), see `BaseDescriptor._property`.
    parent = Instance(cmdlets.Forceable)
    exceptions = ListTrait(TypeTrait(Exception))
    token = UnionTrait((Unicode(), Bool()), allow_none=True)
    doing = Unicode(allow_none=True)
    raise_immediately = CBool()
    warn_log = CallableTrait(allow_none=True)
    info_log = CallableTrait(allow_none=True)

    _root_node: _ErrNode = Instance(_ErrNode)   # type: ignore
    _anchor: _ErrNode = Instance(_ErrNode)      # type: ignore
    _active: _ErrNode = Instance(_ErrNode,      # type: ignore
                                 default_value=None, allow_none=True)

    @property
    def plog(self) -> logging.Logger:
        """Search `log` property in `parent`, or use this module's logger."""
        return getattr(self.parent, 'log', log)

    def logw(self, *args, **kwds):
        log = self.warn_log or partial(self.plog.log, logging.WARNING)
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
        return self._anchor is self._root_node

    @property
    def is_armed(self):
        """Is context ``__enter__()`` currently under process? """
        return self._active is not None

    @property
    def is_good(self):
        """
        An errlog is "good" if its anchor has not captured any exception yet.

        If it does, it cannot be used anymore.
        """
        return not bool(self._anchor.err)

    @property
    def coords(self) -> List[int]:
        """Return my anchor's coordinate-indices from the root of the tree. """
        return self._root_node.node_coordinates(self._anchor)

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
            raise ValueError("Parent '%s' is not Forceable!" % parent)
        super().__init__(parent=parent, exceptions=exceptions or (Exception, ),
                         token=token, doing=doing,
                         raise_immediately=raise_immediately,
                         warn_log=warn_log,
                         info_log=info_log,
                         )
        self._anchor = self._root_node = _ErrNode()

    def __repr__(self):
        return '%s<rot=%r, anc=%s, crd=%s, act=%s>@%s' % (
            type(self).__name__,
            self._root_node,
            self._anchor,
            ', '.join(str(i) for i in self.coords),
            self._active,
            _idstr(self))

    def _scream_on_faulted_reuse(self):
        ## TODO: test _scream_on_faulted_reuse
        if self._anchor.err:
            raise ErrLog.ErrLogException('Cannot re-use faulted %r!' % self)

    def __call__(self,
                 *exceptions: Exception,
                 parent=_no_value,
                 token=_no_value,
                 doing=None,
                 raise_immediately=None,
                 warn_log=_no_value,
                 info_log=_no_value,
                 ) -> 'ErrLog':
        """
        Returns a "cloned" errlog on the same stack-level, reconfigured.

        - Arguments `parent`, `warn_log` & `info_log` are "sticky",
          i.e. if not given, the returned clone inherits them from this instance.

        :param exceptions:
            assumed :class:`Exception` if not given.
        :param token:
            It is "semi-sticky": if not given and :attr:`token` is `True`,
            the returned clone inherits it as `True` also; textual tokens
            are not inherited.

        - Rest arguments are reset to none if not given

        :return:
            a clone :class:`ErrLog` reconfigured
        """
        self._scream_on_faulted_reuse()

        if token is _no_value:
            token = self.token is True or None

        changes = {
            'exceptions': exceptions or (Exception, ),
            'token': token,
        }

        fields = 'parent doing raise_immediately warn_log info_log'
        for f in fields.split():
            v = locals()[f]
            if v is not _no_value:
                changes[f] = v

        ## Note root, anchor, active & children pointers
        #  always shared (not deepcopy).
        clone = self.replace(**changes)

        return clone

    def __enter__(self) -> 'ErrLog':
        """Return `self` upon entering the runtime context."""
        self._scream_on_faulted_reuse()
        if self.is_armed:
            raise ErrLog.ErrLogException("Cannot re-enter context of %r!" % self)

        self._active = self._anchor.new_cnode(self.doing,
                                              self.is_forced,
                                              self.token)
        new_errlog = self.replace(_anchor=self._active, _active=None)

        ## Nest.
        self._nesting_token = _nesting_errlog.set(new_errlog)  # type: ignore

        return new_errlog

    def _report_ok_completion(self) -> None:
        if self.info_log:
            doing = ' %s' % self.doing if self.doing else ''

            coord_ids = self._root_node.node_coordinates(self._active)
            coords = '.'.join(str(i + 1) for i in coord_ids)
            if coords:
                coords += '. '

            nsubs = len(self._active.cnodes)
            subtasks = ''
            if nsubs:
                subtasks = '%i subtasks' % nsubs
                nforced = sum(1 for cn in self._active.cnodes
                              if cn.err)
                ignored = ''
                if nforced:
                    ignored = ', %i errors ignored' % nforced

                subtasks = ' (%s%s)' % (subtasks, ignored)
            self.info_log("%sFinished%s%s." %
                          (coords, doing, subtasks))

    def __exit__(self, exctype, ex, _exctb):
        ## De-nest.
        #
        assert getattr(self, '_nesting_token', None), self
        _nesting_errlog.reset(self._nesting_token)
        self._nesting_token = None

        ## A 3-state flag:
        #  - None: no exc
        #  - False: raising
        #  - True: suppressing raised ex
        suppressed_ex = None
        if exctype is None:
            self._report_ok_completion()
        else:
            suppressed_ex = False

            if issubclass(exctype, tuple(self.exceptions)):
                #ex = ex.with_traceback(exctb)  Ex already has it!
                self._collect_error(ex)

                if self.is_forced or not self.raise_immediately:
                    suppressed_ex = True

        try:
                return suppressed_ex
        finally:
            if self.is_root:
                self.report_root(None if suppressed_ex else ex)
            ## NOTE: won't clear `active` if `report_root()` raises!
            #        Not yet sure if we want that...
            self._active = None

    def _collect_error(self, ex):
        self._active.err = ex

        log = self.plog
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Collecting %s.", _exstr(ex), exc_info=ex)

    def report_root(self, ex_raised: Optional[Exception]) -> Optional['CollectedErrors']:
        """
        Raise or log the errors collected from

        :param ex_raised:
            the cntxt-body exception ``__exit__()`` is about to raise
        :return:
            a :class:`CollectedErrors` in case catured errors contain
            non-forced errors BUT `ex_raised` given.
        :raise CollectedErrors:
            any non-forced exceptions captured in tree (if any),
            unless `ex_raised` given
        """
        node = self._active  # ... not `_anchor`, but why?
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

        collected_errors = CollectedErrors(msg)
        if ex_raised and self.pdebug:
            ex_raised.__cause__ = collected_errors
        else:
            raise collected_errors


def errlogged(*errlog_args, **errlog_kw):
    """
    Decorate functions/methods with a :class:`ErrLog` instance.

    The errlog-contextman is attached on the wrapped function/method
    as the `errlog` attribute.
    """
    def decorate(func):
        @contextlib.wraps(func)
        def inner(forceable, *args, **kw):
            errlog = nesterrlog(forceable, *errlog_args, **errlog_kw)
            inner.errlog = errlog
            with errlog(*errlog_args, **errlog_kw):
                return func(forceable, *args, **kw)

        return inner

    return decorate
