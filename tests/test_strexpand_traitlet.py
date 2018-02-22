# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

import pytest

from polyvers._vendor.traitlets import HasTraits, Unicode  # @UnresolvedImport
from polyvers.strexpand_traitlet import interpolating_unicodes


texts = [
    ('{key}', {'key': 123}, '123'),
    ('a{key}b', {'key': 123}, 'a123b'),

    ('foo', {}, 'foo'),
]


@pytest.mark.parametrize('s, ctxt, exp', texts)
def test_Unicode_interpolation(s, ctxt, exp):
    class C1(HasTraits):
        interpolation = ctxt
        s = Unicode()

    class C2(HasTraits):
        interpolation = lambda _, __, v: v.format(**ctxt)
        s = Unicode()

    class C3(HasTraits):
        interpolation = lambda _, __, v: v.format(**ctxt)
        s = Unicode().tag(no_interpolation=True)

    class C4(HasTraits):
        s = Unicode()

    assert C1(s=s).s == s
    assert C2(s=s).s == s
    assert C3(s=s).s == s
    assert C4(s=s).s == s

    with interpolating_unicodes():
        assert C1(s=s).s == exp
        assert C2(s=s).s == exp
        assert C3(s=s).s == s
        assert C4(s=s).s == s

    assert C1(s=s).s == s
    assert C2(s=s).s == s
    assert C3(s=s).s == s
    assert C4(s=s).s == s
