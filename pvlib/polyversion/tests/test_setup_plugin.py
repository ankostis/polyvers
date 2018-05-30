#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import pytest
import setuptools


## NOTE: Requires this project to be `pip install`-ed.
@pytest.mark.parametrize('kw, exp', [
    ([], r"`polyversion` must be boolean or a dict mapping!"),
    (object(), r"`polyversion` must be boolean or a dict mapping!"),
    ({'BAD': 'OK'}, r"`polyversion` must be boolean or a dict mapping!"),
    ({'version_scheme': 'bad'}, r"`polyversion.version_scheme` must be one of "),
    ({'git_options': 'bad'}, r"`polyversion.git_options` must be an iterable"),

    # Why sometimes getting 'invalid' msg ??
    (True, (r"invalid command name", 'usage:')),
    ({}, (r"invalid command name", 'usage:')),
])
def test_invalid_config(kw, exp):
    with pytest.raises(SystemExit) as ex:
        setuptools.setup(
            project='pname',
            polyversion=kw,
            setup_requires=['polyversion'],
        )

    ## Check if any msg match
    #
    if isinstance(exp, str):
        exp = (exp, )
    last_ex = None
    for msg in exp:
        try:
            assert msg in str(ex)
            return
        except Exception as ex2:
            last_ex = ex2

    if last_ex:
        raise last_ex
