#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import sys

import pytest
import setuptools


## NOTE: Requires this project to be `pip install`-ed.
@pytest.mark.parametrize('kw, exp', [
    ([], r"`polyversion` must be boolean or a dict mapping!"),
    (object(), r"`polyversion` must be boolean or a dict mapping!"),
    ({'BAD': 'OK'}, r"`polyversion` must be boolean or a dict mapping!"),
    ({'version_scheme': 'bad'}, r"`polyversion.version_scheme` must be one of "),
    ({'git_options': 'bad'}, r"`polyversion.git_options` must be an iterable"),

    (True, 'usage:'),
    ({}, 'usage:'),
])
def test_invalid_config(kw, exp, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ('setup.py', ))  # PY3 fails with "invalid cmd"
    with pytest.raises(SystemExit, match=exp):
        setuptools.setup(
            project='pname',
            polyversion=kw,
            setup_requires=['polyversion'],
        )
