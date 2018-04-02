#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers._vendor.traitlets import traitlets as trt
import pytest


exp_tuple, exp_list, exp_int, exp_tuple_assign = (
    dict(expected_exception=trt.TraitError, match="expeted a tuple"),
    dict(expected_exception=trt.TraitError, match="expeted a list"),
    dict(expected_exception=trt.TraitError, match="expeted an int"),
    dict(expected_exception=TypeError,
         match="'tuple' object does not support item assignment"))


@pytest.fixture
def recursed_trait():
    recursed_trait = trt.Tuple(trt.Int(), trt.List())
    recursed_trait._traits[1]._trait = recursed_trait

    return recursed_trait


@pytest.fixture
def eventful_trait():
    recursed_trait = trt.Tuple(trt.Int(), trt.List(eventful=True))
    recursed_trait._traits[1]._trait = recursed_trait

    return recursed_trait


def test_recursed_traitlets_class_definition(recursed_trait):
    ## Class definition will crash if not recursion broken!
    class C(trt.HasTraits):
        t = recursed_trait


def test_recursed_traitlets_construct(recursed_trait):
    class C(trt.HasTraits):
        t = recursed_trait

    ## GOOD
    #
    c = C(t=(1, []))
    assert c.t == (1, [])
    c = C(t=(1, [(22, [(333, [])])]))
    assert c.t == (1, [(22, [(333, [])])])

    ## Default-value is invalid(!),
    #  but validated on 1st access.
    #
    with pytest.raises(trt.TraitError, match="because a length 2"):
        C().t

    ## Test BAD constructors.
    #
    with pytest.raises(**exp_tuple):
        C(t='jj')
    with pytest.raises(**exp_list):
        C(t=(1, 'jj'))
    with pytest.raises(**exp_int):
        C(t=('kk', []))
    with pytest.raises(**exp_tuple):
        C(t=(1, ['jj']))
    with pytest.raises(**exp_list):
        C(t=(1, [(22, 'jj')]))
    with pytest.raises(**exp_int):
        C(t=(1, [('kk', [])]))


def test_recursed_traitlets_assign(recursed_trait):
    class C(trt.HasTraits):
        t = recursed_trait

    c = C()

    ## GOOD
    #
    c.t = (1, [])
    assert c.t == (1, [])

    c.t[1].append((22, []))
    c.t[1].append((33, []))
    assert c.t == (1, [(22, []), (33, [])])

    c.t = (1, [])
    with pytest.raises(trt.TraitError):
        c.t = (1, [(22, [(333, 'ha')])])
    assert c.t == (1, [])

    ## Test BAD assignments.
    #
    c = C(t=(1, []))
    with pytest.raises(**exp_tuple):
        c.t = 'jj'
    assert c.t == (1, [])
    with pytest.raises(**exp_tuple):  # check repeat?
        c.t = 'jj'
    assert c.t == (1, [])

    c.t = (1, [(22, []), (33, [])])
    with pytest.raises(**exp_tuple_assign):
        c.t[1][0][0] = 'jj'
    c.t = (1, [(22, []), (33, [])])
    with pytest.raises(**exp_tuple_assign):  # check repeat?
        c.t[1][0][1] = 'jj'
    assert c.t == (1, [(22, []), (33, [])])


def test_recursed_traitlets_no_event(recursed_trait):
    class C(trt.HasTraits):
        t = recursed_trait

    ## BAD modifications ACCEPTED!!
    #
    c = C(t=(1, []))
    c.t[1].append('jj')

    c.t = (1, [(22, []), (33, [])])
    c.t[1][0][1].append('jj')


def test_recursed_traitlets_eventful(eventful_trait):
    class C(trt.HasTraits):
        t = eventful_trait

    c = C(t=(1, []))
    with pytest.raises(**exp_tuple) as exinfo:
        c.t[1].append('jj')
    assert "because a length 2" not in str(exinfo.value)
    assert c.t != (1, [])  # WARNING: list modified!

    c = C(t=(1, []))
    with pytest.raises(**exp_int) as exinfo:
        c.t[1].append(('jj', []))
    assert "because a length 2" not in str(exinfo.value)
    assert c.t != (1, [])  # WARNING: list modified!

    c = C(t=(1, []))
    with pytest.raises(**exp_list) as exinfo:
        c.t[1].append((1, 'jj'))
    assert "because a length 2" not in str(exinfo.value)
    assert c.t != (1, [])  # WARNING: list modified!

    c = C(t=(1, []))
    with pytest.raises(**exp_tuple) as exinfo:
        c.t[1].append((1, ['jj']))
    assert "because a length 2" not in str(exinfo.value)
    assert c.t != (1, [])  # WARNING: list modified!

    c = C(t=(1, []))
    with pytest.raises(**exp_list) as exinfo:
        c.t[1].append((1, [(1, 'jj')]))
    assert "because a length 2" not in str(exinfo.value)
    assert c.t != (1, [])  # WARNING: list modified!
