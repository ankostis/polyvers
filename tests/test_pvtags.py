#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import pvtags
from polyvers._vendor.traitlets import TraitError
from polyvers.pvtags import Project
import sys

import pytest


pname1 = 'proj1'
p1_pvtag = 'proj1-v0.0.1-2-g'
pname2 = 'proj-2'
p2_pvtag = 'proj-2-V0.2.1'

search_all = pvtags.make_project_matching_all_pvtags()
project1 = Project(pname=pname1)
project2 = Project(pname=pname2,
                   pvtag_frmt='{pname}-V{version}',
                   pvtag_regex=r"""(?xi)
                        ^(?P<project>{pname})
                        -
                        V(?P<version>\d[^-]*)
                        (?:-(?P<descid>\d+-g[a-f\d]+))?$
                    """)
foo = Project(pname='foo')


def test_Project_regex_check():
    with pytest.raises(TraitError,
                       match=r'missing \), unterminated subpattern'):
        Project(pvtag_regex="(")


def test_Project_version_from_pvtag(caplog):
    v = foo.version_from_pvtag('foo-v1.0.0-2-gbaba0')
    assert v == '1.0.0'
    assert "`git-describe` suffix" in caplog.text


def test_new_Project_raises_pvtags_unpopulated():
    with pytest.raises(AssertionError):
        project1.pvtags_history


def test_populate_pvtags_history_per_project(ok_repo):
    ok_repo.chdir()

    with pytest.raises(AssertionError):
        project1.pvtags_history

    pvtags.populate_pvtags_history(project1)
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project1.pvtag == 'proj1-v0.0.1'

    pvtags.populate_pvtags_history(project2)
    assert project2.pvtags_history == []
    pvtags.populate_pvtags_history(project2, include_lightweight=True)
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']
    assert project2.pvtag == 'proj-2-V0.2.1'

    ## Ensure no side-effects.
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []
    assert foo.pvtag is None

    ## Ensure no side-effects.
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']


def test_populate_pvtags_history_multi_projects(ok_repo):
    ok_repo.chdir()

    pvtags.populate_pvtags_history(project1, project2, foo,
                                   include_lightweight=True)
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']
    assert foo.pvtags_history == []


def test_fetch_pvtags_history_no_tags(untagged_repo, empty_repo):
    untagged_repo.chdir()

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []

    empty_repo.chdir()

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []


def test_fetch_pvtags_history_BAD(no_repo):
    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
        pvtags.populate_pvtags_history(foo)


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_fetch_pvtags_history_git_not_in_path(monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvtags.populate_pvtags_history(foo)


# def test_get_subproject_versions(ok_repo, untagged_repo, no_repo):
#     ok_repo.chdir()
#
#     v = pvtags.fetch_pvtags_history()
#     assert v == {
#         pname1: '0.0.1',
#         pname2: '0.2.1',
#     }
#     untagged_repo.chdir()
#
#     v = pvtags.fetch_pvtags_history()
#     assert v == {}
#
#     no_repo.chdir()
#
#     with pytest.raises(sbp.CalledProcessError):
#         v = pvtags.fetch_pvtags_history()
#
#     with pytest.raises(sbp.CalledProcessError):
#         v = pvtags.fetch_pvtags_history(foo)
#
#     with pytest.raises(sbp.CalledProcessError):
#         v = pvtags.fetch_pvtags_history(foo, Project(pname='bar'))
#
#
# def test_get_BAD_projects_versions(ok_repo):
#     ok_repo.chdir()
#     v = pvtags.fetch_pvtags_history(foo)
#     assert dict(v) == {}


##############
## DESCRIBE ##
##############

def test_git_describe_ok(ok_repo):
    ok_repo.chdir()

    v = project1.git_describe()
    assert v.startswith(p1_pvtag)

    with pytest.raises(pvtags.GitVoidError):
        ## Not annotated does not show up.
        project2.git_describe()

    v = project2.git_describe(include_lightweight=True)
    assert v == p2_pvtag
    v = project2.git_describe(all=True)
    assert v == 'tags/' + p2_pvtag


def test_git_describe_bad(ok_repo, no_repo):
    ok_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        foo.git_describe()

    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
        foo.git_describe()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_git_describe_git_not_in_path(monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        foo.git_describe()


#############
## UPDATED ##
#############

def test_last_commit_tstamp_ok(ok_repo, today):
    ok_repo.chdir()

    d = project1.last_commit_tstamp()
    assert d.startswith(today)

    dates = [p.last_commit_tstamp() for p in [foo, project1, project2]]
    assert all(d.startswith(dates[0]) for d in dates)


def test_last_commit_tstamp_untagged(untagged_repo, today):
    untagged_repo.chdir()

    d = foo.last_commit_tstamp()
    assert d.startswith(today)


def test_last_commit_tstamp_BAD(empty_repo, no_repo):
    empty_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        foo.last_commit_tstamp()

    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
        foo.last_commit_tstamp()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_last_commit_tstamp_BAD_no_git_cmd(monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        foo.last_commit_tstamp()
