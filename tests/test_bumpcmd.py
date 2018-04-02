#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers.__main__ import main
from polyvers.oscmd import cmd
import re

import textwrap as tw

from .conftest import (
    assert_in_text, clearlog,
    make_setup_py_without_version, make_setup_py)


def test_bump_cmd_bad(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## No flag/setup.py
    #  Both auto-discoveries fail
    #
    rc = main('bump -v 0.0.1'.split())
    assert rc != 0
    assert_in_text(
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
    clearlog(caplog)
    make_setup_py_without_version(mutable_repo, 'base')

    rc = main('bump --mono-project -v 1.1.1'.split())
    assert rc != 0
    assert_in_text(
        caplog.text,
        require=[
            r"Auto-discovered \d+ sub-project\(s\)",
            r"No version-engraving matched, bump aborted.",
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
    clearlog(caplog)
    setupy_fpath = make_setup_py(mutable_repo, 'simple')

    rc = main('bump  -v --mono-project 0.0.1'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            r" Bumped projects: simple-0.0.0 --> 0.0.1",
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
        chore(ver): bump simple-0.0.0 -> 0.0.1  (tag: r0.0.1, latest)
        added 'setup.py'  (HEAD -> master, tag: v0.0.1)
        some_msg  (origin/master, origin/HEAD)""")
    assert exp in gitlog

    cmd.git.checkout('latest')  # Branch-name from BumpCmd.release_branch.
    setuppy_text = setupy_fpath.read_text(encoding='utf-8')
    assert re.search("version *= *'0.0.1',", setuppy_text)


def test_bump_cmd_monorepo(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## --monorepo
    #
    clearlog(caplog)
    setupy_fpath = make_setup_py(mutable_repo, 'simple')

    rc = main('bump  -v --monorepo 0.0.1'.split())
    # with capsys.disabled():
    #     print(caplog.text)
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            r" Bumped projects: simple-0.0.0 --> 0.0.1",
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
        chore(ver): bump simple-0.0.0 -> 0.0.1  (tag: simple-r0.0.1, latest)
        added 'setup.py'  (HEAD -> master, tag: simple-v0.0.1)
        some_msg  (origin/master, origin/HEAD)""")
    assert exp in gitlog

    cmd.git.checkout('latest')  # Branch-name from BumpCmd.release_branch.
    setuppy_text = setupy_fpath.read_text(encoding='utf-8')
    assert re.search("version *= *'0.0.1',", setuppy_text)