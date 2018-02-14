#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Tests for `polyvers` package."""

from polyvers import polyverslib as pvlib

import pytest

import subprocess as subp


proj1 = 'proj1'
proj2 = 'proj-2'


def rfc2822_now():
    from datetime import datetime
    import email.utils as emu

    return emu.format_datetime(datetime.now())[:12]  # till hour


@pytest.fixture(scope="module")
def ok_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    cmds = """
    git init
    git commit --allow-empty  --no-edit -m some_msg
    git tag proj1-v0.0.0
    git commit --allow-empty  --no-edit -m some_msg
    git tag  proj1-v0.0.1
    git tag  proj-2-v0.2.0
    git commit --allow-empty  --no-edit -m some_msg
    git commit --allow-empty  --no-edit -m some_msg
    git tag proj-2-v0.2.1
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            pvlib.exec_cmd(c)

    return repo_dir


@pytest.fixture(scope="module")
def untagged_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    cmds = """
    git init
    git commit --allow-empty  --no-edit -m some_msg
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            pvlib.exec_cmd(c)

    return repo_dir


@pytest.fixture(scope="module")
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')


def test_get_all_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.find_all_subproject_vtags()
    assert dict(v) == {
        proj1: ['0.0.0', '0.0.1'],
        proj2: ['0.2.0', '0.2.1'],
    }, v

    untagged_repo.chdir()

    v = pvlib.find_all_subproject_vtags()
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.find_all_subproject_vtags()


def test_get_p1_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.find_all_subproject_vtags(proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}, v

    untagged_repo.chdir()

    v = pvlib.find_all_subproject_vtags(proj1)
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.find_all_subproject_vtags(proj1)


def test_get_p2_vtags(ok_repo):
    ok_repo.chdir()
    v = pvlib.find_all_subproject_vtags(proj2)
    assert dict(v) == {proj2: ['0.2.0', '0.2.1']}, v


def test_get_BAD_project_vtag(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.find_all_subproject_vtags('foo')
    assert dict(v) == {}, v

    v = pvlib.find_all_subproject_vtags('foo', proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}, v

    untagged_repo.chdir()

    v = pvlib.find_all_subproject_vtags('foo', 'bar')
    assert dict(v) == {}, v

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.find_all_subproject_vtags('foo')


def test_get_subproject_versions(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.get_subproject_versions()
    assert v == {
        proj1: '0.0.1',
        proj2: '0.2.1',
    }, v

    untagged_repo.chdir()

    v = pvlib.get_subproject_versions()
    assert v == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.get_subproject_versions()

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.get_subproject_versions('foo')

    with pytest.raises(subp.CalledProcessError):
        v = pvlib.get_subproject_versions('foo' 'bar')


def test_get_BAD_projects_versions(ok_repo):
    ok_repo.chdir()
    v = pvlib.get_subproject_versions('foo')
    assert dict(v) == {}, v


##############
## DESCRIBE ##
##############

def test_describe_project_p1(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.describe_project(proj1)
    assert v.startswith('proj1-v0.0.1')
    v, d = pvlib.describe_project(proj1, tag_date=True)
    assert v.startswith('proj1-v0.0.1')
    assert d.startswith(rfc2822_now())

    untagged_repo.chdir()

    v = pvlib.describe_project('foo')
    assert not v
    v, d = pvlib.describe_project('foo', tag_date=True)
    assert not v
    assert not d

    no_repo.chdir()

    v = pvlib.describe_project(proj1)
    assert v == '<git-error>'

    v = pvlib.describe_project(proj1, debug=True)
    assert 'Not a git repository' in v

    v, d = pvlib.describe_project(proj1, tag_date=True, debug=True)
    assert 'Not a git repository' in v
    assert not d


def test_describe_project_p2(ok_repo):
    ok_repo.chdir()

    v = pvlib.describe_project(proj2)
    assert v.startswith('proj-2-v0.2.1')
    v, d = pvlib.describe_project(proj2, tag_date=True)
    assert d.startswith(rfc2822_now())


def test_describe_project_BAD(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.describe_project('foo')
    assert not v
    v, d = pvlib.describe_project('foo', tag_date=True)
    assert not v
    assert not d

    untagged_repo.chdir()

    v = pvlib.describe_project('foo')
    assert not v
    v, d = pvlib.describe_project('foo', tag_date=True)
    assert not v
    assert not d

    no_repo.chdir()

    v = pvlib.describe_project('foo')
    assert v == '<git-error>'

    v, d = pvlib.describe_project('foo', tag_date=True)
    assert v == '<git-error>'
    assert not d

##############
##   MAIN   ##
##############


def test_MAIN_get_all_versions(ok_repo, no_repo, capsys):
    ok_repo.chdir()
    pvlib.main()
    out, err = capsys.readouterr()
    assert out == 'proj-2: 0.2.1\nproj1: 0.0.1\n'
    assert not err

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError) as excinfo:
        pvlib.main()
    assert 'Not a git repository' in str(excinfo.value.stderr)


def test_MAIN_get_project_versions(ok_repo, no_repo, capsys):
    ok_repo.chdir()
    pvlib.main(proj1, proj2)
    out, err = capsys.readouterr()
    assert out == 'proj-2: 0.2.1\nproj1: 0.0.1\n'
    assert not err

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError) as excinfo:
        pvlib.main()
    assert 'Not a git repository' in str(excinfo.value.stderr)


def test_MAIN_describe_projects(ok_repo, no_repo, capsys):
    ok_repo.chdir()
    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out.startswith('proj1-v0.0.1')
    assert not err

    ok_repo.chdir()
    pvlib.main(proj2)
    out, err = capsys.readouterr()
    assert out.startswith('proj-2-v0.2.1')
    assert not err

    no_repo.chdir()
    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out == '<git-error>\n'
    assert err
