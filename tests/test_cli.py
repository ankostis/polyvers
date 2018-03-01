#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers import cli, cmdlets
from polyvers.__main__ import main
from polyvers.mainpump import ListConsumer

import pytest

from .conftest import assert_in_text


all_cmds = [c
            for c in cli.PolyversCmd().all_app_configurables
            if issubclass(c, cmdlets.Cmd)]


def test_git_repo(ok_repo, no_repo):
    ok_repo.chdir()
    got = cli.find_git_root()
    assert ok_repo.samefile(got)

    ndir = (ok_repo / 'abc')
    ndir.mkdir()
    ndir.chdir()
    got = cli.find_git_root()
    assert ok_repo.samefile(got)

    ndir = (ndir / 'def')
    ndir.mkdir()
    ndir.chdir()
    got = cli.find_git_root()
    assert ok_repo.samefile(got)

    no_repo.chdir()
    got = cli.find_git_root()
    assert got is None


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
def test_all_cmds_help_version(cmd):
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['help'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help-all'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--version'])


@pytest.mark.parametrize('cmd, match, illegal', [
    ('config infos', [], ['config_paths: null']),
    ('config desc', ['--Cmd.config_paths=', 'StatusCmd'], []),
    ('config show Project', ['Project(Spec)'], []),
])
def test_config_cmd(cmd, match, illegal):
    lc = ListConsumer()
    rc = main(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    assert_in_text(lc.items, match, illegal)
    #print('\n'.join(lc.items))


def test_status_cmd():
    cmd = 'status'
    lc = ListConsumer()
    rc = main(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    #print('\n'.join(lc.items))
