#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import polyverslib as pvlib
import fnmatch
import re
import sys

import pytest

import os.path as osp
import subprocess as sbp


proj1 = 'proj1'
proj1_ver = '0.0.1+'
proj2 = 'proj-2'
proj2_ver = '0.2.1'


split_pvtag_validation_patterns = [
    ('proj', None),
    ('proj-1.0.5', None),
    ('proj-1-0.5', None),
    ('proj-v1.0-gaffe', None),
    ('proj-v1', ('proj', '1', None)),
    ('pa-v1.2', ('pa', '1.2', None)),
    ('proj.name-v1.2.3', ('proj.name', '1.2.3', None)),
    ('proj-v1.3_name-v1.2.3', ('proj-v1.3_name', '1.2.3', None)),
    ('foo-bar-v00.0-1-g4f99a6f', ('foo-bar', '00.0', '1-g4f99a6f')),
    ('foo_bar-v00.0.dev1-1-g3fb1bfae20', ('foo_bar', '00.0.dev1', '1-g3fb1bfae20')),
]


@pytest.mark.parametrize('inp, exp', split_pvtag_validation_patterns)
def test_split_pvtag_parsing(inp, exp):
    pvtag_regex = re.compile(pvlib._interp_regex(
        pvlib.pvtag_regex,
        pname=r'[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9]'))
    if exp is None:
        with pytest.raises(ValueError):
            pvlib.split_pvtag(inp, pvtag_regex)
    else:
        got = pvlib.split_pvtag(inp, pvtag_regex)
        assert got == exp


@pytest.mark.parametrize('inp, exp', split_pvtag_validation_patterns)
def test_fnmatch_format(inp, exp):
    if exp is None:
        pass
    else:
        project = exp[0]
        frmt = pvlib._interp_fnmatch(pvlib.pvtag_frmt, project)
        assert fnmatch.fnmatch(inp, frmt)


def test_caller_fpath():
    caller_dir = pvlib._caller_fpath(1)
    assert caller_dir == osp.dirname(__file__)

    caller_dir = pvlib._caller_fpath(0)
    exp = osp.join(osp.dirname(__file__), '..', 'polyvers')
    assert osp.realpath(exp) == caller_dir


##############
## DESCRIBE ##
##############

def test_polyversion_p1(ok_repo, untagged_repo, no_repo):
    ## OK REPO

    v = pvlib.polyversion(proj1, repo_path=ok_repo)
    assert v.startswith(proj1_ver)
    v = pvlib.polyversion(proj1, default='<unused>', repo_path=ok_repo)
    assert v.startswith(proj1_ver)

    ## UNTAGGED REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion('foo', repo_path=untagged_repo)
    v = pvlib.polyversion('foo', default='<unused>', repo_path=untagged_repo)
    assert v == '<unused>'

    ## NO REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion(proj1, repo_path=no_repo)
    v = pvlib.polyversion(proj1, default='<unused>', repo_path=no_repo)
    assert v == '<unused>'


def test_polyversion_p2(ok_repo):
    v = pvlib.polyversion(proj2, repo_path=ok_repo,
                          tag_frmt='{pname}-V{version}',
                          tag_regex=r"""(?xmi)
                              ^(?P<pname>{pname})
                              -
                              V(?P<version>\d[^-]*)
                              (?:-(?P<descid>\d+-g[a-f\d]+))?$
                          """,
                          git_options=['--tags'])
    assert v == proj2_ver


def test_polyversion_vtags(vtags_repo):
    ## OK REPO

    v = pvlib.polyversion(proj1, repo_path=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)
    v = pvlib.polyversion(proj1, default='<unused>', repo_path=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)

    ## BAD PROJECT STILL WORKSREPO

    v = pvlib.polyversion('foo', repo_path=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)

    ## bool flag overriden

    v = pvlib.polyversion('fobar', repo_path=vtags_repo, mono_project=False,
                          tag_frmt=pvlib.vtag_frmt,
                          tag_regex=pvlib.vtag_regex)
    assert v.startswith(proj1_ver)


def test_polyversion_BAD_project(ok_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion('foo', repo_path=ok_repo)
    v = pvlib.polyversion('foo', default='<unused>', repo_path=ok_repo)
    assert v == '<unused>'


def test_polyversion_BAD_no_commits(empty_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion('foo', repo_path=empty_repo)
    v = pvlib.polyversion('foo', default='<unused>', repo_path=empty_repo)
    assert v == '<unused>'


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_polyversion_BAD_no_git_cmd(ok_repo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvlib.polyversion('foo', repo_path=ok_repo)
    v = pvlib.polyversion('foo', '0.1.1', repo_path=ok_repo)
    assert v == '0.1.1'


def test_polytime_p1(ok_repo, untagged_repo, no_repo, today):
    ## OK REPO

    d = pvlib.polytime(repo_path=ok_repo)
    assert d.startswith(today)
    d = pvlib.polytime(no_raise=True, repo_path=ok_repo)
    assert d.startswith(today)

    ## UNTAGGED REPO

    pvlib.polytime(repo_path=untagged_repo)
    assert d.startswith(today)
    d = pvlib.polytime(no_raise=True, repo_path=untagged_repo)
    assert d.startswith(today)

    ## NO REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polytime(repo_path=no_repo)
    d = pvlib.polytime(no_raise=True, repo_path=no_repo)
    assert d.startswith(today)


def test_polytime_p2(ok_repo, today):
    d = pvlib.polytime(repo_path=ok_repo)
    assert d.startswith(today)


def test_polytime_BAD_no_commits(empty_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polytime(repo_path=empty_repo)


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_polytime_BAD_no_git_cmd(ok_repo, monkeypatch, today):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvlib.polytime(repo_path=ok_repo)
    d = pvlib.polytime(no_raise=True, repo_path=ok_repo)
    assert d.startswith(today)


##############
##   MAIN   ##
##############
# TODO: Move main from `pvlib` --> `polyvers.pvtgs`

def test_MAIN_polyversions(ok_repo, untagged_repo, no_repo, capsys):
    ok_repo.chdir()

    pvlib.main()
    out, err = capsys.readouterr()
    assert not out and not err

    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out.startswith(proj1_ver) and not err

    pvlib.main(proj1, 'foo')
    out, err = capsys.readouterr()
    assert re.match(
        r'proj1: 0\.0\.1\+2\.g[\da-f]+\nfoo:', out)
    #assert 'No names found' in caplog.text()

    untagged_repo.chdir()

    pvlib.main()
    out, err = capsys.readouterr()
    assert not out and not err
    with pytest.raises(sbp.CalledProcessError):
        pvlib.main('foo')
    pvlib.main('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n'
    #assert 'No names found' in caplog.text()

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        pvlib.main(proj1)
    pvlib.main('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n'
    #assert caplog.records()
