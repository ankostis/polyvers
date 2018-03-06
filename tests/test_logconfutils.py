#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

import logging
from polyvers import logconfutils as lcu

import pytest


def test_notice_level(caplog):
    lcu.patch_new_level_in_logging(25, 'NOTICE')
    lcu.init_logging(level='NOTICE')

    logging.getLogger().notice("It's there!")
    assert "It's there!" in caplog.text


@pytest.mark.parametrize('inp, exp', [
    ('-v', logging.INFO),
    ('--verbose --verbose', logging.DEBUG),
    ('-verbose', logging.INFO),  # still has one 'v'!
    ('-aa -v -b -v a -- -g', logging.DEBUG),
    ('-vv', logging.DEBUG),
    ('-vvv', logging.DEBUG),
    ('a -vjvkv', logging.DEBUG),
    ('a -vv -v --verbose', logging.DEBUG),
])
def test_log_level_from_argv(inp, exp):
    level = lcu.log_level_from_argv(inp.split())
    assert level == exp
