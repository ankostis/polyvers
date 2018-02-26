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


class Template(Unicode):
    """
    A Unicode PEP-3101 expanding any '{key}' from *context* dictionaries (``s.format(d)``).

    To disable interpolation, tag trait with ``'interp_enabled'`` as false.

    :ivar str context_attr:
        The name of the attribute of the defining class holding the context dict.
        [Default: ''interpolation'']
    """
    context_attr = 'interpolations'

    def __init__(self, *args, context_attr=None, **kw):
        """
        :param str context_attr:
            The name of the attribute of the defining class holding the context dict.
            [Default: ''interpolation'']
        """
        if context_attr:
            self.context_attr = context_attr
        super().__init__(*args, **kw)

    def validate(self, obj, value):
        ctxt = getattr(obj, self.context_attr, None)
        if ctxt and self.metadata.get('interp_enabled', True):
            try:
                value = value.format(**ctxt)
            except KeyError as ex:
                msg = ("Unknown key %r in template `%s.%s`!"
                       "\n  Use '{ikeys}' to view all available interpolations."
                       "\n  Original text: %s"
                       % (str(ex), type(obj).__name__, self.name, value))
                raise TraitError(msg)

        return super().validate(obj, value)


class Now:
    def __init__(self, is_utc=False):
        self.is_utc = is_utc

    def __format__(self, format_spec):
        from datetime import datetime as dt

        now = dt.now() if self.is_utc else dt.utcnow()

        return now.__format__(format_spec)


class Keys:
    def __init__(self, mydict):
        self.mydict = mydict

    def __format__(self, format_spec):
        return ', '.join(k for k in self.mydict.keys() if not k.startswith('$'))


class InterpolationContextManager:
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
        self.time_map = {}
        self.env_map = {}
        self.ctxt = ChainMap({}, self.time_map, self.env_map)

        self.update_env()
        self.time_map.update({
            'now': Now(),
            'utcnow': Now(is_utc=True),
            'ikeys': Keys(self.ctxt),
        })

    def update_env(self):
        self.env_map.clear()
        self.env_map.update({'$' + k: v for k, v in os.environ.items()})
