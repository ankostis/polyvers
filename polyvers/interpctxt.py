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
from typing import Dict


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

    The 3 stacked dicts are:
      0. user-map: writes affect permanently this dict only;
      1. time: ('now', 'utcnow'), always updated on access;
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

    @contextlib.contextmanager
    def ikeys(self, **kv_pairs) -> Dict:
        """Temporarily place key-value pairs immediately after user-map (2nd position)."""
        ctxt = self.ctxt
        orig_maps = ctxt.maps
        ctxt.maps = ctxt.maps[:1] + [kv_pairs] + ctxt.maps[1:]
        try:
            yield ctxt
        finally:
            ctxt.maps = orig_maps

    @contextlib.contextmanager
    def imaps(self, *maps: Dict) -> Dict:
        """Temporarily place maps immediately after user-map (2nd position)."""
        assert all(isinstance(d, dict) for d in maps), maps

        ctxt = self.ctxt
        orig_maps = ctxt.maps
        ctxt.maps = ctxt.maps[:1] + list(maps) + ctxt.maps[1:]
        try:
            yield ctxt
        finally:
            ctxt.maps = orig_maps
