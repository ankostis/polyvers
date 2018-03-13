#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import pvtags
from polyvers._vendor import traitlets as trt
from polyvers._vendor.traitlets import config as trc
from polyvers.oscmd import cmd
from polyvers.pvtags import Project
import re
import sys

import pytest


pname1 = 'proj1'
p1_pvtag = 'proj1-v0.0.1-2-g'
pname2 = 'proj-2'
p2_pvtag = 'proj-2-V0.2.1'

search_all = pvtags.make_match_all_pvtags_project()


@pytest.fixture
def proot():
    class C(trc.Application):
        template_project = pvtags.make_pvtag_project()

    return C()


@pytest.fixture
def project1(proot):
    return Project(parent=proot, pname=pname1)


@pytest.fixture
def project2():
    return Project(
        pname=pname2,
        pvtag_frmt='{pname}-V{version}',
        pvtag_regex=r"""(?xi)
            ^(?P<pname>{pname})
            -
            V(?P<version>\d[^-]*)
            (?:-(?P<descid>\d+-g[a-f\d]+))?$
        """)


@pytest.fixture
def foo(proot):
    return Project(parent=proot, pname='foo')


def test_Project_regex_check():
    with pytest.raises(trt.TraitError,
                       match=r'missing \), unterminated subpattern'):
        Project(pvtag_regex="(")


def test_Project_version_from_pvtag(foo, caplog):
    v = foo.version_from_pvtag('foo-v1.0.0-2-gbaba0')
    assert v == '1.0.0'
    assert "`git-describe` suffix" in caplog.text


def test_new_Project_raises_pvtags_unpopulated(project1):
    with pytest.raises(AssertionError):
        project1.pvtags_history


def test_Project_defaults(proot):
    proj = Project()

    assert proj.pvtag_frmt == ''
    assert proj.pvtag_regex == ''
    assert proj.pvtag_fnmatch_frmt == ''

    proj = Project(parent=proot)
    pproj = proot.template_project

    assert proj.pvtag_frmt == pproj.pvtag_frmt
    assert proj.pvtag_regex == pproj.pvtag_regex
    assert proj.pvtag_fnmatch_frmt == pproj.pvtag_fnmatch_frmt


def test_pvtag_Project_interpolations():
    proj = pvtags.make_pvtag_project(pname='foo', version='1.2.3')

    assert 'foo' in proj.pvtag_fnmatch_frmt
    assert proj.pvtag_fnmatch_frmt.endswith('v*')
    assert 'foo' in proj._pvtag_regex_resolved.pattern
    assert not re.search(r'1.2.3', proj._pvtag_regex_resolved.pattern)

    proj = pvtags.make_pvtag_project(pname='f*o')

    assert 'f[*]o' in proj.pvtag_fnmatch_frmt
    assert r'f\*o' in proj._pvtag_regex_resolved.pattern


def test_vtag_Project_interpolations():
    proj = pvtags.make_vtag_project(version='1.2.3(-:')

    assert 'foo' not in proj.pvtag_fnmatch_frmt
    assert proj.pvtag_fnmatch_frmt.endswith('v*')
    assert 'foo' not in proj._pvtag_regex_resolved.pattern
    assert not re.search(r'1.2.3', proj._pvtag_regex_resolved.pattern)


def test_populate_pvtags_history_per_project(ok_repo, project1, project2, foo):
    ok_repo.chdir()

    with pytest.raises(AssertionError):
        project1.pvtags_history

    pvtags.populate_pvtags_history(project1)
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']

    pvtags.populate_pvtags_history(project2)
    assert project2.pvtags_history == []
    pvtags.populate_pvtags_history(project2, include_lightweight=True)
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']

    ## Ensure no side-effects.
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []

    ## Ensure no side-effects.
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']


def test_populate_pvtags_history_multi_projects(ok_repo, project1, project2, foo):
    ok_repo.chdir()

    pvtags.populate_pvtags_history(project1, project2, foo,
                                   include_lightweight=True)
    assert project1.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']
    assert foo.pvtags_history == []


