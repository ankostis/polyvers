#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import mainpump as mpu
from polyvers.cmdlet import cfgcmd, cmdlets
from polyvers.cmdlet.cfgcmd import ConfigCmd, all_configurables
from polyvers.logconfutils import init_logging
import logging

import pytest


init_logging(level=logging.DEBUG)


@pytest.mark.expected_failure()
def test_infos_valid_yaml():
    from ruamel import yaml  # @UnresolvedImport
    res = mpu.collect_cmd(cfgcmd.InfosCmd().run())
    ystr = '\n'.join(res)

    yaml.safe_load(ystr)


def test_infos_smoketest():
    cmd = ConfigCmd.make_cmd(['infos'])  # @UndefinedVariable
    res = mpu.collect_cmd(cmd.start())
    assert len(res) > 10


@pytest.mark.parametrize(
    'case, nlines', [
        ([], 23),
        ('path', 2),
        ('-e path'.split(), 2),
        ('-el path'.split(), 5)
    ])
def test_show_smoketest(case, nlines):
    if not isinstance(case, list):
        case = [case]
    cmd = ConfigCmd.make_cmd(['show'] + case)
    res = mpu.collect_cmd(cmd.start(), dont_coalesce=True, assert_ok=True)
    assert len(res) >= nlines


@pytest.mark.parametrize(
    'case, nlines', [
        ([], 20),
        ('path', 1),
        ('-l verb'.split(), 2),
        ('-e verb'.split(), 2),
        ('-le verb'.split(), 2),
        ('-ecl cmd'.split(), 5),
        ('-cl cmd'.split(), 5)
    ])
def test_desc_smoketest(case, nlines):
    if not isinstance(case, list):
        case = [case]
    cmd = ConfigCmd.make_cmd(['desc'] + case)
    res = mpu.collect_cmd(cmd.start(), dont_coalesce=True, assert_ok=True)
    assert len(res) >= nlines


all_cmds = [c
            for c in all_configurables(ConfigCmd())
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
    assert len(list(c.emit_examples())) > 1
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
