#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from builtins import property
"""Gather multiple exceptions in a nested contexts. """

from typing import Any, List, Dict, Union, Tuple, Optional, Sequence  # noqa: F401 @UnusedImport
import contextlib
import logging

from . import cmdlets
from ._vendor import traitlets as trt
from ._vendor.traitlets.traitlets import (
    List as ListTrait, Type as TypeTrait, Union as UnionTrait
)  # @UnresolvedImport
from ._vendor.traitlets.traitlets import Bool, CBool, Int, Unicode, Instance


log = logging.getLogger(__name__)


class ErrLogErrors(cmdlets.CmdException):
    def __init__(self, etuples, doing=None):
        #self.etuples = etuples

        doing = ' while %s' % doing if doing else ''
        self.is_all_forced = all(is_forced for _, is_forced, _ in etuples)
        reason = 'Bypassed' if self.is_all_forced else 'Collected'
        erlines = ''.join('\n  %s' % ErrLog._format_etuple(*etuple)
                          for etuple in etuples)
        self.msg = "%s %i error(s)%s: %s" % (reason, len(etuples), doing, erlines)

    def __str__(self):
        return self.msg


class _ELNode(trt.HasTraits):
    """
    The basic element of a *recursive* "stack" of.

    ::

        node :=   (doing, is_forced, exception, [node, ...])

    Cannot store textualized exception in the first place because
    this is only known after all its children have been born (if any).
    """
    doing = Unicode(default_value=None, allow_none=True)
    is_forced = Bool(default_value=None, allow_none=True)
    err = Instance(Exception, default_value=None, allow_none=True)
    cnodes = ListTrait()

    def new_cnode(self, doing, is_forced):
        ## `is_empty` already checked by client code
        #   to explain situation.
        assert all(i is None
                   for i in (self.doing, self.is_forced, self.err)
                   ), self

        self.doing = doing or ''
        self.is_forced = bool(is_forced)

        if self.cnodes is None:
            self.cnodes = []

        child = _ELNode()
        self.cnodes.append(child)

        return child

    def dissarm(self, err=None):
        self.doing = self.is_forced = self.err = err

    @property
    def is_empty(self):
        props = (self.doing, self.is_forced, self.err)
        is_empty = any(i is None for i in props)
        if is_empty and not all(i is None for i in props):
            raise ErrLogErrors('Expected an fully empty %r!' % self)

        return is_empty

    def cnode_coordinates(self, node, coords: List[int]):
        if self is node:
            return

        for i, self in enumerate(self.cnodes):
            if node is self:
                coords.append(i)
                return

    def __repr__(self):
        props = (self.doing, self.is_forced, self.cnodes)
        ## Avoid recursion using `is_empty()`.
        is_empty = any(i is None for i in props)
        if is_empty:
            return 'ELN()'
        return 'ELN(%s, %s, %s, %s)@%s' % (
            self.doing, self.is_forced, self.err,
            self.cnodes and '...' or '[]', id(self))


_ELNode.cnodes._trait = Instance(_ELNode)


