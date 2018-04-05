#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from collections import OrderedDict, defaultdict
from polyvers.utils import yamlutil as yu
import io

import pytest


@pytest.mark.parametrize('inp, exp', [
    (None, ''),
    ({}, ''),
    ([], ''),
    (OrderedDict(a=1), "a: 1"),
    (defaultdict(list, a='1'), "a: '1'"),

])
def test_yaml_dump(inp, exp):
    got = yu.ydumps(inp)
    assert got == exp

    sio = io.StringIO()
    yu.ydumps(inp, sio)
    got = sio.getvalue()
    assert got.strip() == exp
