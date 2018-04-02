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
from polyvers.cmdlet.slice_traitlet import _parse_slice
from polyvers.logconfutils import init_logging
from polyvers.pvproject import Project, Graft, _slices_to_ids
from pprint import pformat  # noqa: F401  @UnusedImport
from tests import conftest
import logging
import re

import pytest

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
    matches = list(re.match('.', str(i)) for i in range(listlen))

    gs = Graft.new(slices=slices, regex='')

    matches = gs.sliced_matches(matches)
    assert len(exp) == len(matches)
    assert [h.group() for h in matches] == [str(i) for i in exp]


def test_overlapped_matches():
    from unittest.mock import Mock

    def match(span):
        return Mock(**{'span.return_value': span})

    ranges = [
        (3, 5),
        (1, 2),
        (1, 3),  # Gone
        (2, 3),
        (2, 4),  # Gone
        (5, 7),
        (3, 3),
        (3, 4),  # Gone
        (1, 1),
        (7, 7),
    ]
    res = engrave.overlapped_matches([match(r) for r in ranges])
    #print('\n'.join(str(s) for s in res))
    assert {r.span() for r in res} == {
        (1, 3),
        (2, 4),
        (3, 4),
    }

    res = engrave.overlapped_matches([match(r) for r in ranges],
                                     no_touch=True)
    print('\n'.join(str(s) for s in res))
    assert {r.span() for r in res} == {
        (1, 3),
        (2, 3),
        (2, 4),
        (5, 7),
        (3, 3),
        (3, 4),
        (1, 1),
    }


def test_scan(fileset_mutable, orig_files, f1_graft, f2_graft, caplog):
    caplog.set_level(0)
    fileset_mutable.chdir()
    cfg = Config()
    cfg.Project.pname = 'prj1'
    cfg.Project.engraves = [{
        'globs': ['/a/f*', 'b/f1', '/b/f2', 'b/?3'],
        'grafts': [f1_graft, f2_graft],
    }]

    prj = Project(config=cfg)
    fproc = engrave.FileProcessor()
    match_map = fproc.scan_projects([prj])
    assert len(match_map) == 6  # nfiles
    #print(pformat(match_map))
    assert fproc.nmatches() == 4

    for fpath, text in orig_files.items():
        ftxt = (fileset_mutable / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)


def test_engrave(fileset_mutable, ok_files, f1_graft, f2_graft, caplog):
    caplog.set_level(0)
    fileset_mutable.chdir()
    cfg = Config()
    cfg.Project.pname = 'prj1'
    cfg.Project.current_version = '0.0.0'
    cfg.Project.version = '0.0.1'
    cfg.Project.engraves = [{
        'globs': ['/a/f*', 'b/f1', '/b/f2', 'b/?3'],
        'grafts': [f1_graft, f2_graft],
    }]

    prj = Project(config=cfg)
    fproc = engrave.FileProcessor()
    match_map = fproc.scan_projects([prj])
    fproc.engrave_matches(match_map)
    #print(pformat(match_map))
    assert fproc.nmatches() == 4

    for fpath, text in ok_files.items():
        ftxt = (fileset_mutable / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)


def test_engrave_duped_scans(fileset_mutable, ok_files, f1_graft, f2_graft, caplog):
    caplog.set_level(0)
    fileset_mutable.chdir()
    cfg = Config()
    cfg.Project.pname = 'prj1'
    cfg.Project.current_version = '0.0.0'
    cfg.Project.version = '0.0.1'
    cfg.Project.engraves = [{
        'globs': ['/a/f*'],
        'grafts': [f1_graft, f1_graft, f2_graft, f2_graft],
    }, {
        'globs': ['b/f1', 'b/?3'],
        'grafts': [f1_graft, f2_graft],
    }, ]
    prj1 = Project(config=cfg)

    cfg.Project.engraves = [{
        'globs': ['/a/f*', '/b/f2', 'b/?3'],
        'grafts': [f1_graft, f2_graft],
    }]
    prj2 = Project(config=cfg)

    fproc = engrave.FileProcessor()
    match_map = fproc.scan_projects([prj1, prj2])
    fproc.engrave_matches(match_map)
    #print(pformat(match_map))
    assert fproc.nmatches() == 4

    for fpath, text in ok_files.items():
        ftxt = (fileset_mutable / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)
