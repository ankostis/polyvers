#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Common pytest fixtures."""

from polyvers import polyverslib as pvlib
from py.path import local as P  # @UnresolvedImport
import pytest


def touchpaths(tdir, paths_txt):
    """
    :param tdir:
        The dir to create the file-hierarchy under.
    :param str paths_txt:
        A multiline text specifying one file/dir per line to create.
        Paths ending with '/' are treated as dirs.
        Empty lines or those with '#' as the 1st non-space char are ignored.
    """
    tdir = P(tdir)
    for f in paths_txt.split('\n'):
        f = f.strip()
        if f and not f.startswith('#'):
            (tdir / f).ensure(dir=f.endswith('/'))


@pytest.fixture(scope="session")
def ok_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    cmds = """
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
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
            pvlib.exec_cmd(c.split())

    return repo_dir


@pytest.fixture(scope="session")
def untagged_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('untagged')
    repo_dir.chdir()
    cmds = """
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    git commit --allow-empty  --no-edit -m some_msg
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            pvlib.exec_cmd(c.split())

    return repo_dir


@pytest.fixture(scope="session")
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')
