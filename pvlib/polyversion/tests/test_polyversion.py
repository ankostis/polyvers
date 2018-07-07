#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import fnmatch
import os
import re
import sys

import pytest

import os.path as osp
import polyversion as pvlib
import subprocess as sbp


PY_OLD_SBP = sys.version_info < (3, 5)

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
        'v',
        pname=r'[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9]'))
    if exp is None:
        with pytest.raises(ValueError):
            pvlib.split_pvtag(inp, [pvtag_regex])
    else:
        got = pvlib.split_pvtag(inp, [pvtag_regex])
        assert got == exp


@pytest.mark.parametrize('inp, exp', split_pvtag_validation_patterns)
def test_fnmatch_format(inp, exp):
    if exp is None:
        pass
    else:
        project = exp[0]
        frmt = pvlib._interp_fnmatch(pvlib.pvtag_format, 'v', project)
        assert fnmatch.fnmatch(inp, frmt)


def test_caller_fpath():
    caller_dir = pvlib._caller_srcpath(1)
    exp = osp.join(osp.dirname(__file__), '..')
    assert os.stat(caller_dir) == os.stat(exp)

    caller_dir = pvlib._caller_srcpath(0)
    exp = osp.join(osp.dirname(__file__), '..')
    ## Windows misses `osp.samefile()`,
    # see https://stackoverflow.com/questions/8892831/
    assert os.stat(caller_dir) == os.stat(exp)


def test_caller_module():
    caller_mod = pvlib._caller_module_name(1)
    assert caller_mod == __name__.split('.')[-1]


##############
## DESCRIBE ##
##############

def test_polyversion_p1(ok_repo, untagged_repo, no_repo):
    ## OK REPO

    v = pvlib.polyversion(pname=proj1, basepath=ok_repo)
    assert v.startswith(proj1_ver)
    v = pvlib.polyversion(pname=proj1, default_version='<unused>', basepath=ok_repo)
    assert v.startswith(proj1_ver)

    ## UNTAGGED REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion(pname='foo', default_version=None, basepath=untagged_repo)
    v = pvlib.polyversion(pname='foo', default_version='<unused>', basepath=untagged_repo)
    assert v == '<unused>'

    ## NO REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion(pname=proj1, default_version=None, basepath=no_repo)
    v = pvlib.polyversion(pname=proj1, default_version='<unused>', basepath=no_repo)
    assert v == '<unused>'


