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

import os.path as osp


init_logging(level=logging.DEBUG)

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


@pytest.mark.expected_failure()
def test_infos_valid_yaml():
    import yaml
    res = mpu.collect_cmd(cfgcmd.InfosCmd().run())
    ystr = '\n'.join(res)

    yaml.load(ystr)


def test_infos_smoketest():
    cmd = ConfigCmd.make_cmd(['infos'])
    res = mpu.collect_cmd(cmd.start())
    assert len(res) > 10, res


@pytest.mark.parametrize('case',
                         [[], 'path', '-e path'.split(), '-el path'.split()])
def test_show_smoketest(case):
    if not isinstance(case, list):
        case = [case]
    cmd = ConfigCmd.make_cmd(['show'] + case)
    res = mpu.collect_cmd(cmd.start(), dont_coalesce=True, assert_ok=True)
    assert len(res) == 0, res


@pytest.mark.parametrize('case',
                         [[], 'path', '-l path'.split(),
                          '-e path'.split(), '-le path'.split(),
                          '-ecl path'.split(), '-cl rec'.split()])
def test_desc_smoketest(case):
    if not isinstance(case, list):
        case = [case]
    cmd = ConfigCmd.make_cmd(['desc'] + case)
    res = mpu.collect_cmd(cmd.start(), dont_coalesce=True, assert_ok=True)
    assert len(res) > 10, res
