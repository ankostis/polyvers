#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Gather multiple exceptions in a nested contexts. """

from typing import Any, List, Dict, Union, Tuple, Optional, Sequence  # noqa: F401 @UnusedImport
import logging

from . import cmdlets
from ._vendor import traitlets as trt
from ._vendor.traitlets.traitlets import (
    List as ListTrait, Type as TypeTrait, Union as UnionTrait
)  # @UnresolvedImport
from ._vendor.traitlets.traitlets import Bool, CBool, Int, Unicode, Instance


log = logging.getLogger(__name__)


class ErrLog(cmdlets.Replaceable, trt.HasTraits):
    """
    A contextman collecting or "forcing" errors in a :class:`Spec` error-list.

    - Unknown errors (not in `exceptions`) always bubble up immediately.
    - If `token` given and exitst in :attr:`Spec.force`, errors are "forced",
      i.e. are collected and logged as `log_level` when :meth:`report_errors()`
      invoked.
    - Non-"forced" errors are either `raise_immediately`, or raised collectively
      when :meth:`report_errors()` invoked.
    - Collected errors ("forced" or non-`raise_immediately`) are logged on DEBUG
      immediately.

    :ivar spec:
        the spec instance to search in its :attr:`Spec.force` for the token
    :ivar exceptions:
        the exceptions to delay or forced; others are left to bubble immediately
    :ivar token:
        the :attr:`force` token to respect, like :meth:`Spec.is_force()`,
        with possible values:
          - false: (default) completely ignore `force` trait
            (errors collected are just delayed);
          - <a string>: "force" errors if this token is in `force` trait;
          - `True`: "force" errors if `True` is in :attr:`force``force`.
    :ivar raise_immediately:
        if not forced, do not wait for `report_errors()` call to raise them;
        suggested use when a function decorator.  Also when --debug.
    :ivar log_level:
        the logging level to use when just reporting errors.
        Note that all errors are always reported immediately on DEBUG.

    :ivar _enforced_error_tuples:
        collected arrors as a list of 3-tuples (doing, raise_later, ex),
        cleared only when :meth:`report_errors()` called.

    See :meth:`Spec.errlog()` for example.
    """
    parent = Instance(cmdlets.Forceable)
    exceptions = ListTrait(TypeTrait(Exception))
    token = UnionTrait((Unicode(), Bool()), allow_none=True)
    doing = Unicode(None, allow_none=True)
    raise_immediately = CBool()
    log_level = UnionTrait((Int(), Unicode()))

    @property
    def plog(self) -> logging.Logger:
        """Search log property up the `parent` hierarchy."""
        return getattr(self.parent, 'log', log)

    def is_forced(self):
        """Try `force` in `parent` first."""
        return getattr(self.parent, 'is_forced')(token=self.token)

    def __init__(self,
                 parent: cmdlets.Forceable,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,  # Start as collecting only
                 doing=None,
                 raise_immediately=None,
                 log_level=logging.WARNING
                 ) -> None:
        super().__init__(parent=parent, token=token, doing=doing,
                         raise_immediately=raise_immediately,
                         log_level=log_level)
        if exceptions:
            self.exceptions = exceptions
        self._enforced_error_tuples: List[Tuple[Any, bool, Exception]] = []

    def __call__(self,
                 *exceptions: Exception,
                 token: Union[bool, str, None] = None,
                 doing=None,
                 raise_immediately=None,
                 log_level: Union[int, str] = None):
        """Reconfigure a new errlog."""
        changes = {}
        fields = zip('token doing raise_immediately log_level'.split(),
                     [token, doing, raise_immediately, log_level])
        for k, v in fields:
            if v is not None:
                changes[k] = v
        if exceptions:  # None-check futile
            changes['exceptions'] = self.exceptions

        clone = self.replace(**changes)
        ## Share my etuples with clone.
        clone._enforced_error_tuples = self._enforced_error_tuples

        return clone

    def __enter__(self):
        """Return `self` upon entering the runtime context."""
        return self

    def __exit__(self, exctype, excinst, _exctb):
        if exctype is not None:
            suppress_ex = False
            try:
                if issubclass(exctype, tuple(self.exceptions)):
                    is_forced = self.is_forced()
                    if is_forced or not self.raise_immediately:
                        #excinst = excinst.with_traceback(exctb)  Ex already has it!
                        self._collect_error(is_forced, excinst)
                        suppress_ex = True

                return suppress_ex
            finally:
                if not suppress_ex:
                    doing = self.doing
                    self.doing = ("%s failed unexpectedly" % doing
                                  if doing else
                                  "failing unexpectedly")
                    self.report_errors(no_raise=True)

    @classmethod
    def _format_etuple(cls, doing, is_forced, ex):
        doing = doing and " while %s" % doing or ''
        errtype = '"forced"' if is_forced else 'delayed'
        exstr = str(ex)
        if exstr:
            exstr = "%s: %s" % (type(ex).__name__, exstr)
        else:
            exstr = type(ex).__name__
        return "%s error%s -> %s" % (errtype, doing, exstr)

    def _collect_error(self, is_forced, error):
        #error = error.with_traceback(exctb)  Ex already has it!
        etuple = (self.doing, is_forced, error)

        log = self.plog
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Collecting %s" % self._format_etuple(*etuple),
                      exc_info=error)

        self._enforced_error_tuples.append(etuple)

    def _flush_errors(self) -> Optional[str]:
        """Generate a message for all collected errors, before clearing them."""
        if self._enforced_error_tuples:
            etuples = self._enforced_error_tuples
            self._enforced_error_tuples = []  # Avoid stacktrace memleaks.
            erlines = ''.join('\n  %s' % self._format_etuple(*etuple)
                              for etuple in etuples)
            doing = self.doing and ' while %s' % self.doing or ''
            all_forced = all(is_forced for _, is_forced, _ in etuples)
            reason = 'Bypassed' if all_forced else 'Collected'

            return "%s %i error(s)%s: %s" % (
                reason, len(etuples), doing, erlines)

    def report_errors(self, no_raise=False) -> str:
        etuples = self._enforced_error_tuples  # Order with `_flush()` matters!
        if etuples:
            err_msg = self._flush_errors()
            all_forced = all(is_forced for _, is_forced, _ in etuples)
            if no_raise or all_forced:
                self.plog.log(self.log_level, err_msg)
            else:
                raise cmdlets.CmdException(err_msg)
