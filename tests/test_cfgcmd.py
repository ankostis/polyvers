#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.logconfutils import init_logging
from polyvers import cfgcmd
from polyvers.mainpump import collect_cmd
import logging
import os
import pytest

import os.path as osp
import subprocess as sbp


init_logging(level=logging.DEBUG)

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


@pytest.mark.expected_failure()
def test_paths_valid_yaml():
    import yaml
    res = collect_cmd(cfgcmd.InfosCmd().run())
    ystr = '\n'.join(res)

    yaml.load(ystr)


def test_paths_smoketest():
    ret = sbp.check_call('polyvers config infos', env=os.environ)
    assert ret == 0


@pytest.mark.parametrize('case',
                         ['', 'proj', '-e proj', '-el proj'])
def test_show_smoketest(case):
    cmd = ('co2dice config show ' + case).strip()
    ret = sbp.check_call(cmd, env=os.environ)
    assert ret == 0


@pytest.mark.parametrize('case',
                         ['', 'TstampReceiver', 'recv', '-l rec', '-e rec',
                          '-le rec' '-ecl rec', '-cl rec'])
def test_desc_smoketest(case):
    cmd = ('co2dice config desc ' + case).strip()
    ret = sbp.check_call(cmd, env=os.environ)
    assert ret == 0
