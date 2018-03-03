# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.interpctxt import Now, InterpolationContextManager

import pytest


def test_dates_interpolation():
    now_frmt = '{now:%Y-%m-%d %H:%M}'

    assert now_frmt.format_map({'now': Now()}) != now_frmt


def test_InterpolationContextManager():
    ctxt = InterpolationContextManager().ctxt

    s = 'stop the clock at {now}!'
    assert s.format_map(ctxt) != s

    assert 'Keys we have: {ikeys}'.format_map(ctxt) != 'Keys we have: {ikeys}'

    ctxt['A'] = '42'
    assert 'What? {A}'.format(**ctxt) == 'What? 42'


def test_InterpolationContextManager_temp_ikeys():
    frmt = "Lucky {b}!"

    with pytest.raises(KeyError):
        frmt.format()

    ctxtman = InterpolationContextManager()
    with ctxtman.ikeys(b=13) as ictxt:
        assert frmt.format(**ictxt) == "Lucky 13!"
        assert frmt.format_map(ictxt) == "Lucky 13!"

    with pytest.raises(KeyError):
        frmt.format(**ictxt)


def test_InterpolationContextManager_temp_imaps():
    frmt = "Lucky {b}!"

    with pytest.raises(KeyError):
        frmt.format()

    ctxtman = InterpolationContextManager()
    with ctxtman.imaps({'b': 13}) as ictxt:
        assert frmt.format(**ictxt) == "Lucky 13!"
        assert frmt.format_map(ictxt) == "Lucky 13!"

    with pytest.raises(KeyError):
        frmt.format(**ictxt)