def test_polyversion_p2(ok_repo):
    v = pvlib.polyversion(pname=proj2, basepath=ok_repo,
                          tag_format='{pname}-V{version}',
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

    v = pvlib.polyversion(pname=proj1, basepath=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)
    v = pvlib.polyversion(pname=proj1, default_version='<unused>',
                          basepath=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)

    ## BAD PROJECT STILL WORKSREPO

    v = pvlib.polyversion(pname='foo', basepath=vtags_repo, mono_project=True)
    assert v.startswith(proj1_ver)

    ## bool flag overriden

    v = pvlib.polyversion(pname='fobar', basepath=vtags_repo, mono_project=False,
                          tag_format=pvlib.vtag_format,
                          tag_regex=pvlib.vtag_regex)
    assert v.startswith(proj1_ver)


def test_polyversion_BAD_project(ok_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion(pname='foo', default_version=None, basepath=ok_repo)
    v = pvlib.polyversion(pname='foo', default_version='<unused>', basepath=ok_repo)
    assert v == '<unused>'


def test_polyversion_BAD_no_commits(empty_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polyversion(pname='foo', default_version=None, basepath=empty_repo)
    v = pvlib.polyversion(pname='foo', default_version='<unused>', basepath=empty_repo)
    assert v == '<unused>'


def test_polyversion_BAD_env_var(no_repo, empty_repo, untagged_repo,
                                 monkeypatch):
    monkeypatch.setenv('foo_VERSION', '1.2.3')
    root = (no_repo / '/')

    for repo in [no_repo, empty_repo, untagged_repo]:
        root.chdir()
        assert pvlib.polyversion(pname='foo', basepath=repo) == '1.2.3'
        pvlib.polytime(pname='foo', basepath=repo)

        repo.chdir()
        assert pvlib.polyversion(pname='foo') == '1.2.3'
        pvlib.polytime(pname='foo', basepath=repo)


def test_polyversion_BAD_custom_env_var(no_repo, empty_repo, untagged_repo,
                                        monkeypatch):
    monkeypatch.setenv('PPP', '1.2.3')
    root = (no_repo / '/')

    for repo in [no_repo, empty_repo, untagged_repo]:
        root.chdir()
        assert pvlib.polyversion(pname='foo', basepath=repo,
                                 default_version_env_var='PPP') == '1.2.3'
        pvlib.polytime(pname='foo', basepath=repo,
                       default_version_env_var='PPP')
        pvlib.polytime(basepath=repo,
                       default_version_env_var='PPP')

        repo.chdir()
        assert pvlib.polyversion(pname='foo',
                                 default_version_env_var='PPP') == '1.2.3'
        pvlib.polytime(pname='foo', basepath=repo,
                       default_version_env_var='PPP')
        pvlib.polytime(basepath=repo,
                       default_version_env_var='PPP')


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_polyversion_BAD_no_git_cmd(ok_repo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvlib.polyversion(pname='foo', default_version=None, basepath=ok_repo)
    v = pvlib.polyversion(pname='foo', default_version='0.1.1', basepath=ok_repo)
    assert v == '0.1.1'


def test_polytime_p1(ok_repo, untagged_repo, no_repo, today):
    ## OK REPO

    d = pvlib.polytime(basepath=ok_repo)
    assert d.startswith(today)
    d = pvlib.polytime(no_raise=True, basepath=ok_repo)
    assert d.startswith(today)

    ## UNTAGGED REPO

    pvlib.polytime(basepath=untagged_repo)
    assert d.startswith(today)
    d = pvlib.polytime(no_raise=True, basepath=untagged_repo)
    assert d.startswith(today)

    ## NO REPO

    with pytest.raises(sbp.CalledProcessError):
        pvlib.polytime(basepath=no_repo)
    d = pvlib.polytime(no_raise=True, basepath=no_repo)
    assert d.startswith(today)


def test_polytime_p2(ok_repo, today):
    d = pvlib.polytime(basepath=ok_repo)
    assert d.startswith(today)


def test_polytime_BAD_no_commits(empty_repo):
    with pytest.raises(sbp.CalledProcessError):
        pvlib.polytime(basepath=empty_repo)


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_polytime_BAD_no_git_cmd(ok_repo, monkeypatch, today):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvlib.polytime(basepath=ok_repo)
    d = pvlib.polytime(no_raise=True, basepath=ok_repo)
    assert d.startswith(today)


##############
##   MAIN   ##
##############

def test_MAIN_polyversions(ok_repo, untagged_repo, no_repo, capsys, caplog):
    from polyversion import run
    ok_repo.chdir()

    run()
    out, err = capsys.readouterr()
    assert not out and not err
    assert not caplog.text

    run(proj1)
    out, err = capsys.readouterr()
    assert out.startswith(proj1_ver) and not err

    run(proj1, '-t')
    out, err = capsys.readouterr()
    assert not err
    assert out.startswith(proj1)
    assert proj1_ver[:-1] in out  # clip local-ver char

    run(proj1, 'foo')
    out, err = capsys.readouterr()
    assert re.match(
        r'proj1: 0\.0\.1\+2\.g[\da-f]+\nfoo:', out)
    #assert 'No names found' in caplog.text()

    run('-t', proj1, 'foo')
    out, err = capsys.readouterr()
    #'proj1: proj1-v0.0.1-2-gccff299\nfoo: \n
    assert re.match(
        r'proj1: proj1-v0\.0\.1\-2-g[\da-f]+\nfoo:', out)

    untagged_repo.chdir()
    git_err = '' if PY_OLD_SBP else 'fatal: No names found'

    run()
    out, err = capsys.readouterr()
    assert not out and not err
    with pytest.raises(sbp.CalledProcessError, match="'git', 'describe'"):
        run('foo')
    out, err = capsys.readouterr()
    assert not out and not err
    assert git_err in caplog.text
    caplog.clear()

    run('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n' and not err
    assert git_err in caplog.text
    caplog.clear()

    run('foo', '-t', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n' and not err
    assert git_err in caplog.text
    caplog.clear()

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        run(proj1)
    run('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n'
    #assert caplog.records()
