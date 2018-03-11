# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""
Enable Unicode-trait to pep3101-interpolate `{key}` patterns from "context" dicts.
"""
from collections import ChainMap, abc
import contextlib
import os
from typing import Dict

from ._vendor.traitlets import traitlets as trt


class Now:  # TODO: privatize
    def __init__(self, is_utc=False):
        self.is_utc = is_utc

    def __format__(self, format_spec):
        from datetime import datetime as dt

        now = dt.now() if self.is_utc else dt.utcnow()

        return now.__format__(format_spec)


class Keys:  # TODO: privatize
    def __init__(self, mydict):
        self.mydict = mydict

    def __format__(self, format_spec):
        return ', '.join(k for k in self.mydict.keys() if not k.startswith('$'))


class _MissingKeys(dict):
    __slots__ = ()

    def __missing__(self, key):
        return '{%s}' % key


#: Used when interp-context claiming to have all keys.
_missing_keys = _MissingKeys()


class _HasTraitObjectDict(abc.Mapping):
    def __init__(self, _obj: trt.HasTraits):
        self._obj: trt.HasTraits = _obj

    def __len__(self):
        return len(self._obj.traits())

    def __getitem__(self, key):
        if self._obj.has_trait(key):
            return getattr(self._obj, key)
        else:
            raise KeyError(key)

    def __iter__(self):
        return iter(self._obj.trait_names())


def dictize_object(obj):
    if isinstance(obj, (dict, abc.Mapping)):
        pass
    elif isinstance(obj, trt.HasTraits):
        obj = _HasTraitObjectDict(obj)
    else:
        ## Collect object's and MRO classes's items
        # in a chain-dict.
        #
        maps = [vars(obj)]
        maps.extend(vars(c) for c in type(obj).mro())
        obj = ChainMap(*maps)

    return obj


class InterpolationContext(ChainMap):
    """
    A stack of 4 dics to be used as interpolation context.

    The 3 stacked dicts are:
      0. user-map: writes affect permanently this dict only;
      1. time: ('now', 'utcnow'), always updated on access;
      2. env-vars, `$`-prefixed.

    Append more dicts in ``self.maps`` list if you wish.
    """
    def __init__(self):
        super().__init__()
        self.time_map = {
            'now': Now(),
            'utcnow': Now(is_utc=True),
            'ikeys': Keys(self),
        }
        self.env_map = {}
        self.maps.extend([self.time_map, self.env_map])

        self.update_env()

    def update_env(self):
        self.env_map.clear()
        self.env_map.update({'$' + k: v for k, v in os.environ.items()})

    @contextlib.contextmanager
    def ikeys(self, *maps: Dict, stub_keys=False, **kv_pairs) -> Dict:
        """
        Temporarily place more maps immediately after user-map (2nd position).

        :param maps:
            a list of dictionaries/objects/HasTraits from which to draw
            items/attributes/trait-values, all in decreasing priority.
        :param stub_keys:
            If true, any missing-key gets returned as ``{key}``.

            .. NOTE::
               Use ``str.format_map()`` when `stub_keys` is true; ``format()``
               will clone existing keys in a static map.

        Later maps take precedence over earlier ones; `kv_pairs` have the highest,
        `stub_keys` the lowest (if true).
        """
        tmp_maps = [_missing_keys] if stub_keys else []
        tmp_maps.extend(dictize_object(m) for m in maps)
        if kv_pairs:
            tmp_maps.append(kv_pairs)

        orig_maps = self.maps
        self.maps = orig_maps[:1] + tmp_maps[::-1] + orig_maps[1:]
        try:
            yield self
        finally:
            self.maps = orig_maps
