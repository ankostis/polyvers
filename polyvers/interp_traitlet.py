# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Enable Unicode-trait to pep3101-interpolate `{key}` patterns from "context" dicts.
"""

from collections import ChainMap
import contextlib
import os

from ._vendor.traitlets import TraitError, Unicode  # @UnresolvedImport


_original_Unicode_validate = Unicode.validate


def enable_unicode_trait_interpolating(context_attr='interpolation'):
    """
    Patch :class:`Unicode` trait to interpolate from a context-dict on defining class.

    :patam str context_attr:
        The name of the attribute to search on the defining class;
        might be a dict or a callable returning a dict.
    """
    global _original_Unicode_validate

    def interpolating_validate(self, obj, value):
        ctxt = getattr(obj, context_attr, None)
        print(getattr(self, 'no_interpolation', None))
        if ctxt and not self.metadata.get('no_interpolation'):
            try:
                if callable(ctxt):
                    value = ctxt(self, value)
                else:
                    value = value.format(**ctxt)
            except Exception as ex:
                msg = ("Failed expanding trait `%s.%s` due to: %r"
                       "\n  Original text: %s"
                       % (type(obj).__name__, self.name, ex, value))
                raise TraitError(msg)

        return _original_Unicode_validate(self, obj, value)

    Unicode.validate = interpolating_validate


def dissable_unicode_trait_interpolating():
    global _original_Unicode_validate

    Unicode.validate = _original_Unicode_validate


@contextlib.contextmanager
def interpolating_unicodes(**kw):
    enable_unicode_trait_interpolating(**kw)
    try:
        yield
    finally:
        dissable_unicode_trait_interpolating()


class Now:
    def __init__(self, is_utc=False):
        self.is_utc = is_utc

    def __format__(self, format_spec):
        from datetime import datetime as dt

        now = dt.now() if self.is_utc else dt.utcnow()

        return now.__format__(format_spec)


class InterpContext:
    """
    A stack of 3 dics to be used as interpolation context.

    The 3 stacked dicts are:
      0. user-info: writes affect this dict only,
      1. time: ('now', 'utcnow'), always updated on access,
      2. env-vars, `$`-prefixed.

    :ivar dict ctxt:
        the dictionary with all key-value interpolations

    """
    def __init__(self, user_dicts_n=0):
        """
        :param int user_dicts_n:
            how many extra dicts to insert in the context (apart from the 3)
        """
        dicts = [{} for _ in range(3 + user_dicts_n)]
        dicts[1] = {
            'now': Now(),
            'utcnow': Now(is_utc=True),
        }
        self.ctxt = ChainMap(*dicts)
        self.update_env()

    def update_env(self):
        self.ctxt.maps[2] = {'$' + k: v for k, v in os.environ.items()}
