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

from .conftest import assert_in_text


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
    ('config show Project', ['Project(Spec'], []),
])
def test_config_cmd(cmd, match, illegal):
    lc = ListConsumer()
    rc = main(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    assert_in_text(lc.items, match, illegal)
    #print('\n'.join(lc.items))


def test_status_cmd_vtags(python_monoproject, caplog, capsys):
    python_monoproject.chdir()

    rc = main('status -v'.split())
    assert rc != 0
    assert_in_text(
        caplog.text,
        require=[
            "No '.polyvers' config-file(s) found!",
            "Auto-discovered 1 sub-project(s)",
            "Cannot auto-discover versioning scheme,"
        ], forbid=[
            "Cannot auto-discover (sub-)project",
        ])
    out, err = capsys.readouterr()
    assert not err and not out

    caplog.clear()
    ## Workaround https://github.com/pytest-dev/pytest/issues/3297
    caplog.handler.stream.truncate(0)

    cmd.git.tag('v0.1.0', m='annotate!')
    rc = main('status -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "No '.polyvers' config-file(s) found!",
            "Auto-discovered 1 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err and 'versions:\n  simple: v0.1.0\n' in out


def test_status_cmd_pvtags(python_monorepo, caplog, capsys):
    python_monorepo.chdir()

    rc = main('status -v'.split())
    assert rc != 0
    assert_in_text(
        caplog.text,
        require=[
            "No '.polyvers' config-file(s) found!",
            "Auto-discovered 2 sub-project(s)",
            "Cannot auto-discover versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
        ])
    out, err = capsys.readouterr()
    assert not err
    assert not out

    caplog.clear()
    ## Workaround https://github.com/pytest-dev/pytest/issues/3297
    caplog.handler.stream.truncate(0)

    cmd.git.tag('base-v0.1.0', m='annotate!')
    rc = main('status -v'.split())
    assert rc == 0
    assert_in_text(
        caplog.text,
        require=[
            "No '.polyvers' config-file(s) found!",
            "Auto-discovered 2 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    ## TODO: report mismatch of project-names/vtags.
    assert 'versions:\n  foo: base-v0.1.0\n' in out
