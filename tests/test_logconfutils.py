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


argv_data = [
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
    ('-vvvvvq', 4, []),
]


@pytest.mark.parametrize('inp, exp_verbose, exp_argv', argv_data)
def test_count_multiflag_in_argv(inp, exp_verbose, exp_argv):
    inp = inp.split()
    if isinstance(exp_argv, str):
        exp_argv = exp_argv.split()

    verbosity, new_argv = lcu._count_multiflag_in_argv(inp, 'v', 'verbose')
    quitness, new_argv = lcu._count_multiflag_in_argv(new_argv, 'q', 'quiet')
    new_level = verbosity - quitness
    assert new_level == exp_verbose
    assert new_argv == inp

    verbosity, new_argv = lcu._count_multiflag_in_argv(inp, 'v', 'verbose', True)
    quitness, new_argv = lcu._count_multiflag_in_argv(new_argv, 'q', 'quiet', True)
    new_level = verbosity - quitness
    assert new_level == exp_verbose
    assert new_argv == exp_argv


def test_log_level_from_argv_start_level():
    start_level = 30
    level, _ = lcu.log_level_from_argv((), start_level=start_level)
    assert level == start_level

    with pytest.raises(ValueError, match=r"Expecting an \*integer\*"):
        lcu.log_level_from_argv((), start_level=3.14)

    with pytest.raises(ValueError, match=r"Expecting an \*existing\*"):
        lcu.log_level_from_argv((), start_level=-500)


@pytest.mark.parametrize('inp, exp_verbose, _', argv_data)
def test_log_level_from_argv(inp, exp_verbose, _):
    lcu.init_logging(level=logging.INFO)

    start_level = 30
    level, _ = lcu.log_level_from_argv(inp.split(), start_level=start_level)

    levels = list(sorted(logging._levelToName))
    start_level_index = levels.index(start_level)
    exp_level_index = max(0, min(len(levels) - 1, start_level_index - exp_verbose))
    assert level == levels[exp_level_index]
