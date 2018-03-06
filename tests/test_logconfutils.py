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


lcu.patch_new_level_in_logging(25, 'NOTICE')


def test_notice_level(caplog):
    lcu.init_logging(level='NOTICE')

    logging.getLogger().notice("It's there!")
    assert "It's there!" in caplog.text


@pytest.mark.parametrize('inp, exp_level, exp_argv', [
    ('-v', 1, []),
    ('--verbose --verbose', 2, []),
    ('-verbose', 1, '-erbose'),  # still has one 'v'!
    ('-aa -v -b -v a -- -g', 2, '-aa -b a -- -g'),
    ('-vv', 2, []),
    ('-vvv -g', 3, '-g'),
    ('a -vjvkv', 3, 'a -jk'),
    ('a -vv -v --verbose', 4, 'a'),

    ('-q', -1, []),
    ('-klq', -1, '-kl'),
    ('-klq --quiet', -2, '-kl'),

    ('-vvq', 1, []),
    ('-vvqk -v --quiet', 1, '-k'),
])
def test_count_multiflag_in_argv(inp, exp_level, exp_argv):
    inp = inp.split()
    if isinstance(exp_argv, str):
        exp_argv = exp_argv.split()

    verbosity, new_argv = lcu._count_multiflag_in_argv(inp, 'v', 'verbose')
    quitness, new_argv = lcu._count_multiflag_in_argv(new_argv, 'q', 'quiet')
    new_level = verbosity - quitness
    assert new_level == exp_level
    assert new_argv == inp

    verbosity, new_argv = lcu._count_multiflag_in_argv(inp, 'v', 'verbose', True)
    quitness, new_argv = lcu._count_multiflag_in_argv(new_argv, 'q', 'quiet', True)
    assert new_level == exp_level
    assert new_argv == exp_argv


def test_log_level_from_argv_start_level():
    level, _ = lcu.log_level_from_argv((), start_level_index=3)
    assert level == 25  # With NOTICE level patched in.


@pytest.mark.parametrize('inp, exp', [
    ('-v', logging.INFO),
    ('--verbose --verbose', logging.DEBUG),
    ('-verbose', logging.INFO),  # still has one 'v'!
    ('-aa -v -b -v a -- -g', logging.DEBUG),
    ('-vv', logging.DEBUG),
    ('-vvv', logging.NOTSET),
    ('a -vjvkv', logging.NOTSET),
    ('a -vv -v --verbose', logging.NOTSET),

    ('-vvq', logging.INFO),
    ('-vvq -v --quiet', logging.INFO),
    ('-vvvvvq', logging.NOTSET),
])
def test_log_level_from_argv(inp, exp):
    lcu.init_logging(level=logging.INFO)

    level, _ = lcu.log_level_from_argv(inp.split(), start_level_index=3)
    assert level == exp
