#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
import logging
from pathlib import Path
from polyvers import engrave
from polyvers._vendor.traitlets.config import Config
from polyvers.engrave import GrepSpec, slices_to_ids
from polyvers.logconfutils import init_logging
from polyvers.slice_traitlet import _parse_slice
import re

import pytest

import itertools as itt
import textwrap as tw


init_logging(level=logging.DEBUG, logconf_files=[])


def posixize(paths):
    return [f.as_posix() for f in paths]


def test_prepare_glob_list():
    patterns = tw.dedent("""
        abc
          dddf/
        ## ffgg
          # gg
        !ghh
        /abc

        !/abc
          \\!foo

        //abc
        ./foobar

        123/567
    """).split('\n')
    pats = engrave.prepare_glob_list(patterns)
    assert pats == tw.dedent("""
        **/abc
        **/dddf/
        !**/ghh
        abc
        !abc
        **/!foo
        abc
        foobar
        **/123/567
    """).strip().split('\n')


f1 = """
stays the same
a = b
stays the same
"""
f1_vgrep = {'regex': r'(?m)^(\w+) *= *(\w+)',
            'subst': r'A\1A = B\2B'}
f11 = """
stays the same
AaA = BbB
stays the same
"""

f2 = """
CHANGE
THESE
leave
"""
f2_vgrep = {'regex': r'(?m)^CHANGE\s+THESE$',
            'subst': 'changed them'}
f22 = """
changed them
leave
"""

f3 = """
Lorem ipsum dolor sit amet,
consectetur adipiscing elit,
sed do eiusm
"""

files = {
    'a/f1': f1,
    'a/f2': f2,
    'a/f3': f3,

    'b/f1': f1,
    'b/f2': f2,
    'b/f3': f3,
}

ok_files = {
    'a/f1': f11,
    'a/f2': f22,
    'a/f3': f3,

    'b/f1': f11,
    'b/f2': f22,
    'b/f3': f3,
}


@pytest.fixture
def fileset(tmpdir):
    tmpdir.chdir()
    for fpath, text in files.items():
        (tmpdir / fpath).write_text(tw.dedent(text),
                                    encoding='utf-8', ensure=True)

    return tmpdir


@pytest.mark.parametrize('patterns', [
    ('/a/f*', 'b/f?'),
    ('/a/f*', 'b/f1', '/b/f2', 'b/?3'),
    ('**/f*', ),
    ('/**/f*', ),
])
def test_glob(patterns, fileset):
    files = engrave.glob_files(patterns)
    assert posixize(files) == 'a/f1 a/f2 a/f3 b/f1 b/f2 b/f3'.split()


def test_glob_mybase():
    files = [Path('../a')]
    assert engrave.glob_filter_in_mybase(files, '.') == []
    assert engrave.glob_filter_in_mybase(files, Path('.').resolve() / 'b') == []


def test_glob_relative(fileset):
    (fileset / 'a').chdir()
    files = engrave.glob_files(['*', '../b/f*'])
    assert posixize(files) == 'f1 f2 f3'.split()


def test_glob_otherbases(fileset):
    files = engrave.glob_files(['*/*'], other_bases=['b'])
    assert posixize(files) == 'a/f1 a/f2 a/f3'.split()


slices_test_data = [
    ('-1:', 5, [4]),
    ([1, '3'], 5, [1, 3]),
    (':', 2, [0, 1]),
    (0, 1, [0]),
    (':', 0, []),
    ('5', 2, []),
    ('5', 2, []),
]


@pytest.mark.parametrize('slices, listlen, exp', slices_test_data)
def test_slices_to_ids(slices, listlen, exp):
    thelist = list(range(listlen))
    slices = slices if isinstance(slices, list) else [slices]
    slices = [_parse_slice(s) for s in slices]
    got = slices_to_ids(slices, thelist)
    assert got == exp


@pytest.mark.parametrize('slices, listlen, exp', slices_test_data)
def test_MatchSpec_slicing(slices, listlen, exp):
    m = re.match('.*', '')  # Get hold of some re.match object.
    hits = list(itt.repeat(m, listlen))

    gs = GrepSpec(hits=hits, slices=slices, regex='')
    hits_indices = gs._get_hits_indices()
    assert hits_indices == exp

    gs.hits_indices = hits_indices
    hits = list(gs._yield_masked_hits())
    assert len(hits_indices) == len(hits)


def test_engrave(fileset):
    cfg = Config()
    cfg.Engrave.patterns = ['/a/f*', 'b/f1', '/b/f2', 'b/?3']
    cfg.Engrave.vgreps = [f1_vgrep, f2_vgrep]

    e = engrave.Engrave(config=cfg)
    e.engrave_all()

    for fpath, text in ok_files.items():
        ftxt = (fileset / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)
