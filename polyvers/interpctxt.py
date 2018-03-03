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
    A stack of 4 dics to be used as interpolation context.

    The 4 stacked dicts are:
      0. user-info: writes affect permanently this dict only;
      1. tmp-keys: using :meth:`keys` as context-manager affect this
         dict only;
      3. time: ('now', 'utcnow'), always updated on access;
      3. env-vars, `$`-prefixed.

    Append more dicts in ``self.ctxt.maps`` list if you wish.

    :ivar dict ctxt:
        the dictionary with all key-value interpolations

    """
    def __init__(self):
        self.time_map = {}
        self._temp_map = {}
        self.env_map = {}
        self.ctxt = ChainMap({}, self._temp_map, self.time_map, self.env_map)

        self.update_env()
        self.time_map.update({
            'now': Now(),
            'utcnow': Now(is_utc=True),
            'ikeys': Keys(self.ctxt),
        })

    def update_env(self):
        self.env_map.clear()
        self.env_map.update({'$' + k: v for k, v in os.environ.items()})

    @contextlib.contextmanager
    def keys(self, **keys):
        """Temporarily place key-value pairs into context."""
        self._temp_map.update(keys)
        try:
            yield self.ctxt
        finally:
            self._temp_map.clear()
