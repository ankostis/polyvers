#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import gitag
from polyvers._vendor import traitlets as trt
from polyvers._vendor.traitlets import config as trc
from polyvers.pvproject import Project
from polyvers.utils.oscmd import cmd
import re
import sys

import pytest

import polyversion as pvlib


pname1 = 'proj1'
p1_vtag = 'proj1-v0.0.1-2-g'
pname2 = 'proj-2'
p2_vtag = 'proj-2-V0.2.1'

search_all = gitag.make_match_all_pp_vtags_project()


@pytest.fixture
def monorepocfg():
    template_project = gitag.make_pp_project()
    cfg = trc.Config({
        'Project': {
            'tag_format': template_project.tag_format,
            'gitdesc_repat': template_project.gitdesc_repat,
        }})

    return cfg


@pytest.fixture
def project1(monorepocfg):
    return Project(config=monorepocfg, pname=pname1)


@pytest.fixture
def project2():
    return Project(
        pname=pname2,
        tag_format='{pname}-V{version}',
        gitdesc_repat=r"""(?xmi)
            ^(?P<pname>{pname})
            -
            V(?P<version>\d[^-]*)
            (?:-(?P<descid>\d+-g[a-f\d]+))?$
        """)


@pytest.fixture
def foo(monorepocfg):
    return Project(config=monorepocfg, pname='foo')


def test_Project_regex_check():
    with pytest.raises(trt.TraitError,
                       match=r'missing \), unterminated subpattern'):
        Project(gitdesc_repat="(")


def test_Project_version_from_vtag(foo):
    v = foo.version_from_vtag('foo-v1.0.0-2-gbaba0')
    assert v == '1.0.0'


def test_new_Project_raises_vtags_unpopulated(project1):
    with pytest.raises(AssertionError):
        project1.vtags_history


def test_Project_defaults(monorepocfg):
    proj = Project()

    assert proj.tag_format == ''
    assert proj.gitdesc_repat == ''
    assert proj.tag_fnmatch() == ''

    proj = Project(config=monorepocfg)

    assert proj.tag_format == pvlib.pp_tag_format
    assert proj.gitdesc_repat == pvlib.pp_gitdesc_repat
    assert proj.tag_fnmatch() == '-v*'


def test_pp_Project_interpolations():
    proj = gitag.make_pp_project(pname='foo', version='1.2.3')

    assert 'foo' in proj.tag_fnmatch()
    assert proj.tag_fnmatch().endswith('v*')
    assert 'foo' in proj.gitdesc_regex().pattern
    assert not re.search(r'1.2.3', proj.gitdesc_regex().pattern)

    proj = gitag.make_pp_project(pname='f*o')

    assert 'f[*]o' in proj.tag_fnmatch()
    assert r'f\*o' in proj.gitdesc_regex().pattern


def test_mp_Project_interpolations():
    with pytest.raises(trt.TraitError, match="Invalid version: '1.2.3"):
        gitag.make_mp_project(version='1.2.3(-: ')

    proj = gitag.make_mp_project(version='1.2.3')

    assert 'foo' not in proj.tag_fnmatch()
    assert proj.tag_fnmatch().endswith('v*')
    assert 'foo' not in proj.gitdesc_regex().pattern
    assert not re.search(r'1.2.3', proj.gitdesc_regex().pattern)


def test_populate_vtags_history_per_project(ok_repo, project1, project2, foo):
    ok_repo.chdir()

    with pytest.raises(AssertionError):
        project1.vtags_history

    gitag.populate_vtags_history(project1)
    assert project1.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']

    gitag.populate_vtags_history(project2)
    assert project2.vtags_history == []
    gitag.populate_vtags_history(project2, include_lightweight=True)
    assert project2.vtags_history == ['proj-2-V0.2.1', 'proj-2-V0.2.0']

    ## Ensure no side-effects.
    assert project1.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']

    gitag.populate_vtags_history(foo)
    assert foo.vtags_history == []

    ## Ensure no side-effects.
    assert project1.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']
    assert project2.vtags_history == ['proj-2-V0.2.1', 'proj-2-V0.2.0']


def test_populate_vtags_history_multi_projects(ok_repo, project1, project2, foo):
    ok_repo.chdir()

    gitag.populate_vtags_history(project1, project2, foo,
                                 include_lightweight=True)
    assert project1.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']
    assert project2.vtags_history == ['proj-2-V0.2.1', 'proj-2-V0.2.0']
    assert foo.vtags_history == []


def test_fetch_vtags_history_no_tags(untagged_repo, empty_repo, foo):
    untagged_repo.chdir()

    gitag.populate_vtags_history(foo)
    assert foo.vtags_history == []

    empty_repo.chdir()

    gitag.populate_vtags_history(foo)
    assert foo.vtags_history == []


