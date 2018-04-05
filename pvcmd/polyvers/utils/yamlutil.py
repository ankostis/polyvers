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


_Y = None


def _get_yamel():
    global _Y

    if not _Y:
        from ruamel import yaml
        from ruamel.yaml.representer import RoundTripRepresenter

        for d in [odict, defaultdict]:
            RoundTripRepresenter.add_representer(
                d, RoundTripRepresenter.represent_dict)
        _Y = yaml.YAML()

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
