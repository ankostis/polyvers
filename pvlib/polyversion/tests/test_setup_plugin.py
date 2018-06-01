#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import sys

import pytest
import setuptools
import subprocess as sbp


_exp_bad_args = "error in setup command: invalid polyversion args due to: "


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
def test_invalid_config(kw, exp, rtag_monorepo, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ('setup.py', 'clean'))  # PY3 fails with "invalid cmd"
    rtag_monorepo.chdir()

    if exp is None:
        setuptools.setup(
            project='pname',
            polyversion=kw,
            setup_requires=['polyversion'],
        )
    else:
        with pytest.raises(SystemExit, match=exp):
            setuptools.setup(
                project='pname',
                polyversion=kw,
                setup_requires=['polyversion'],
            )


def test_build_on_release_check(mutable_mono_project, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ('setup.py', 'bdist'))
    mutable_mono_project.chdir()

    with pytest.raises(SystemExit, match="Attempted to run 'bdist'"):
        setuptools.setup(
            project='pname',
            polyversion=True,
            setup_requires=['polyversion'],
        )

    monkeypatch.setattr(sys, 'argv', ('setup.py', 'bdist_dumb'))
    with pytest.raises(SystemExit, match="Attempted to run 'bdist_dumb'"):
        setuptools.setup(
            project='pname',
            polyversion=True,
            setup_requires=['polyversion'],
        )

    setuptools.setup(
        project='pname',
        polyversion=True,
        skip_polyversion_check=True,
        setup_requires=['polyversion'],
    )

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
