#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers import cli
from polyvers.utils.oscmd import cmd
import re

import pytest

import textwrap as tw

from .conftest import (
    check_text, make_setup_py_without_version, make_setup_py, make_init_py)


@pytest.fixture(autouse=True)
def set_homedir(tmpdir_factory, monkeypatch):
    import os

    homedir = tmpdir_factory.mktemp('homedir')
    monkeypatch.setitem(os.environ, 'HOME', str(homedir))


def test_bump_cmd_bad(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## No flag/setup.py
    #  Both auto-discoveries fail
    #
    rc = cli.run('bump -v 0.0.1'.split())
    assert rc != 0
    check_text(
        caplog.text,
        require=[
            r"Cannot auto-discover versioning scheme,"
        ], forbid=[
            r"Auto-discovered versioning scheme",
            r"Auto-discovered \d+ sub-project\(s\)",
            r"Cannot auto-discover \(sub-\)project",
        ],
        is_regex=True)
    out, err = capsys.readouterr()
    assert not err and not out

    ##############
    ## --mono-project
    #  no-current version
    #
    caplog.clear()
    make_setup_py_without_version(mutable_repo, 'base')

    rc = cli.run('bump --mono-project -v 1.1.1'.split())
    assert rc != 0
    check_text(
        caplog.text,
        require=[
            r"Auto-discovered \d+ sub-project\(s\)",
            r"No version-engravings happened, bump aborted.",
        ], forbid=[
            r"Auto-discovered versioning scheme",
            r"Cannot auto-discover versioning scheme,"
        ],
        is_regex=True)
    out, err = capsys.readouterr()
    assert not err and not out


def test_bump_cmd_mono_project(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## --mono-project
    #
    caplog.clear()
    setupy_fpath = make_setup_py(mutable_repo, 'simple')
    rc = cli.run('bump  -v --mono-project 0.0.1'.split())
    assert rc == 1
    check_text(
        caplog.text,
        require=[
            'No version-engravings happened, bump aborted'
        ], forbid=[
            r"Bumped projects",
            r"simple-0.0.0 --> 0.0.1",
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not out and not err

    init_fpath = make_init_py(mutable_repo, 'simple')
    caplog.clear()
    rc = cli.run('bump  -v --mono-project 0.0.1'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            r"Bumped projects",
            r"simple-0.0.0 --> 0.0.1",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not out and not err

    gitlog = cmd.git.log(format="format:%s %d", all=True)
    # with capsys.disabled():
    #     print(gitlog)
    exp = tw.dedent("""\
        chore(ver): bump simple-r0.0.0 -> 0.0.1  (tag: r0.0.1, latest)
        added '__init__.py'  (HEAD -> master, tag: v0.0.1)
        added 'setup.py'
        some_msg  (origin/master, origin/HEAD)""")
    check_text(gitlog, exp)

    cmd.git.checkout('latest')  # Branch-name from BumpCmd.release_branch.
    setuppy_text = setupy_fpath.read_text(encoding='utf-8')
    assert re.search("version *= *'something there',", setuppy_text), setuppy_text

    init_text = init_fpath.read_text(encoding='utf-8')
    assert re.search("__version__   *= *'0.0.1'", init_text), init_text
    # time: 2018-05-31T05:00:17.549448
    assert re.search(r"__updated__   *= *'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d.\d{6}",
                     init_text), init_text


def test_bump_cmd_monorepo(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## --monorepo
    #
    caplog.clear()
    setupy_fpath = make_setup_py(mutable_repo, 'simple')
    init_fpath = make_init_py(mutable_repo, 'simple')
    rc = cli.run('bump  -v --monorepo 0.0.1'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            r"Bumped projects",
            r"simple-0.0.0 --> 0.0.1",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not out and not err

    gitlog = cmd.git.log(format="format:%s %d", all=True)
    # with capsys.disabled():
    #     print(gitlog)
    exp = tw.dedent("""\
        chore(ver): bump simple-r0.0.0 -> 0.0.1  (tag: simple-r0.0.1, latest)
        added '__init__.py'  (HEAD -> master, tag: simple-v0.0.1)
        added 'setup.py'
        some_msg  (origin/master, origin/HEAD)""")
    check_text(gitlog, exp)

    cmd.git.checkout('latest')  # Branch-name from BumpCmd.release_branch.
    setuppy_text = setupy_fpath.read_text(encoding='utf-8')
    assert re.search("version *= *'something there',", setuppy_text), setuppy_text

    init_text = init_fpath.read_text(encoding='utf-8')
    assert re.search("__version__   *= *'0.0.1'", init_text), init_text
    # time: 2018-05-31T05:00:17.549448
    assert re.search(r"__updated__   *= *'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d.\d{6}",
                     init_text), init_text

    # # FIXME: project fails with return mg['version']!
    # rc = cli.run('init'.split())
    # _ = capsys.readouterr()
    # assert rc == 1

    rc = cli.run('bump  --amend badver'.split())
    assert rc == 1
    capsys.readouterr()
    check_text(
        caplog.text,
        require=[
            r"Unknown project",
        ])

    caplog.clear()
    rc = cli.run('bump  -v --amend'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            r"Bumped projects",
            r"simple-0.0.0 --> 0.0.1",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not out and not err

    caplog.clear()
    rc = cli.run('bump  -v --amend --engrave-only'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            r"Engraved projects",
            r"simple-0.0.0 --> 0.0.1",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
            r"Bumped projects",
        ])
    out, err = capsys.readouterr()
    assert not out and not err
