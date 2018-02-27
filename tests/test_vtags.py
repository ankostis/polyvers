#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import vtags

import pytest

import subprocess as sbp


proj1 = 'proj1'
proj2 = 'proj-2'


def test_get_all_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags()
    assert dict(v) == {
        proj1: ['0.0.0', '0.0.1'],
        proj2: ['0.2.0', '0.2.1'],
    }
    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags()
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.find_all_subproject_vtags()


def test_get_p1_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags(proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}
    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags(proj1)
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.find_all_subproject_vtags(proj1)


def test_get_p2_vtags(ok_repo):
    ok_repo.chdir()
    v = vtags.find_all_subproject_vtags(proj2)
    assert dict(v) == {proj2: ['0.2.0', '0.2.1']}


def test_get_BAD_project_vtag(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags('foo')
    assert dict(v) == {}
    v = vtags.find_all_subproject_vtags('foo', proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}

    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags('foo', 'bar')
    assert dict(v) == {}
    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.find_all_subproject_vtags('foo')


def test_get_subproject_versions(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.get_subproject_versions()
    assert v == {
        proj1: '0.0.1',
        proj2: '0.2.1',
    }
    untagged_repo.chdir()

    v = vtags.get_subproject_versions()
    assert v == {}

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.get_subproject_versions()

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.get_subproject_versions('foo')

    with pytest.raises(sbp.CalledProcessError):
        v = vtags.get_subproject_versions('foo' 'bar')


def test_get_BAD_projects_versions(ok_repo):
    ok_repo.chdir()
    v = vtags.get_subproject_versions('foo')
    assert dict(v) == {}


##############
## DESCRIBE ##
##############

def rfc2822_today():
    ## TCs may fail if run when day changes :-)
    return vtags.rfc2822_now()[:12]  # till hour


def test_describe_project_p1(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.describe_project(proj1,)
    assert v.startswith('proj1-v0.0.1')
    v = vtags.describe_project(proj1, default='<unused>')
    assert v.startswith('proj1-v0.0.1')
    v, d = vtags.describe_project(proj1, tag_date=True)
    assert v.startswith('proj1-v0.0.1') and d.startswith(rfc2822_today())
    v, d = vtags.describe_project(proj1, default='<unused>', tag_date=True)
    assert v.startswith('proj1-v0.0.1') and d.startswith(rfc2822_today())

    untagged_repo.chdir()

    with pytest.raises(vtags.NoVersionError):
        v = vtags.describe_project('foo')
    v = vtags.describe_project('foo', default='<unused>')
    assert v == '<unused>'
    with pytest.raises(vtags.NoVersionError):
        vtags.describe_project('foo', tag_date=True)
    v, d = vtags.describe_project('foo', default=(1, 2, 3), tag_date=True)
    assert v == (1, 2, 3) and d.startswith(rfc2822_today())

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        vtags.describe_project(proj1)
    v = vtags.describe_project(proj1, default='<unused>')
    assert v == '<unused>'

    v, d = vtags.describe_project(proj1, default='ab', tag_date=True)
    assert v == 'ab' and d.startswith(rfc2822_today())


def test_describe_project_p2(ok_repo):
    ok_repo.chdir()

    v = vtags.describe_project(proj2)
    assert v.startswith('proj-2-v0.2.1')
    v, d = vtags.describe_project(proj2, tag_date=True)
    assert d.startswith(rfc2822_today())


def test_describe_project_BAD(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    with pytest.raises(vtags.NoVersionError):
        vtags.describe_project('foo')
    v = vtags.describe_project('foo', default='<unused>')
    assert v == '<unused>'
    with pytest.raises(vtags.NoVersionError):
        vtags.describe_project('foo', tag_date=True)

    v, d = vtags.describe_project('foo', default='a', tag_date=True)
    assert v == 'a' and d.startswith(rfc2822_today())
