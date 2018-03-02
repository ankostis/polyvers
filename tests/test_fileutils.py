#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import fileutils

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
