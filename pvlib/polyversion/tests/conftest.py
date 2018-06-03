#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""Common pytest fixtures."""

import pytest

import subprocess as sbp


def _exec_cmds(cmds):
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            sbp.check_call(c.split())


@pytest.fixture()
def today():
    """A :rfc:`2822` formated timestamp: ``Thu, 01 Mar 2018 09:46:47 +0000`` """

    from polyversion import rfc2822_tstamp

    ## TCs may fail if run when day changes :-)
    #  Unfortunately cannot compare full-date (``[:12]   #till hour``)
    #  format Git does return single-digit month-day,
    #  not '01' as the mail-standard does::
    #     Thu, 1 Mar 2018 09:46:47 +0000
    return rfc2822_tstamp()[:5]  # till Day-of-week


######################
## IMMMUTABLE REPOS ##
######################

@pytest.fixture(scope='session')
def ok_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    _exec_cmds("""
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    git commit --allow-empty  --no-edit -m some_msg
    git tag proj1-v0.0.0 -m annotated
    git commit --allow-empty  --no-edit -m some_msg
    git tag  proj1-v0.0.1 -m annotated
    git tag  proj-2-V0.2.0
    git commit --allow-empty  --no-edit -m some_msg
    git commit --allow-empty  --no-edit -m some_msg
    git tag proj-2-V0.2.1
    """)

    return repo_dir


@pytest.fixture(scope='session')
def vtags_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    _exec_cmds("""
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    git commit --allow-empty  --no-edit -m some_msg
    git tag v0.0.0 -m annotated
    """)

    (repo_dir / 'pypak.py').write('')

    _exec_cmds("""
    git add .
    git commit --no-edit -m some_msg
    git commit --allow-empty  --no-edit -m some_msg
    git tag  v0.0.1 -m annotated
    git commit --allow-empty  --no-edit -m some_msg
    """)

    return repo_dir


@pytest.fixture(scope='session')
def rtagged_vtags_repo(tmpdir_factory, vtags_repo):
    newrepo = tmpdir_factory.mktemp('rtag_monorepo')
    newrepo_rel = vtags_repo.bestrelpath(newrepo)
    vtags_repo.chdir()
    _exec_cmds("""
    git clone . %(newrepo)s
    git -C %(newrepo)s commit --allow-empty  --no-edit -m r-c
    git -C %(newrepo)s tag  r0.0.1 -m annotated
    """ % {'newrepo': newrepo_rel})

    return newrepo


@pytest.fixture(scope='session')
def untagged_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('untagged')
    repo_dir.chdir()
    _exec_cmds("""
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    git commit --allow-empty  --no-edit -m some_msg
    """)

    return repo_dir


@pytest.fixture(scope='session')
def empty_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('untagged')
    repo_dir.chdir()
    _exec_cmds("""
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    """)

    return repo_dir


@pytest.fixture(scope='session')
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')
