#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

import logging
from polyvers import cfgcmd
from polyvers import mainpump as mpu
from polyvers.cfgcmd import ConfigCmd
from polyvers.logconfutils import init_logging

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
    assert len(res) > 10, res


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
    assert len(res) >= nlines, res


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
    assert len(res) >= nlines, res
