#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import sys

import pytest
import setuptools
import subprocess as sbp


_exp_bad_args = "error in setup command: invalid polyversion args due to: "


def call_setup(pv, skip_check=None):
    setuptools.setup(
        project='pname',
        polyversion=pv,
        skip_polyversion_check=skip_check,
        setup_requires=['polyversion'],
        packages=['pypak'],
    )


## NOTE: Requires `polyversion` lib to be ``pip install -e pvlib``.
@pytest.mark.parametrize('kw, exp', [
    ([1], _exp_bad_args + "cannot convert dictionary"),
    (object(), _exp_bad_args + "'object' object is not iterable"),
    ({'BAD': 'OK'}, _exp_bad_args + "'SetupKeyword' object has no attribute 'BAD'"),
    ({'git_options': True},
     r"error in setup command: "
     "invalid polyversion `git_options` due to: "
     "'bool' object is not iterable"),

    (True, None),
    ({}, None),
    ([], None),  # empty kv-pair list
])
def test_invalid_config(kw, exp, ok_repo, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ('setup.py', 'clean'))
    ok_repo.chdir()

    if exp:
        with pytest.raises(SystemExit, match=exp):
            call_setup(kw)
    else:
        call_setup(kw)


@pytest.mark.parametrize('cmd, skip_check, rtagged, screams', [
    ('bdist', None, 0, True),
    ('bdist_dumb', False, 0, True),

    ('clean', None, 0, False),
    ('clean', True, 0, False),
    ('clean', None, 1, False),
    ('clean', True, 1, False),

    ('bdist_dumb', None, 1, False),
    ('bdist_dumb', True, 1, False),
])
def test_build_on_release_check(cmd, skip_check, rtagged, screams,
                                vtags_repo, rtagged_vtags_repo, monkeypatch):
    if rtagged:
        rtagged_vtags_repo.chdir()
    else:
        vtags_repo.chdir()

    monkeypatch.setattr(sys, 'argv', ('setup.py', cmd))
    if screams:
        with pytest.raises(SystemExit, match="Attempted to run '%s'" % cmd):
            call_setup(True, skip_check)
    else:
        call_setup(True, skip_check)

    monkeypatch.setattr(sys, 'argv', ('setup.py', 'clean'))

    setuptools.setup(
        project='pname',
        polyversion=True,
        skip_polyversion_check=False,
        setup_requires=['polyversion'],
    )

    monkeypatch.setattr(sys, 'argv', ('setup.py', 'bdist'))

    sbp.check_call('git commit --allow-empty  --no-edit -m r-c'.split())
    sbp.check_call('git tag  proj1-r0.0.1 -m annotated'.split())

    setuptools.setup(
        project='pname',
        polyversion=True,
        skip_polyversion_check=True,
        setup_requires=['polyversion'],
    )

    setuptools.setup(
        project='pname',
        polyversion=True,
        skip_polyversion_check=True,
        setup_requires=['polyversion'],
    )
