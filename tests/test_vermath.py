#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import vermath

import pytest


@pytest.mark.parametrize('v1, v2, exp', [
    ('1.1.1', '0.1.2', '1.2.3'),
    ('0.0', '1.1.1', '1.1.1'),
    ('1.1.1', '0.0', '1.1.1'),

    ('0.0.dev1', '0.0.dev2', '0.0.dev3'),
    ('1.1.dev2', '0.0.0.dev2', '1.1.0.dev4'),
    ('1.1a1', '0.2.0a0', '1.3a1'),
    ('1.1.post3', '2.2.2.post1', '3.3.2.post4'),
])
def test_versions_addition(v1, v2, exp):
    from packaging.version import Version

    got = vermath.calc_versions_op('+', v1, v2)
    assert got == Version(exp)
