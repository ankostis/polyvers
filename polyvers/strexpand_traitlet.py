# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Enable Unicode-trait to interpolate `%(key)s)` patterns from "context" dicts.
"""

from ._vendor.traitlets import TraitError, Unicode  # @UnresolvedImport
import contextlib


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
                value = ctxt(self, value) if callable(ctxt) else value % ctxt
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