def test_fetch_vtags_history_BAD(no_repo, foo):
    no_repo.chdir()

    with pytest.raises(gitag.NoGitRepoError):
        gitag.populate_vtags_history(foo)


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_fetch_vtags_history_git_not_in_path(foo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        gitag.populate_vtags_history(foo)


def test_project_matching_all_pp_vtags(ok_repo, project1):
    ok_repo.chdir()

    all_vtags = gitag.make_match_all_pp_vtags_project()
    gitag.populate_vtags_history(all_vtags)
    assert all_vtags.pname == '<PVTAG>'
    assert all_vtags.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']

    all_vtags = gitag.make_match_all_mp_vtags_project()
    assert all_vtags.pname == '<VTAG>'
    gitag.populate_vtags_history(all_vtags)
    assert all_vtags.vtags_history == []


def test_simple_project(mutable_pp_repo, project2, caplog):
    BAD_TAG = 'irrelevant_tag'
    mutable_pp_repo.chdir()
    caplog.set_level(0)

    cmd.git.tag(BAD_TAG, m='ggg')
    cmd.git.tag('v123')
    cmd.git.tag('v12.0', m='hh')
    all_mp_tags = gitag.make_match_all_mp_vtags_project()
    caplog.clear()
    gitag.populate_vtags_history(all_mp_tags)
    assert all_mp_tags.vtags_history == ['v12.0']
    assert BAD_TAG not in caplog.text

    gitag.populate_vtags_history(all_mp_tags, include_lightweight=True)
    assert all_mp_tags.vtags_history == ['v12.0', 'v123']

    ## Check both vtag & vtag formats.

    all_pp_tags = gitag.make_match_all_pp_vtags_project()
    gitag.populate_vtags_history(project2, all_pp_tags, all_mp_tags,
                                 include_lightweight=True)
    assert all_mp_tags.vtags_history == ['v12.0', 'v123']
    assert all_pp_tags.vtags_history == ['proj1-v0.0.1', 'proj1-v0.0.0']
    assert project2.vtags_history == ['proj-2-V0.2.1', 'proj-2-V0.2.0']


##############
## DESCRIBE ##
##############

def test_git_describe_ok(ok_repo, project1, project2):
    ok_repo.chdir()

    v = project1.git_describe()
    assert v.startswith(p1_vtag)

    with pytest.raises(gitag.GitVoidError):
        ## Not annotated does not show up.
        project2.git_describe()

    v = project2.git_describe(include_lightweight=True)
    assert v == p2_vtag
    v = project2.git_describe(all=True)
    assert v == p2_vtag


def test_git_describe_bad(ok_repo, no_repo, foo):
    ok_repo.chdir()

    with pytest.raises(gitag.GitVoidError):
        foo.git_describe()

    no_repo.chdir()

    with pytest.raises(gitag.NoGitRepoError):
        foo.git_describe()


def test_git_describe_mismatch_version(ok_repo, project1):
    ok_repo.chdir()

    project1.gitdesc_repat = """
        ^(?P<pname>BADNAME)
        -
        v(?P<version>\d[^-]*)
        (?:-(?P<descid>\d+-g[a-f\d]+))?$
    """
    with pytest.raises(trt.TraitError):
        project1.git_describe()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_git_describe_git_not_in_path(foo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        foo.git_describe()


#############
## UPDATED ##
#############

def test_last_commit_tstamp_ok(ok_repo, today, project1, project2, foo):
    ok_repo.chdir()

    d = project1.last_commit_tstamp()
    assert d.startswith(today)

    dates = [p.last_commit_tstamp() for p in [foo, project1, project2]]
    assert all(d.startswith(dates[0]) for d in dates)


def test_last_commit_tstamp_untagged(untagged_repo, today, foo):
    untagged_repo.chdir()

    d = foo.last_commit_tstamp()
    assert d.startswith(today)


def test_last_commit_tstamp_BAD(empty_repo, no_repo, foo):
    empty_repo.chdir()

    with pytest.raises(gitag.GitVoidError):
        foo.last_commit_tstamp()

    no_repo.chdir()

    with pytest.raises(gitag.NoGitRepoError):
        foo.last_commit_tstamp()


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_last_commit_tstamp_BAD_no_git_cmd(foo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        foo.last_commit_tstamp()


def test_git_restore_point(mutable_repo):
    mutable_repo.chdir()

    ## no rollback without errors
    #
    with gitag.git_restore_point():
        cmd.git.commit(m='some msg', allow_empty=True)
        exp_point = cmd.git.rev_parse.HEAD()
    assert cmd.git.rev_parse.HEAD() == exp_point

    ## rollback
    #
    with pytest.raises(ValueError, match='Opa!'):
        with gitag.git_restore_point():
            cmd.git.commit(m='some msg', allow_empty=True)
            raise ValueError('Opa!')
    assert cmd.git.rev_parse.HEAD() == exp_point

    ## rollback forced
    #
    with gitag.git_restore_point(True):
        cmd.git.commit(m='some msg', allow_empty=True)
    assert cmd.git.rev_parse.HEAD() == exp_point
