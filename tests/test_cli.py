#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers.__main__ import main

import pytest


@pytest.mark.parametrize('cmd', [
    'config infos',
    'config desc',
    'config show',
])
def test_config_cmd(cmd):
    main(cmd.split())


def test_status_cmd():
    cmd = 'status'
    main(cmd.split())