## TODO: decouple `force` from `ErrLog`.
class ErrLog(cmdlets.Replaceable, trt.HasTraits):
    """
    A contextman collecting or "forcing" in a :class:`Spec` error-list.

    - Unknown (not in `exceptions`) always bubble up immediately.
    - If `token` given and exitst in :attr:`Spec.force`, are "forced",
      i.e. are collected and logged as `log_level` when :meth:`report()`
      invoked.
    - Non-"forced" are either `raise_immediately`, or raised collectively
      when :meth:`report()` invoked.
    - Collected ("forced" or non-`raise_immediately`) are logged on DEBUG
      immediately.

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
        e.g. "having fun" would result roughly in::

            ErrLogErrors("Collected 2 while having fun:")

    :ivar raise_immediately:
        if not forced, do not wait for `report()` call to raise them;
        suggested use when a function decorator.  Also when --debug.
    :ivar log_level:
        the logging level to use when just reporting.
        Note that all are always reported immediately on DEBUG.

    :ivar _my_node:
        a list of `doing` with each nested errlog appending one more
    :ivar _enforced_error_tuples:
        collected arrors as a list of 3-tuples (doing, is_forced, ex),
        cleared only when :meth:`report()` called.

    See :meth:`Spec.errlog()` for example.
    """
    class ErrLogException(Exception):
        """A pass-through for critical ErrLog, e.g. context re-enter. """
        pass

    @staticmethod
    def _format_etuple(doing, is_forced, ex):
        doing = doing and " while %s" % doing or ''
        errtype = '"forced"' if is_forced else 'delayed'
        exstr = str(ex)
        if exstr:
            exstr = "%s: %s" % (type(ex).__name__, exstr)
        else:
            exstr = type(ex).__name__
        return "%s error%s -> %s" % (errtype, doing, exstr)

    ## TODO: weakref(ErrLog.parent), see `BaseDescriptor._property`.
    parent = Instance(cmdlets.Forceable)
    exceptions = ListTrait(TypeTrait(Exception))
    token = UnionTrait((Unicode(), Bool()), allow_none=True)
    doing = Unicode(allow_none=True)
    raise_immediately = CBool()
    log_level = UnionTrait((Int(), Unicode()))

    #: A point in the `_root_node` to grow from.
    _root_node: _ELNode = Instance(_ELNode)  # type: ignore
    _my_node = _root_node

    @property
    def plog(self) -> logging.Logger:
        """Search `log` property in `parent`, or use this module's logger."""
        return getattr(self.parent, 'log', log)

    @property
    def pdebug(self) -> logging.Logger:
        """Search `debug` property in `parent`, or False."""
        return getattr(self.parent, 'debug', False)

    def is_forced(self):
        """Try `force` in `parent` first."""
        ## TODO: decouple `force` from `ErrLog`.
        return getattr(self.parent, 'is_forced')(token=self.token)

    @property
    def is_root(self):
        return self._my_node is self._root_node

    @property
    def is_armed(self):
        """Is context ``__enter__()`` currently under process? """
        return not self._my_node.is_empty

    @property
    def _my_node_coordinates(self):
        return self._root_node._my_node_coords(self)

    def __init__(self,
                 parent: cmdlets.Forceable,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,  # Start as collecting only
                 doing=None,
                 raise_immediately=None,
                 log_level=logging.WARNING
                 ) -> None:
        """Root created only in constructor - the rest in __call__()/__enter__()."""
        if not isinstance(parent, cmdlets.Forceable):
            raise trt.TraitError("Parent '%s' is not Forceable!" % parent)
        super().__init__(parent=parent, exceptions=exceptions,
                         token=token, doing=doing,
                         raise_immediately=raise_immediately,
                         log_level=log_level,
                         )
        self._root_node = _ELNode()

    def __repr__(self):
        return '%s(%s, coords=root=%s, root=%s)@%s)' % (
            type(self).__name__,
            self._my_node, self._my_node_coordinates, self._root_node,
            id(self))

    def __call__(self,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,
                 doing=None,
                 raise_immediately=None,
                 log_level: Union[int, str] = None):
        """Reconfigure a new errlog on the same stack-level."""
        changes = {}  # to gather replaced fields
        fields = zip('token doing raise_immediately log_level'.split(),
                     [token, doing, raise_immediately, log_level])
        for k, v in fields:
            if v is not None:
                changes[k] = v
        if exceptions:  # None-check futile
            changes['exceptions'] = exceptions

        ## Note etuples-root & children always shared (not deepcopy).

        clone = self.replace(**changes)

        return clone

    def __enter__(self):
        """Return `self` upon entering the runtime context."""
        if self.is_armed:
            raise ErrLog.ErrLogException("Cannot re-enter context!")

        new_node = self._my_node.new_cnode(self.doing, self.is_forced())
        new_errlog = self.replace(_my_node=new_node)

        return new_errlog

    def __exit__(self, exctype, ex, _exctb):
        ## 3-state out flag:
        #  - None: no exc
        #  - False: raising
        #  - True: collecting raised ex
        suppress_ex = None
        try:
            if exctype is not None:
                suppress_ex = False

                if issubclass(exctype, ErrLog.ErrLogException):
                    pass  # Let critical internal error bubble-up.

                if issubclass(exctype, tuple(self.exceptions)):
                    is_forced = self.is_forced()
                    if is_forced or not self.raise_immediately:
                        #ex = ex.with_traceback(exctb)  Ex already has it!
                        self._collect_error(is_forced, ex)
                        suppress_ex = True

                return suppress_ex
        finally:
            node = self._my_node
            if suppress_ex is False:  # exit is raising
                doing = node.doing
                doing = ("%s failed unexpectedly" % doing
                         if doing else
                         "failing unexpectedly")
                self.report(do_raise=False, doing=doing)
            elif not node:
                self.report(do_raise=None)
            else:
                pass  ## stacked, do nothing

    def _collect_error(self, is_forced, error):
        #error = error.with_traceback(exctb)  Ex already has it!
        etuple = (self._my_node[-1], is_forced, error)

        log = self.plog
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Collecting %s" % self._format_etuple(*etuple),
                      exc_info=error)

        self._enforced_error_tuples.append(etuple)

    def report(self, do_raise=None, doing=None) -> str:
        """
        :param raise:
            3-state bool:
            - None: raise only if any non-forced (i.e. stack-level == 1)
            - False: log only (i.e. in a finally block)
            - True: raise only (i.e. stack-level > 1)
        """
        etuples = self._enforced_error_tuples[:]  # Order with `_flush()` matters!
        if etuples:
            self._enforced_error_tuples.clear()  # Avoid tb-memleaks from all clones.

            ex = ErrLogErrors(etuples)
            is_all_forced = ex.is_all_forced
            if do_raise is True or (do_raise is None and not is_all_forced):
                raise ex from None

            if do_raise is False or (do_raise is None and is_all_forced):
                self.plog.log(self.log_level, str(ex))
            else:
                raise AssertionError(do_raise, is_all_forced)


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
