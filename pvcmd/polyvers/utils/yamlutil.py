#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""YAML utils."""
#: YAML dumper used e.g. to serialize command's outputs.

from _collections import defaultdict, OrderedDict as odict
from typing import Optional
import io
import pathlib
import textwrap as tw

from .._vendor import traitlets as trt


class YAMLable(metaclass=trt.MetaHasTraits):
    """A `HasTraits` mixin to denote to yaml-representer to dump all traits as dict values."""
    @staticmethod
    def _YAML_represent(dumper, data):
        from ..cmdlet import traitquery
        from ruamel.yaml import scalarstring as scs

        def wrap_any_text(v):
            if isinstance(v, str) and '\n' in v and len(v) > 32:
                return scs.preserve_literal(tw.dedent(v.replace('\r\n', '\n')
                                                      .replace('\r', '\n'))
                                            .strip())
            return v

        tnames = traitquery.select_traits(data, YAMLable,
                                          config=True)
        #cls_name = getattr(data, 'name', type(data).__name__)
        ddict = {tname: wrap_any_text(getattr(data, tname))
                 for tname in tnames}
        return _get_yamel().representer.represent_dict(ddict)


def _init_yaml():
    from ruamel import yaml
    from ruamel.yaml.representer import RoundTripRepresenter

    def _represent_path(_dumper, path):
        return y.representer.represent_str(str(path))

    y = yaml.YAML(typ='rt')

    yaddrepr = y.representer
    for d in [odict, defaultdict]:
        yaddrepr.add_representer(d, RoundTripRepresenter.represent_dict)

    yaddrepr.add_multi_representer(pathlib.Path, _represent_path)
    yaddrepr.add_multi_representer(YAMLable, YAMLable._YAML_represent)

    return y


_Y = None


def _get_yamel():
    global _Y

    if not _Y:
        _Y = _init_yaml()

    return _Y


def ydumps(obj, sink=None) -> Optional[str]:
    "Dump any false objects as empty string, None as nothing, or as YAML. "

    if not obj:
        if sink:
            sink.write('')
            return  # type: ignore
        return ''

    dump_to_str = not bool(sink)
    if dump_to_str:
        sink = io.StringIO()

    _get_yamel().dump(obj, sink)

    if dump_to_str:
        return sink.getvalue().strip()


def yloads(text):
    "Dump any false objects as empty string, None as nothing, or as YAML. "

    if not text:
        return

    return _get_yamel().load(text)
