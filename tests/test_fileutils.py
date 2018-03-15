#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from pathlib import Path
from polyvers import fileutils
import os

import pytest


ensure_ext_data = [
    (('foo', '.bar'), 'foo.bar'),
    (('foo.', '.bar'), 'foo.bar'),
    (('foo', 'bar'), 'foo.bar'),
    (('foo.', 'bar'), 'foo.bar'),
    (('foo.bar', 'bar'), 'foo.bar'),
    (('foobar', 'bar'), 'foobar'),
    (('foobar', '.bar'), 'foobar.bar'),
    (('foo.BAR', '.bar'), 'foo.BAR'),
    (('foo.DDD', '.bar'), 'foo.DDD.bar'),
]


@pytest.mark.parametrize('inp, exp', ensure_ext_data)
def test_ensure_ext(inp, exp):
    got = fileutils.ensure_file_ext(*inp)
    assert got == exp


def test_ensure_ext_regex():
    inp = 'foo.xlt', '.xlsx', r'\.xl\w{1,2}'
    exp = 'foo.xlt'
    got = fileutils.ensure_file_ext(*inp, is_regex=True)
    assert got == exp


def test_git_repo(ok_repo, no_repo):
    ok_repo.chdir()
    got = fileutils.find_git_root()
    assert ok_repo.samefile(got)

    ndir = (ok_repo / 'abc')
    ndir.mkdir()
    ndir.chdir()
    got = fileutils.find_git_root()
    assert ok_repo.samefile(got)

    ndir = (ndir / 'def')
    ndir.mkdir()
    ndir.chdir()
    got = fileutils.find_git_root()
    assert ok_repo.samefile(got)

    no_repo.chdir()
    got = fileutils.find_git_root()
    assert got is None


base_or_same_data = [
    ('a', 'a/f1', True, True),
    ('a', 'a/f1', True, True),
    ('a', 'b/f1', False, False),

    ('.', 'b/f1', True, True),

    ('a', 'a', None, None),
    ('a', 'b/../a', None, None),
    ('a', 'b/../a', None, None),
    ('a/f1', 'a/f1', None, None),
    ('.', '.', None, None),
    ('./a/..', '.', None, None),
    ('.', './a/..', None, None),

    ('BAD', 'a', False, False),
    ('a', 'a/BAD', True, True),
    ('a/BAD', 'a', False, False),
    ('BAD', 'BAD', None, None),

    ## Resolve on unknowns

    ('BAD', 'BAD/../BAD', True if os.name == 'nt' else None, True),
    ('BAD/../BAD', 'BAD', False if os.name == 'nt' else None, False),

    ('BAD', 'BAD/a/..', None, True),  # Strict differ!
    ('BAD/a/..', 'BAD', None, False),  # Strict differ!

    ('BAD/..', 'BAD/..', None, None),
    ('BAD/../bar', 'BAD/../bar', None, None),

    ## LITERAL matches (surprising!)

    ('BAD', 'BAD/..', True, True),
    ('BAD', 'BAD/../bar', True, True),
]


@pytest.mark.parametrize('basepath, longpath, exp, exp_strict', base_or_same_data)
def test_is_base_or_same(fileset, basepath, longpath, exp, exp_strict):
    fileset.chdir()
    assert fileutils._is_base_or_same(Path(basepath), Path(longpath)) is exp
    assert fileutils._is_base_or_same(Path(basepath), Path(longpath),
                                      strict=True) is exp_strict


@pytest.mark.parametrize('f1, f2, exp', [
    ('a', 'a/f1', False),
    ('a/f1', 'a/f1', True),
    ('BAD', 'BAD', None),
])
def test_is_same_file(fileset, f1, f2, exp):
    fileset.chdir()
    assert fileutils._is_same_file(Path(f1), Path(f2)) is exp
