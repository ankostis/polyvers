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
