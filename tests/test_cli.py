#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from collections import OrderedDict, defaultdict
from polyvers import cli, cmdlets
from polyvers.__main__ import main
from polyvers.mainpump import ListConsumer
from polyvers.oscmd import cmd

import pytest

import textwrap as tw

from .conftest import assert_in_text, clearlog, make_setup_py


@pytest.mark.parametrize('inp, exp', [
    (None, None),
    ({}, ''),
    ([], ''),
    (OrderedDict(a=1), "a: 1"),
    (defaultdict(list, a='1'), "a: '1'"),

])
def test_yaml_dump(inp, exp):
    got = cli.ydumps(inp)
    assert got == exp


all_cmds = [c
            for c in cli.PolyversCmd().all_app_configurables
            if issubclass(c, cmdlets.Cmd)]


@pytest.mark.parametrize('cmd', all_cmds)
def test_all_cmds_help_smoketest(cmd):
    cmd.class_get_help()
    cmd.class_config_section()
    cmd.class_config_rst_doc()

    c = cmd()
    c.print_help()
    c.document_config_options()
    c.print_alias_help()
    c.print_flag_help()
    c.print_options()
    c.print_subcommands()
    c.print_examples()
    #assert len(list(c.emit_examples())) > 1  TODO: Require cmd examples
    c.print_help()


@pytest.mark.parametrize('cmd', all_cmds)
def test_all_cmds_help_version(cmd, capsys):
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['help'])

    ## Check cmdlet interpolations work.
    #
    out, err = capsys.readouterr()
    assert not err
    assert '{cmd_chain}' not in out
    assert '{appname}' not in out

    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help-all'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--version'])


@pytest.mark.parametrize('cmd, match, illegal', [
    ('config infos', [], ['config_paths: null']),
    ('config desc', ['--Cmd.config_paths=', 'StatusCmd'], []),
    ('config desc bump -c', ['Increase the version of project', 'BumpCmd'], []),
    ('config show Project', ['Project(Spec'], []),
    ('config show Project.tag', ["tag_vprefixes = ('v', 'r')"], []),
])
def test_config_cmd(cmd, match, illegal):
    ## VERY IMPORTANT TCs FOR ConfigCmd!!!
    lc = ListConsumer()
    rc = main(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    assert_in_text(lc.items, match, illegal)
    #print('\n'.join(lc.items))


def test_status_cmd_vtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## No flag/setup.py
    #  Both auto-discoveries fail
    #
    rc = main('status -v'.split())
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
    ## --monorepo
    #
    clearlog(caplog)

    rc = main('status --mono-project -v'.split())
    assert rc != 0
    assert_in_text(
        caplog.text,
        require=[
            r"Cannot auto-discover \(sub-\)project",
        ], forbid=[
            r"Auto-discovered versioning scheme",
            r"Auto-discovered \d+ sub-project\(s\)",
            r"Cannot auto-discover versioning scheme,"
        ],
        is_regex=True)
    out, err = capsys.readouterr()
    assert not err and not out

    ##############
    ## setup.py + --monorepo
    #
    clearlog(caplog)
    make_setup_py(mutable_repo, 'simple')

    rc = main('status --mono-project -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "Auto-discovered 1 sub-project(s)",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert 'simple:\n  version:\n' == out

    rc = main('status --mono-project --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert 'simple:\n  version:\n  history: []\n  basepath: .\n' == out

    ##############
    ## TAG REPO
    #
    clearlog(caplog)

    cmd.git.tag('v0.1.0', m='annotate!')
    rc = main('status -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "Auto-discovered 1 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert 'simple:\n  version: v0.1.0\n' == out

    rc = main('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = tw.dedent("""\
        simple:
          version: v0.1.0
          history:
          - v0.1.0
          basepath: .
    """)
    assert exp == out

    rc = main('status --all simple'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert exp == out

    rc = main('status --all simple foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert exp == out

    rc = main('status --all foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not out


def test_status_cmd_pvtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## No flag/setup.py
    #  Both auto-discoveries fail
    #
    rc = main('status -v'.split())
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
    ## --monorepo
    #
    clearlog(caplog)

    rc = main('status --monorepo -v'.split())
    assert rc != 0
    assert_in_text(
        caplog.text,
        require=[
            r"Cannot auto-discover \(sub-\)project",
        ], forbid=[
            r"Auto-discovered versioning scheme",
            r"Auto-discovered \d+ sub-project\(s\)",
            r"Cannot auto-discover versioning scheme,"
        ],
        is_regex=True)
    out, err = capsys.readouterr()
    assert not err and not out

    ##############
    ## setup.py + --monorepo
    #
    clearlog(caplog)
    make_setup_py(mutable_repo, 'base')
    make_setup_py(mutable_repo / 'foo_project', 'foo')

    rc = main('status --monorepo -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "Auto-discovered 2 sub-project(s)",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert 'base:\n  version:\nfoo:\n  version:\n' == out

    rc = main('status --monorepo --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert ('base:\n  version:\n  history: []\n  basepath: .\nfoo:\n  '
            'version:\n  history: []\n  basepath: foo_project\n') == out

    ##############
    ## TAG REPO
    #
    clearlog(caplog)

    cmd.git.tag('base-v0.1.0', m='annotate!')
    rc = main('status -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "Auto-discovered 2 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    exp = "base:\n  version: base-v0.1.0\nfoo:\n  version:\n"
    assert exp == out

    rc = main('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = tw.dedent("""\
    base:
      version: base-v0.1.0
      history:
      - base-v0.1.0
      basepath: .
    foo:
      version:
      history: []
      basepath: foo_project
    """)
    assert exp == out

    rc = main('status --all base foo'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert exp == out

    rc = main('status --all base foo BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert exp == out

    rc = main('status --all BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not out

    rc = main('status --all foo BAD'.split())
    assert rc == 0
    exp = tw.dedent("""\
    foo:
      version:
      history: []
      basepath: foo_project
    """)
    out, err = capsys.readouterr()
    assert exp == out
