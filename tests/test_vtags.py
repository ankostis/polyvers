#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import vtags
import pytest

import subprocess as subp


proj1 = 'proj1'
proj2 = 'proj-2'


def test_get_all_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags()
    assert dict(v) == {
        proj1: ['0.0.0', '0.0.1'],
        proj2: ['0.2.0', '0.2.1'],
    }, v

    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags()
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = vtags.find_all_subproject_vtags()


def test_get_p1_vtags(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags(proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}, v

    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags(proj1)
    assert dict(v) == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = vtags.find_all_subproject_vtags(proj1)


def test_get_p2_vtags(ok_repo):
    ok_repo.chdir()
    v = vtags.find_all_subproject_vtags(proj2)
    assert dict(v) == {proj2: ['0.2.0', '0.2.1']}, v


def test_get_BAD_project_vtag(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.find_all_subproject_vtags('foo')
    assert dict(v) == {}, v

    v = vtags.find_all_subproject_vtags('foo', proj1)
    assert dict(v) == {proj1: ['0.0.0', '0.0.1']}, v

    untagged_repo.chdir()

    v = vtags.find_all_subproject_vtags('foo', 'bar')
    assert dict(v) == {}, v

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = vtags.find_all_subproject_vtags('foo')


def test_get_subproject_versions(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = vtags.get_subproject_versions()
    assert v == {
        proj1: '0.0.1',
        proj2: '0.2.1',
    }, v

    untagged_repo.chdir()

    v = vtags.get_subproject_versions()
    assert v == {}

    no_repo.chdir()

    with pytest.raises(subp.CalledProcessError):
        v = vtags.get_subproject_versions()

    with pytest.raises(subp.CalledProcessError):
        v = vtags.get_subproject_versions('foo')

    with pytest.raises(subp.CalledProcessError):
        v = vtags.get_subproject_versions('foo' 'bar')


def test_get_BAD_projects_versions(ok_repo):
    ok_repo.chdir()
    v = vtags.get_subproject_versions('foo')
    assert dict(v) == {}, v
