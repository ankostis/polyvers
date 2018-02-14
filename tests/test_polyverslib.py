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


@pytest.fixture(scope="module")
def git_repo(tmpdir_factory):
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
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')


def test_get_all_vtags(git_repo, no_repo):
    git_repo.chdir()
    d = pvlib.find_all_subproject_vtags()
    assert dict(d) == {
        proj1: ['0.0.0', '0.0.1'],
        proj2: ['0.2.0', '0.2.1'],
    }, d

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError):
        d = pvlib.find_all_subproject_vtags()


def test_get_p1_vtags(git_repo, no_repo):
    git_repo.chdir()
    d = pvlib.find_all_subproject_vtags(proj1)
    assert dict(d) == {proj1: ['0.0.0', '0.0.1']}, d

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError):
        d = pvlib.find_all_subproject_vtags(proj1)


def test_get_p2_vtags(git_repo, no_repo):
    git_repo.chdir()
    d = pvlib.find_all_subproject_vtags(proj2)
    assert dict(d) == {proj2: ['0.2.0', '0.2.1']}, d

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError):
        d = pvlib.find_all_subproject_vtags(proj2)


def test_get_subproject_versions(git_repo, no_repo):
    git_repo.chdir()
    d = pvlib.get_subproject_versions()
    assert d == {
        proj1: '0.0.1',
        proj2: '0.2.1',
    }, d

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError):
        d = pvlib.get_subproject_versions()


def test_describe_project_p1(git_repo, no_repo):
    from datetime import datetime
    import email.utils as emu

    git_repo.chdir()
    v = pvlib.describe_project(proj1)
    assert v.startswith('proj1-v0.0.1')

    git_repo.chdir()
    v, d = pvlib.describe_project(proj1, date=True)
    assert v.startswith('proj1-v0.0.1')
    assert d.startswith(emu.format_datetime(datetime.now())[:12])  # till hour

    no_repo.chdir()
    v = pvlib.describe_project(proj1)
    assert v == '<git-error>'

    v = pvlib.describe_project(proj1, debug=True)
    assert 'Not a git repository' in v


def test_describe_project_p2(git_repo, no_repo):
    git_repo.chdir()
    v = pvlib.describe_project(proj2)
    assert v.startswith('proj-2-v0.2.1')


def test_MAIN_get_all_versions(git_repo, no_repo, capsys):
    git_repo.chdir()
    pvlib.main()
    out, err = capsys.readouterr()
    assert out == 'proj-2: 0.2.1\nproj1: 0.0.1\n'
    assert not err

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError) as excinfo:
        pvlib.main()
    assert 'Not a git repository' in str(excinfo.value.stderr)


def test_MAIN_get_project_versions(git_repo, no_repo, capsys):
    git_repo.chdir()
    pvlib.main(proj1, proj2)
    out, err = capsys.readouterr()
    assert out == 'proj-2: 0.2.1\nproj1: 0.0.1\n'
    assert not err

    no_repo.chdir()
    with pytest.raises(subp.CalledProcessError) as excinfo:
        pvlib.main()
    assert 'Not a git repository' in str(excinfo.value.stderr)


def test_MAIN_describe_projects(git_repo, no_repo, capsys):
    git_repo.chdir()
    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out.startswith('proj1-v0.0.1')
    assert not err

    git_repo.chdir()
    pvlib.main(proj2)
    out, err = capsys.readouterr()
    assert out.startswith('proj-2-v0.2.1')
    assert not err

    no_repo.chdir()
    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out == '<git-error>\n'
    assert err


