#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import pytest
import setuptools

## NOTE: Requires this project to be `pip install`-ed.


@pytest.mark.parametrize('kw, exp', [
    (True, r"invalid command name "),
    ([], r"`polyversion` must be boolean or a dict mapping!"),
    (object(), r"`polyversion` must be boolean or a dict mapping!"),
    ({'BAD': 'OK'}, r"`polyversion` must be boolean or a dict mapping!"),
    ({'version_scheme': 'bad'}, r"`polyversion.version_scheme` must be one of "),
    ({'git_options': 'bad'}, r"`polyversion.git_options` must be an iterable"),
    #({}, r"usage: setup.py"),
    ({}, r"invalid command name "),
])
def test_invalid_config(kw, exp):
    with pytest.raises(SystemExit,
                       match=exp):
        setuptools.setup(
            project='pname',
            polyversion=kw,
            setup_requires=['polyversion'],
        )
