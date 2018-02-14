#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Common pytest fixtures."""

from polyvers import polyverslib as pvlib

import pytest


@pytest.fixture(scope="module")
def ok_repo(tmpdir_factory):
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
def untagged_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('untagged')
    repo_dir.chdir()
    cmds = """
    git init
    git commit --allow-empty  --no-edit -m some_msg
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            pvlib.exec_cmd(c)

    return repo_dir


@pytest.fixture(scope="module")
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')
