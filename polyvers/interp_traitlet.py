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
import os

from ._vendor.traitlets import TraitError, Unicode  # @UnresolvedImport


_original_Unicode_validate = Unicode.validate


class Template(Unicode):
    """
    A Unicode PEP-3101 expanding any '{key}' from *context* dictionaries (``s.format(d)``).

    To disable interpolation, tag trait with ``'interp_enabled'`` as false.

    :ivar str context_attr:
        The name of the attribute to search on the defining class;
        might be a context-dict or a callable performing the interpolation.
        [Default: ''interpolation'']
    """
    context_attr = 'interpolation'

    def __init__(self, *args, context_attr=None, **kw):
        """
        :param str context_attr:
            The name of the attribute to search on the defining class;
            might be a context-dict or a callable performing the interpolation.
        """
        if context_attr:
            self.context_attr = context_attr
        super().__init__(*args, **kw)

    def validate(self, obj, value):
        ctxt = getattr(obj, self.context_attr, None)
        if ctxt and self.metadata.get('interp_enabled', True):
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

        return super().validate(obj, value)


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

    Append more dicts in ``self.ctxt.maps`` list if you wish.

    :ivar dict ctxt:
        the dictionary with all key-value interpolations

    """
    def __init__(self):
        dicts = [{} for _ in range(3)]
        dicts[1] = {
            'now': Now(),
            'utcnow': Now(is_utc=True),
        }
        self.ctxt = ChainMap(*dicts)
        self.update_env()

    def update_env(self):
        self.ctxt.maps[2] = {'$' + k: v for k, v in os.environ.items()}
