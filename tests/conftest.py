#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Common pytest fixtures."""

import pytest

from py.path import local as P  # @UnresolvedImport
import subprocess as sbp


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


def assert_in_text(text, require=None, forbid=None):
    """
    Checks strings are (not) contained in text.

    :param text:
        a string or a list of strings
    :param require:
        A string (or list of strings) that must require at some text's line.
    :param forbid:
        A string (or list of strings) that must NOT require at any text's line.
    :raise pytest.Failed:
        with all errors detected
    """
    __tracebackhide__ = True
    if isinstance(text, str):
        text = text.split('\n')

    if isinstance(require, str):
        require = [require]
    if isinstance(forbid, str):
        forbid = [forbid]

    matches = set()
    illegals = {}
    for i, l in enumerate(text):
        for mterm in require:
            if mterm not in matches and mterm in l:
                matches.add(mterm)

        for iterm in forbid:
            if iterm and iterm in l:
                illegals[iterm] = i

    missed = set(require) - matches
    err1 = missed and "MISSES: %s" % ', '.join(missed) or ''
    err2 = illegals and "ILLEGALS: \n  %s" % '\n  '.join(
        "%r in line(%i): %s" % (k, v + 1, text[v]) for k, v in illegals.items()) or ''

    if err1 or err2:
        pytest.fail("Text errors: %s %s\n  text: %s" %
                    (err1, err2, '\n    '.join(text)))


@pytest.fixture()
def today():
    """A :rfc:`2822` formated timestamp: ``Thu, 01 Mar 2018 09:46:47 +0000`` """

    from polyvers.polyverslib import rfc2822_tstamp

    ## TCs may fail if run when day changes :-)
    #  Unfortunately cannot compare full-date (``[:12]   #till hour``)
    #  format Git does return single-digit month-day,
    #  not '01' as the mail-standard does::
    #     Thu, 1 Mar 2018 09:46:47 +0000
    return rfc2822_tstamp()[:5]  # till Day-of-week


@pytest.fixture()
def mutable_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
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
            sbp.check_call(c.split())

    return repo_dir


@pytest.fixture(scope="session")
def ok_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    cmds = """
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
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            sbp.check_call(c.split())

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
            sbp.check_call(c.split())

    return repo_dir


@pytest.fixture(scope="session")
def empty_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('untagged')
    repo_dir.chdir()
    cmds = """
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    """
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            sbp.check_call(c.split())

    return repo_dir


@pytest.fixture(scope="session")
def no_repo(tmpdir_factory):
    return tmpdir_factory.mktemp('norepo')
