# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""Tests for AutoInstance traitlet."""

import pytest

from traitlets import HasTraits
from polyvers.strexpand_traitlet import StrExpand


texts = [
    ('{key}', {'key': 123}, '123'),
    ('a{key}b', {'key': 123}, 'a123b'),
]
@pytest.mark.parametrize('s, ctxt, exp', texts)
def test_StrExpand(s, ctxt, exp):
    class C1(HasTraits):
        s = StrExpand(ctxt=ctxt)
    assert C1(s=s).s == exp, (s, ctxt, exp)

    class C2(HasTraits):
        s = StrExpand(ctxt={})
    assert C2(s=s).s == s, s

    class C3(HasTraits):
        s = StrExpand(ctxt=lambda _, __, ____: ctxt)
    assert C3(s=s).s == exp, (s, ctxt, exp)

    class C4(HasTraits):
        s = StrExpand(ctxt=lambda _, __, ___: {})
    assert C4(s=s).s == s, s