def test_fetch_pvtags_history_no_tags(untagged_repo, empty_repo, foo):
    untagged_repo.chdir()

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []

    empty_repo.chdir()

    pvtags.populate_pvtags_history(foo)
    assert foo.pvtags_history == []


def test_fetch_pvtags_history_BAD(no_repo, foo):
    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
        pvtags.populate_pvtags_history(foo)


@pytest.mark.skipif(sys.version_info < (3, ),
                    reason="FileNotFoundError not in PY27, OSError only.")
def test_fetch_pvtags_history_git_not_in_path(foo, monkeypatch):
    monkeypatch.setenv('PATH', '')

    with pytest.raises(FileNotFoundError):
        pvtags.populate_pvtags_history(foo)


def test_project_matching_all_pvtags(ok_repo, project1):
    ok_repo.chdir()

    all_pvtags = pvtags.make_match_all_pvtags_project()
    pvtags.populate_pvtags_history(all_pvtags)
    assert all_pvtags.pname == '<PVTAG>'
    assert all_pvtags.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']

    all_vtags = pvtags.make_match_all_vtags_project()
    assert all_vtags.pname == '<VTAG>'
    pvtags.populate_pvtags_history(all_vtags)
    assert all_vtags.pvtags_history == []


def test_simple_project(monorepo, project2):
    monorepo.chdir()

    cmd.git.tag('v123')
    cmd.git.tag('v12.0', m='hh')
    all_vtags = pvtags.make_match_all_vtags_project()
    pvtags.populate_pvtags_history(all_vtags)
    assert all_vtags.pvtags_history == ['v12.0']

    pvtags.populate_pvtags_history(all_vtags, include_lightweight=True)
    assert all_vtags.pvtags_history == ['v12.0', 'v123']

    ## Check both pvtag & vtag formats.

    all_pvtags = pvtags.make_match_all_pvtags_project()
    pvtags.populate_pvtags_history(project2, all_pvtags, all_vtags,
                                   include_lightweight=True)
    assert all_vtags.pvtags_history == ['v12.0', 'v123']
    assert all_pvtags.pvtags_history == ['proj1-v0.0.0', 'proj1-v0.0.1']
    assert project2.pvtags_history == ['proj-2-V0.2.0', 'proj-2-V0.2.1']


##############
## DESCRIBE ##
##############

def test_git_describe_ok(ok_repo, project1, project2):
    ok_repo.chdir()

    v = project1.git_describe()
    assert v.startswith(p1_pvtag)

    with pytest.raises(pvtags.GitVoidError):
        ## Not annotated does not show up.
        project2.git_describe()

    v = project2.git_describe(include_lightweight=True)
    assert v == p2_pvtag
    v = project2.git_describe(all=True)
    assert v == p2_pvtag


def test_git_describe_bad(ok_repo, no_repo, foo):
    ok_repo.chdir()

    with pytest.raises(pvtags.GitVoidError):
        foo.git_describe()

    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
        foo.git_describe()


def test_git_describe_mismatch_version(ok_repo, project1):
    ok_repo.chdir()

    project1.pvtag_regex = """
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

    with pytest.raises(pvtags.GitVoidError):
        foo.last_commit_tstamp()

    no_repo.chdir()

    with pytest.raises(pvtags.NoGitRepoError):
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
    with pvtags.git_restore_point():
        cmd.git.commit(m='some msg', allow_empty=True)
        exp_point = cmd.git.rev_parse.HEAD()
    assert cmd.git.rev_parse.HEAD() == exp_point

    ## rollback
    #
    with pytest.raises(ValueError, match='Opa!'):
        with pvtags.git_restore_point():
            cmd.git.commit(m='some msg', allow_empty=True)
            raise ValueError('Opa!')
    assert cmd.git.rev_parse.HEAD() == exp_point

    ## rollback forced
    #
    with pvtags.git_restore_point(True):
        cmd.git.commit(m='some msg', allow_empty=True)
    assert cmd.git.rev_parse.HEAD() == exp_point
