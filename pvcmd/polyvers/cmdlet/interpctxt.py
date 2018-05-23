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
from typing import Union, Optional, Callable, ContextManager
import contextlib
import logging
import os

from .._vendor.traitlets import traitlets as trt


log = logging.getLogger(__name__)


class Now:  # TODO: privatize
    def __init__(self, is_utc=False):
        self.is_utc = is_utc

    def __format__(self, format_spec):
        from datetime import datetime as dt

        now = dt.now() if self.is_utc else dt.utcnow()

        return now.__format__(format_spec)


class _KeysDumper:  # TODO: privatize
    def __init__(self, mydict):
        self.mydict = mydict

    def __format__(self, format_spec):
        return ', '.join(k for k in self.mydict.keys() if not k.startswith('$'))


class _MissingKeys(dict):
    __slots__ = ('value')

    def __init__(self, value=None):
        self.value = value

    def __missing__(self, key):
        if callable(self.value):
            return self.value(key)
        return self.value or '{%s}' % key


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


class _EscapedObjectDict(_HasTraitObjectDict):
    """
    Escape all object's attribute-values through the given function.

    Utility for using objects as :meth:`InterpolationContext.ikeys` maps
    for regex/glob patterns.
    """
    def __init__(self, _obj: trt.HasTraits, escape_func) -> None:
        super().__init__(_obj)
        self._escape_func = escape_func

    def __getitem__(self, key):
        if self._obj.has_trait(key):
            v = getattr(self._obj, key)
            if isinstance(v, str):
                v = self._escape_func(v)

            return v
        else:
            raise KeyError(key)


def dictize_object(obj, _escaped_for: Union[Callable, str] = None):
    """
    Make an object appear as a dict for :meth:`InterpolationContext.ikeys()`.

    :param _escaped_for:
        one of 'glob', 'regex' or a callable to escape object's attribute values
    """
    if isinstance(obj, (dict, abc.Mapping)):
        pass
    elif isinstance(obj, trt.HasTraits):
        if not _escaped_for:
            obj = _HasTraitObjectDict(obj)
        else:
            if _escaped_for == 'glob':
                import glob
                _escaped_for = glob.escape

            elif _escaped_for == 'regex':
                import re
                _escaped_for = re.escape

            elif not callable(_escaped_for):
                raise AssertionError(
                    "Invalid `_escaped_for` %r!"
                    "\n  It must be either a callable or 'glob'/'regex'." %
                    _escaped_for)

            obj = _EscapedObjectDict(obj, _escaped_for)
    else:
        ## Collect object's and MRO classes's items
        # in a chain-dict.
        #
        cls = obj if isinstance(obj, type) else type(obj)
        maps = [vars(obj)]
        maps.extend(vars(c) for c in cls.mro())
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
            'ikeys': _KeysDumper(self),
        }
        self.env_map = {}
        self.maps.extend([self.time_map, self.env_map])

        self.update_env()

    def update_env(self):
        self.env_map.clear()
        self.env_map.update({'$' + k: v for k, v in os.environ.items()})

    @contextlib.contextmanager
    def ikeys(self, *maps,
              _stub_keys: Union[str, bool, None] = False,
              _escaped_for: Union[Callable, str] = None,
              **kv_pairs
              ) -> ContextManager['InterpolationContext']:
        """
        Temporarily place maps and kwds immediately after user-map (2nd position).

        - For params, see :meth:`interp()`.

        .. Attention::
           Must use ``str.format_map()`` when `_stub_keys` is true;
           otherwise, ``format()`` will clone all existing keys in
           a static map.
        """
        tmp_maps = [dictize_object(m, _escaped_for=_escaped_for) for m in maps
                    if m]
        if kv_pairs:
            tmp_maps.append(kv_pairs)

        orig_maps = self.maps
        maps = orig_maps[:1] + tmp_maps[::-1] + orig_maps[1:]
        if _stub_keys:
            maps.append(_missing_keys
                        if _stub_keys is True
                        else _MissingKeys(_stub_keys))
        self.maps = maps
        try:
            yield self
        finally:
            self.maps = orig_maps

    def interp(self, text: Optional[str],
               *maps,
               _stub_keys=False,
               _escaped_for: Union[Callable, str] = None,
               _suppress_errors: bool = None,
               **kv_pairs
               ) -> Optional[str]:
        """
        Interpolate text with values from maps and kwds given.

        :param text:
            the text to interpolate; if null/empty, returned as is
        :param maps:
            a list of dictionaries/objects/HasTraits from which to draw
            items/attributes/trait-values, all in increasing priority.
            Nulls ignored.
        :param _stub_keys:
            - If false, missing keys raise KeyError.
            - If `True`, any missing *key* gets replaced by ``{key}``
              (practically remain unchanged).
            - If callable, the `key` is passed to it as a the only arg, and
              the result gets replaced.
            - Any other non-false value is returned for every *key*.
        :param _suppress_errors:
            ignore any interpolation errors and return original string
        :param _escaped_for:
            a callable or ('glob'|'regex') to escape object's attribute values

        Later maps take precedence over earlier ones; `kv_pairs` have the highest,
        but `_stub_keys` the lowest (if true).
        """
        if not text:
            return text

        with self.ikeys(*maps, _stub_keys=_stub_keys,
                        _escaped_for=_escaped_for,
                        **kv_pairs) as cntx:
            if _suppress_errors:
                try:
                    text = text.format_map(cntx)
                except Exception as ex:
                    log.debug("Interpolating '%s' failed due to: %r",
                              text[:100], ex, exc_info=ex)
            else:
                text = text.format_map(cntx)

            return text
