# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers._vendor.traitlets import traitlets as trt
from polyvers.interpctxt import Now, InterpolationContext, _HasTraitObjectDict, dictize_object

import pytest


def test_dates_interpolation():
    now_frmt = '{now:%Y-%m-%d %H:%M}'

    assert now_frmt.format_map({'now': Now()}) != now_frmt


def test_InterpolationContext():
    ctxt = InterpolationContext()

    s = 'stop the clock at {now}!'
    assert s.format_map(ctxt) != s

    assert ctxt.interp('Keys we have: {ikeys}') != 'Keys we have: {ikeys}'

    ctxt['A'] = '42'
    assert 'What? {A}'.format(**ctxt) == 'What? 42'


def test_interp_ikeys_key():
    ctxt = InterpolationContext()
    with ctxt.ikeys({'a': 1, 'bb': 2}):
        keys = '{ikeys}'.format_map(ctxt)

    keys = [k.strip() for k in keys.split(',')]
    assert set(keys) == set('utcnow ikeys a bb now'.split())


@pytest.mark.parametrize('maps, kw, exp', [
    ([{'a': 1}, {'a': 2}], {}, '2'),
    ([{'a': 1}, {'a': 2}], {'a': 3}, '3'),
])
def test_interp_temp_order(maps, kw, exp):
    ctxt = InterpolationContext()
    ctxt.maps.append({'c': 3})

    with ctxt.ikeys(*maps, **kw):
        assert ctxt.interp('{a}') == exp
        assert '{c}'.format_map(ctxt) == '3'

    with ctxt.ikeys(*maps, **kw, stub_keys=True):
        assert ctxt.interp('{a}') == exp
        assert '{b}'.format_map(ctxt) == '{b}'
        assert '{c}'.format_map(ctxt) == '3'


def test_interp_temp_ikeys():
    frmt = "Lucky {b}! {a}."
    exp = "Lucky 13! Cool."

    with pytest.raises(KeyError):
        frmt.format()

    ctxt = InterpolationContext()
    with ctxt.ikeys(a='Cool', b=13) as ictxt:
        assert frmt.format_map(ictxt) == exp

    with pytest.raises(KeyError):
        frmt.format(**ictxt)

    with ctxt.ikeys({'b': 13, 'a': 'Cool'}) as ictxt:
        assert frmt.format(**ictxt) == exp
        assert frmt.format_map(ictxt) == exp

    with ctxt.ikeys(None, {'b': 13, 'a': 'Cool'}, None, {}) as ictxt:
        assert frmt.format(**ictxt) == exp
        assert ictxt.interp(frmt) == exp

    with pytest.raises(KeyError):
        frmt.format(**ictxt)

    with ctxt.ikeys({'b': 13}, a='Cool') as ictxt:
        assert frmt.format(**ictxt) == exp
        assert frmt.format_map(ictxt) == exp

    with ctxt.ikeys({'b': 14}, a='Cool', b='13') as ictxt:
        assert frmt.format(**ictxt) == exp
        assert ictxt.interp(frmt) == exp

    with pytest.raises(KeyError):
        frmt.format(**ictxt)


def test_interp_missing_ikeys():
    frmt = "{missing} key"

    with pytest.raises(KeyError):
        frmt.format()

    ctxt = InterpolationContext()

    with ctxt.ikeys(stub_keys=True) as ictxt:
        with pytest.raises(KeyError):
            assert frmt.format(**ictxt) == frmt
        assert frmt.format_map(ictxt) == frmt

    with ctxt.ikeys(stub_keys='no') as ictxt:
        with pytest.raises(KeyError):
            assert frmt.format(**ictxt) == frmt
        assert frmt.format_map(ictxt) == 'no key'

    with ctxt.ikeys(a=1, stub_keys=True) as ictxt:
        with pytest.raises(KeyError):
            assert frmt.format(**ictxt) == frmt
        assert frmt.format_map(ictxt) == frmt

    with ctxt.ikeys({'ff': 12}, stub_keys=True, a=1) as ictxt:
        with pytest.raises(KeyError):
            assert frmt.format(**ictxt) == frmt
        assert frmt.format_map(ictxt) == frmt

    with pytest.raises(KeyError):
        frmt.format()


def test_interp_on_objects():
    class C:
        a = 1

    ctxt = InterpolationContext()
    with ctxt.ikeys(C()):
        assert '{a}'.format_map(ctxt) == '1'

    c = C()
    c.b = 2
    with ctxt.ikeys(c):
        assert '{a}{b}'.format_map(ctxt) == '12'

    class D(C):
        d = 4

    d = D()
    d.c = 3
    with ctxt.ikeys(d) as ctxt:
        assert '{a}{c}{d}'.format_map(ctxt) == '134'

        with pytest.raises(KeyError):
            ctxt.interp('{b}')

    with ctxt.ikeys(C, d) as ctxt:
        assert '{a}{c}{d}'.format_map(ctxt) == '134'

        with pytest.raises(KeyError):
            '{b}'.format_map(ctxt)


def test_ikeys_key_on_objects():
    class C:
        aa = 1

    c = C()
    c.bb = 2

    ctxt = InterpolationContext()
    with ctxt.ikeys(c):
        keys = '{ikeys}'.format_map(ctxt)

    keys = [k.strip() for k in keys.split(',')]
    assert 'aa' in keys and 'bb' in keys


def test_dictize_object_on_HasTraitObjectDict():
    class C(trt.HasTraits):
        a = trt.Int(1)

    od = _HasTraitObjectDict(C())
    assert dictize_object(od) is od


def test_interp_on_HasTraits():
    class C(trt.HasTraits):
        a = trt.Int(1)
        b = trt.Int()

        @trt.default('b')
        def _make_b(self):
            return 2

    c = C()
    c.c = 3
    ctxt = InterpolationContext()
    with ctxt.ikeys(C()):
        assert '{a}{b}'.format_map(ctxt) == '12'

    with pytest.raises(KeyError):
        assert '{c}'.format_map(ctxt)

    class D(C):
        d = trt.Int(4)
        e = trt.Int()

    d = D()
    d.e = 5
    d.f = 6
    with ctxt.ikeys(d) as ctxt:
        assert '{a}{b}{d}{e}'.format_map(ctxt) == '1245'

        with pytest.raises(KeyError):
            assert '{c}'.format_map(ctxt)
        with pytest.raises(KeyError):
            assert ctxt.interp('{f}')


def test_ikeys_key_on_HasTraits():
    class C(trt.HasTraits):
        aa = trt.Int(1)
        a = 0

    c = C()
    c.b = 2

    ctxt = InterpolationContext()
    with ctxt.ikeys(c):
        keys = '{ikeys}'.format_map(ctxt)

    keys = [k.strip() for k in keys.split(',')]
    assert 'aa' in keys
    badkeys = (set(['a', 'b']) & set(keys))
    assert not badkeys

    class D(C):
        d = trt.Int(4)
        e = trt.Int()

    d = D()
    d.e = 5
    d.f = 6

    with ctxt.ikeys(d):
        keys = '{ikeys}'.format_map(ctxt)

    keys = [k.strip() for k in keys.split(',')]
    assert 'aa' in keys
    badkeys = (set(['a', 'b']) & set(keys))
    assert not badkeys
