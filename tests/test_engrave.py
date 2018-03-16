#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from pathlib import Path
from polyvers import engrave
from polyvers._vendor.traitlets.config import Config
from polyvers.engrave import GraftSpec, _slices_to_ids
from polyvers.logconfutils import init_logging
from polyvers.slice_traitlet import _parse_slice
from tests import conftest
import logging
import re

import pytest

import itertools as itt
import textwrap as tw


init_logging(level=logging.DEBUG, logconf_files=[])


def posixize(paths):
    return [f.as_posix() for f in paths]


def test_prepare_glob_pairs():
    globs = tw.dedent("""
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
    pat_pairs = engrave._prepare_glob_pairs(globs)
    assert pat_pairs == [
        ('**/abc', None),
        ('**/dddf/', None),
        (None, '**/ghh'),
        ('abc', None),
        (None, 'abc'),
        ('**/!foo', None),
        ('abc', None),
        ('foobar', None),
        ('**/123/567', None),
    ]


@pytest.fixture
def fileset_mutable(tmpdir_factory, fileset, orig_files):
    tmpdir = tmpdir_factory.mktemp('engraveset_mutable')
    return conftest._make_fileset(tmpdir, orig_files)


################
## TEST CASES ##
################

@pytest.mark.parametrize('globs', [
    ('/a/f*', 'b/f?'),
    ('/a/f*', 'b/f1', '/b/f2', 'b/?3'),
    ('**/f*', ),
    ('/**/f*', ),
])
def test_glob(globs, fileset):
    fileset.chdir()
    files = engrave.glob_files(globs)
    assert posixize(files) == 'a/f1 a/f2 a/f3 b/f1 b/f2 b/f3'.split()


@pytest.mark.parametrize('globs, exp', [
    ('!a !/b/ /**/f*', ''),
    ('/a/f* !b /b/f*', 'a/f1 a/f2 a/f3'),
    ('/a/f* !/b/ /b/f*', 'a/f1 a/f2 a/f3'),
    ('!b/ /a/f*', 'a/f1 a/f2 a/f3'),

    ('/a/f* /b/f* !a/ !b/', 'a/f1 a/f2 a/f3 b/f1 b/f2 b/f3'),
])
def test_glob_negatives(globs, exp, fileset):
    fileset.chdir()
    files = engrave.glob_files(globs.split())
    assert posixize(files) == exp.split()


def test_glob_mybase():
    files = [Path('../a')]
    assert engrave._glob_filter_in_mybase(files, '.') == []
    assert engrave._glob_filter_in_mybase(files, Path('.').resolve() / 'b') == []


def test_glob_relative(fileset):
    (fileset / 'a').chdir()
    files = engrave.glob_files(['*', '../b/f*'])
    assert posixize(files) == 'f1 f2 f3'.split()


def test_glob_filter_out_other_bases(fileset, orig_files):
    fileset.chdir()
    search_files = [Path(f) for f in orig_files]
    obases = [Path('b')]
    filtered_files = engrave._glob_filter_out_other_bases(search_files, obases)
    assert filtered_files == [f for f in search_files
                              if str(f).startswith('a')]


def test_glob_otherbases(fileset, orig_files):
    fileset.chdir()
    files = engrave.glob_files(['*/*'], other_bases=['b'])
    assert posixize(files) == 'a/f1 a/f2 a/f3'.split()

    ## `mybase` wins coinciding `obases`.
    #
    files = engrave.glob_files(['*/*'],
                               other_bases=['.'])
    assert files == [Path(f) for f in orig_files]


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
    got = _slices_to_ids(slices, thelist)
    assert got == exp


@pytest.mark.parametrize('slices, listlen, exp', slices_test_data)
def test_MatchSpec_slicing(slices, listlen, exp):
    m = re.match('.*', '')  # Get hold of some re.match object.
    hits = list(itt.repeat(m, listlen))

    gs = GraftSpec(hits=hits, slices=slices, regex='')
    hits_indices = gs._get_hits_indices()
    assert hits_indices == exp

    gs.hits_indices = hits_indices
    hits = gs.valid_hits()
    assert len(hits_indices) == len(hits)


def test_engrave(fileset_mutable, ok_files, f1_graft, f2_graft):
    fileset_mutable.chdir()
    cfg = Config()
    cfg.Engrave.globs = ['/a/f*', 'b/f1', '/b/f2', 'b/?3']
    cfg.Engrave.grafts = [f1_graft, f2_graft]

    e = engrave.Engrave(config=cfg)
    subs_map = e.scan_and_engrave()
    nhits = sum(fspec.nhits for fspec in subs_map.values())
    nsubs = sum(fspec.nsubs for fspec in subs_map.values())
    assert nhits == nsubs == 4

    for fpath, text in ok_files.items():
        ftxt = (fileset_mutable / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)


def test_engrave_subs_None(fileset_mutable, f1_graft, f2_graft):
    fileset_mutable.chdir()

    f1_graft['subst'] = None

    cfg = Config()
    cfg.Engrave.globs = ['/a/f*', 'b/f1', '/b/f2', 'b/?3']
    cfg.Engrave.grafts = [f1_graft, f2_graft]

    e = engrave.Engrave(config=cfg)

    hits_map = e.scan_hits()
    nhits = sum(fspec.nhits for fspec in hits_map.values())
    assert nhits == 4

    subs_map = e.scan_and_engrave()
    nhits2 = sum(fspec.nhits for fspec in subs_map.values())
    nsubs = sum(fspec.nsubs for fspec in subs_map.values())
    assert nhits2 == 4
    assert nsubs == 2

    ok_files = {
        'a/f1': conftest.f1,
        'a/f2': conftest.f22,
        'a/f3': conftest.f3,

        'b/f1': conftest.f1,
        'b/f2': conftest.f22,
        'b/f3': conftest.f3,
    }

    for fpath, text in ok_files.items():
        ftxt = (fileset_mutable / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)


def test_scan_engrave(fileset_mutable, f1_graft, f2_graft):
    fileset_mutable.chdir()
    cfg = Config()
    globs = ['/a/f*', 'b/f1', '/b/f2', 'b/?3']
    cfg.Engrave.grafts = [f1_graft, f2_graft]

    e1 = engrave.Engrave.new(globs=globs, grafts=[f1_graft])
    e2 = engrave.Engrave.new(globs=globs, grafts=[f2_graft])

    hits_map = engrave.scan_engraves([e1, e2])
    assert isinstance(hits_map, dict)
    nhits = sum(fspec.nhits for fspec in hits_map.values())

    assert nhits == 4
    assert len(hits_map) == 6
