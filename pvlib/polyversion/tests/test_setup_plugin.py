#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import re
import sys

import pytest
import setuptools


_exp_bad_args = \
    "error in pname setup command: invalid content in `polyversion` keyword due to: "
_git_desc_cmd = re.escape(
    r"Command '['git', 'describe', '--match=pname-v*', '--match=pname-r*']' returned non-zero")


def call_setup(pv, **kwds):
    setuptools.setup(
        name='pname',
        polyversion=pv,
        setup_requires=['polyversion'],
        py_modules=['pypak'],
        **kwds
    )


## NOTE: Requires `polyversion` lib to be ``pip install -e pvlib``.
@pytest.mark.parametrize('kw, exp', [
    ([1], SystemExit(_exp_bad_args + "cannot convert dictionary")),
    (object(), SystemExit(_exp_bad_args + "'object' object is not iterable")),
    ({'BAD': 'OK'}, SystemExit(_exp_bad_args + r"extra keys \(BAD\)")),
    ({'git_options': True},
     TypeError(r"invalid `git_options` due to: 'bool' object is not iterable")),

    (True, Exception(_git_desc_cmd)),  # no monorepo
    ({}, Exception(_git_desc_cmd)),    # no monorepo
    ([], Exception(_git_desc_cmd)),    # no monorepo, empty kv-pair list

    ({'mono_project': True}, None),    # no monorepo, empty kv-pair list
])
def test_invalid_config(kw, exp, rtagged_vtags_repo, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ('setup.py', 'clean'))
    rtagged_vtags_repo.chdir()

    if exp:
        with pytest.raises(type(exp), match=str(exp)):
            call_setup(kw)
    else:
        call_setup(kw)


@pytest.mark.parametrize('cmd, check_enabled, rtagged, ex', [
    ('bdist', True, 0, "Attempted to run 'bdist'"),
    ('bdist_dumb', True, 0, "Attempted to run 'bdist_dumb'"),

    ('bdist_wheel', None, 0, None),

    ('clean', None, 0, None),
    ('clean', True, 0, None),
    ('clean', None, 1, None),
    ('clean', True, 1, None),

    ('bdist_dumb', None, 1, None),
    ('bdist_dumb', True, 1, None),
])
def test_build_on_release_check(cmd, check_enabled, rtagged, ex,
                                vtags_repo, rtagged_vtags_repo,
                                monkeypatch, capsys):
    pvargs = {'mono_project': True}
    myrepo = rtagged_vtags_repo if rtagged else vtags_repo
    myrepo.chdir()

    monkeypatch.setattr(sys, 'argv', ('setup.py', cmd))
    if ex:
        with pytest.raises(SystemExit, match=ex) as ex:
            call_setup(pvargs,
                       polyversion_check_bdist_enabled=check_enabled,
                       version='0.0.0')  # we don't check no `default_version`
        out, err = capsys.readouterr()
        assert not out and not err
    else:
        call_setup(pvargs,
                   polyversion_check_bdist_enabled=check_enabled,
                   version='0.0.0')
        out, err = capsys.readouterr()
        assert 'running %s' % cmd in out.strip()
        assert not err

        ## Test with cwd outside repo.
        #
        (myrepo / '..').chdir()
        call_setup(pvargs,
                   polyversion_check_bdist_enabled=check_enabled,
                   version='0.0.0',
                   package_dir={'': myrepo.basename})
        out, err = capsys.readouterr()
        assert 'running %s' % cmd in out.strip()
        assert not err
