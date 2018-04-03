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
import textwrap as tw


def dict_eq(d1, d2):
    """
    Compare dictionaries regardless of their classes.

    .. Note::
        Adapted from https://stackoverflow.com/a/4527978/548792
        with ``set()-->sorted()`` so it works with non-hashable (mutable) values.
        But will fail with non-orderable key/values.
    """
    return d1 is d2 is None or sorted(d1.items()) == sorted(d2.items())


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


def _re_match(subtext, text):
    import re

    try:
        subtext = re.compile(subtext)
    except Exception as ex:
        raise ValueError("Bad regex '%s' due to: %s" %
                         (subtext, ex)) from None
    else:
        return subtext.search(text)


def assert_in_text(text, require=None, forbid=None, is_regex=False):
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

    if is_regex:
        match_func = _re_match
    else:
        match_func = lambda subtext, text: subtext in text

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
            if mterm not in matches and match_func(mterm, l):
                matches.add(mterm)

        for iterm in forbid:
            if iterm and match_func(iterm, l):
                illegals[iterm] = i

    missed = set(require) - matches
    err1 = missed and "\n  - MISSES: \n    - %s" % '\n    - '.join(missed) or ''
    err2 = illegals and "\n  - ILLEGALS: \n    - %s" % '\n    - '.join(
        "%r in line(%i): %s" % (k, v + 1, text[v]) for k, v in illegals.items()) or ''

    if err1 or err2:
        pytest.fail("Text errors: %s %s\n  text: %s" %
                    (err1, err2, '\n    '.join(text)))


def clearlog(caplog):
    "Workaround not clearing text: https://github.com/pytest-dev/pytest/issues/3297"
    import io

    caplog.clear()
    caplog.handler.stream = io.StringIO()


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


#############
## FILESET ##
#############

f1 = """
stays the same
a = b
stays the same
"""
f11 = """
stays the same
AaA = BbB
stays the same
"""


@pytest.fixture
def f1_graft():
    return {'regex': r'(?m)^(\w+) *= *(\w+)',
            'subst': r'A\1A = B\2B'}


f2 = """
leave
CHANGE
THESE
leave
"""
f22 = """
leave
changed them
leave
"""


@pytest.fixture
def f2_graft():
    return {'regex': r'(?m)^CHANGE\s+THESE',
            'subst': 'changed them'}


f3 = """
Lorem ipsum dolor sit amet,
consectetur adipiscing elit,
sed do eiusm
"""


@pytest.fixture(scope='module')
def orig_files():
    return {
        'a/f1': f1,
        'a/f2': f2,
        'a/f3': f3,

        'b/f1': f1,
        'b/f2': f2,
        'b/f3': f3,
    }


@pytest.fixture(scope='module')
def ok_files():
    return {
        'a/f1': f11,
        'a/f2': f22,
        'a/f3': f3,

        'b/f1': f11,
        'b/f2': f22,
        'b/f3': f3,
    }


def _make_fileset(tdir, files):
    for fpath, text in files.items():
        (tdir / fpath).write_text(tw.dedent(text),
                                  encoding='utf-8', ensure=True)

    return tdir


@pytest.fixture(scope='module')
def fileset(tmpdir_factory, orig_files):
    tmpdir = tmpdir_factory.mktemp('engraveset')
    return _make_fileset(tmpdir, orig_files)


######################
## IMMMUTABLE REPOS ##
######################

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
def vtags_repo(tmpdir_factory):
    repo_dir = tmpdir_factory.mktemp('repo')
    repo_dir.chdir()
    cmds = """
    git init
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    git commit --allow-empty  --no-edit -m some_msg
    git tag v0.0.0 -m annotated
    git commit --allow-empty  --no-edit -m some_msg
    git commit --allow-empty  --no-edit -m some_msg
    git tag  v0.0.1 -m annotated
    git commit --allow-empty  --no-edit -m some_msg
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


###################
## MUTABLE REPOS ##
###################

def clone_repo(orig_repo, clone_path):
    "Note: `clone_path` must be a sibling of `orig_repo`!"
    parent_dir = (orig_repo / '..')
    ivars = {'orig_dir': orig_repo.basename,
             'clone_dir': clone_path.relto(parent_dir)}

    parent_dir.chdir()
    c = 'git clone %(orig_dir)s %(clone_dir)s' % ivars
    sbp.check_call(c.split())

    clone_path.chdir()
    cmds = """
    git config user.email "test@example.com"
    git config user.name "Testing Bot"
    """ % ivars
    for c in cmds.split('\n'):
        c = c and c.strip()
        if c:
            sbp.check_call(c.split())

    return clone_path


@pytest.fixture()
def monorepo(ok_repo, tmpdir_factory):
    mutable_repo = tmpdir_factory.mktemp('monorepo')
    return clone_repo(ok_repo, mutable_repo)


@pytest.fixture()
def mutable_repo(untagged_repo, tmpdir_factory):
    mutable_repo = tmpdir_factory.mktemp('mutable_repo')
    return clone_repo(untagged_repo, mutable_repo)


def _add_file_to_repo(fpath, text):
    from polyvers.utils.oscmd import cmd

    fpath.write_text(text, encoding='utf-8', ensure=True)
    with fpath.dirpath().as_cwd():
        cmd.git.add(fpath.basename)
        cmd.git.commit(message="added '%s'" % fpath.basename)


def make_setup_py_without_version(setup_dir, pname):
    fpath = (setup_dir / 'setup.py')
    text = """setup(name='%s')""" % pname
    _add_file_to_repo(fpath, text)

    return fpath


def make_setup_py(setup_dir, pname):
    fpath = (setup_dir / 'setup.py')
    text = tw.dedent("""
        setup(
            name='%s',
            version = a func('"something there'),
            )

        """ % pname)
    _add_file_to_repo(fpath, text)

    return fpath
