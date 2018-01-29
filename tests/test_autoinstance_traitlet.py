# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""Tests for AutoInstance traitlet."""

import pytest
from traitlets import List, Instance, CInt
from traitlets.config import Configurable, Config

from multivers.autoinstance_traitlet import AutoList


class C(Configurable):
    i = CInt(config=True)


class A(Configurable):
    a = AutoList(Instance(C), config=True)


def test_smoke():
    cfg = Config({'A': {'a': [{'i': 1}, {}, Config(C={'i': 2})]}})
    a = A(config=cfg)
    assert [1, 0, 2] == [e.i for e in a.a]


simple_nesting = [
    ## Empties ignore defaults in parents.
    ({'A': {'a': []}}, None),
    ({'A': {'a': [], 'C': {'i': -2}}}, None),
    ({'A': {'a': []}, 'C': {'i': -1}}, None),
    ({'A': {'a': [], 'C': {'i': -2}}, 'C': {'i': -1}}, None),

    ## Defaults in parents.
    ({'A': {'a': [{}], 'C': {'i': -2}}}, -2),
    ({'A': {'a': [{}]}, 'C': {'i': -1}}, -1),
    ({'A': {'a': [{}], 'C': {'i': -2}}, 'C': {'i': -1}}, -2),

    ({'A': {'a': [{}, {}], 'C': {'i': -2}}}, [-2, -2]),
    ({'A': {'a': [{}, {}]}, 'C': {'i': -1}}, [-1, -1]),
    ({'A': {'a': [{}, {}], 'C': {'i': -2}}, 'C': {'i': -1}}, [-2, -2]),

    ## Elements override defaults
    ({'A': {'a': [{'i': 2}]}}, 2),
    ({'A': {'a': [{'i': 2}], 'C': {'i': -2}}}, 2),
    ({'A': {'a': [{'i': 2}]}, 'C': {'i': -1}}, 2),
    ({'A': {'a': [{'i': 2}], 'C': {'i': -2}}, 'C': {'i': -1}}, 2),
    ({'A': {'a': [{'i': 2}, {'i': 3}, {'i': 1}], 'C': {'i': -2}}, 'C': {'i': -1}}, [2, 3, 1]),

    ## Multiple elements + defaults
    ({'A': {'a': [{}, {'i': 1}]}}, [0, 1]),
    ({'A': {'a': [{}, {'i': 1}], 'C': {'i': -2}}}, [-2, 1]),
    ({'A': {'a': [{}, {'i': 1}]}, 'C': {'i': -1}}, [-1, 1]),

    ({'A': {'a': [{}, {'i': 1}, {}]}}, [0, 1, 0]),
    ({'A': {'a': [{}, {'i': 1}], 'C': {'i': -2}}}, [-2, 1, -2]),
    ({'A': {'a': [{}, {'i': 1}]}, 'C': {'i': -1}}, [-1, 1, -1]),

]


@pytest.mark.parametrize('cfg, exp', simple_nesting)
def test_simple_merge(cfg, exp):
    a = A(config=Config(cfg))

    if exp is None:
        assert len(a.a) == 0, cfg
    elif isinstance(exp, list):
        assert exp == [e.i for e in a.a], cfg
    else:
        assert a.a[0].i == exp, cfg


class B(Configurable):
    b = Instance(C, config=True)
    bb = CInt()


class AA(Configurable):
    aa = AutoList(Instance(B), config=True)


recursive_nesting = [
    ({'AA': {
        'aa': [{'b': {'i': 2}, 'bb': 2}, ],
        'B': {'b': {'i': -2}}},
        'B': {'b': {'i': -1}}}, 2),
]


@pytest.mark.parametrize('cfg, exp', recursive_nesting)
def test_recursive_merge(cfg, exp):
    a = AA(config=Config(cfg))
    if exp is None:
        assert len(a.aa) == 0, cfg
    elif isinstance(exp, list):
        assert exp == [e.i for e in a.a], cfg
    else:
        assert a.aa[0].b.i == exp, cfg
