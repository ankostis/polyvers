#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers.__main__ import main
from polyvers.mainpump import ListConsumer

import pytest

from .conftest import assert_in_text


@pytest.mark.parametrize('cmd, match, illegal', [
    ('config infos', [], ['config_paths: null']),
    ('config desc', ['--Cmd.config_paths=', 'StatusCmd'], []),
    ('config show Project', ['Project(Base)'], []),
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
