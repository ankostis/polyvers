#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import pvtags
import sys

import pytest

import subprocess as sbp


proj1 = 'proj1'
proj1_desc = 'proj1-v0.0.1-2-g'
proj2 = 'proj-2'
proj2_desc = 'proj-2-v0.2.1'


@pytest.fixture()
def projspec():
    return pvtags.Project()


def test_get_all_pvtags(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = projspec.find_all_subproject_pvtags()
    assert dict(v) == {
        proj1: ['0.0.0', '0.0.1'],
        proj2: ['0.2.0', '0.2.1'],
    }
    untagged_repo.chdir()

    v = projspec.find_all_subproject_pvtags()
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.find_all_subproject_pvtags()


def test_get_p1_pvtags(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = projspec.find_all_subproject_pvtags(proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}
    untagged_repo.chdir()

    v = projspec.find_all_subproject_pvtags(proj1)
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.find_all_subproject_pvtags(proj1)


def test_get_p2_pvtags(projspec, ok_repo):
    ok_repo.chdir()
    v = projspec.find_all_subproject_pvtags(proj2)
    assert dict(v) == {proj2: ['0.2.0', '0.2.1']}


def test_get_BAD_project_pvtag(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = projspec.find_all_subproject_pvtags('foo')
    assert dict(v) == {}
    v = projspec.find_all_subproject_pvtags('foo', proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}

    untagged_repo.chdir()

    v = projspec.find_all_subproject_pvtags('foo', 'bar')
    assert dict(v) == {}
    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.find_all_subproject_pvtags('foo')


def test_get_subproject_versions(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = projspec.get_subproject_versions()
    assert v == {
        proj1: '0.0.1',
        proj2: '0.2.1',
    }
    untagged_repo.chdir()

    v = projspec.get_subproject_versions()
    assert v == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.get_subproject_versions()

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.get_subproject_versions('foo')

    with pytest.raises(sbp.CalledProcessError):
        v = projspec.get_subproject_versions('foo' 'bar')


def test_get_BAD_projects_versions(projspec, ok_repo):
    ok_repo.chdir()
    v = projspec.get_subproject_versions('foo')
    assert dict(v) == {}


##############
## DESCRIBE ##
##############

def test_git_describe_p1(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    projspec.pname = proj1
    v = projspec.git_describe()
    assert v.startswith(proj1_desc)

    untagged_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        projspec.pname = 'foo'
        v = projspec.git_describe()

    no_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        projspec.pname = proj1
        projspec.git_describe()


def test_git_describe_p2(projspec, ok_repo):
    ok_repo.chdir()

    projspec.pname = proj2
    v = projspec.git_describe()
    assert v == proj2_desc


def test_git_describe_BAD(projspec, ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        projspec.pname = 'foo'
        projspec.git_describe()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_git_describe_BAD_no_git_cmd(projspec, ok_repo, monkeypatch):
    ok_repo.chdir()
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        projspec.pname = 'foo'
        projspec.git_describe()


def test_last_commit_tstamp_p1(projspec, ok_repo, untagged_repo, no_repo, today):
    ok_repo.chdir()

    d = projspec.last_commit_tstamp()
    assert d.startswith(today)

    untagged_repo.chdir()

    d = projspec.last_commit_tstamp()
    assert d.startswith(today)

    no_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        projspec.last_commit_tstamp()


def test_last_commit_tstamp_BAD_no_commits(projspec, empty_repo):
    empty_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        projspec.last_commit_tstamp()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_last_commit_tstamp_BAD_no_git_cmd(projspec, ok_repo, monkeypatch):
    ok_repo.chdir()
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        projspec.last_commit_tstamp()
