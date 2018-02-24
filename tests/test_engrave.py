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

import pytest

import textwrap as tw


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
        **/123/567
    """).strip().split('\n')


f1 = """
stays the same
a = b
stays the same
"""
f1_vgrep = (r'^(\w+) *= *(\w+)', r'A\1A = B\2B')
f11 = """
stays the same
AaA = BbB
stays the same
"""

f2 = """
CHANGE leave
leave
"""
f2_vgrep = ('CHANGE', 'changed')
f22 = """
changed leave
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
    assert files == 'a/f1 a/f2 a/f3 b/f1 b/f2 b/f3'.split()


def test_engrave(fileset):
    cfg = Config()
    cfg.Engrave.files = ['/a/f*', 'b/f1', '/b/f2', 'b/?3']
    cfg.Engrave.vgreps = [f1_vgrep, f2_vgrep]

    e = engrave.Engrave(config=cfg)
    e.engrave_all()

    for fpath, text in ok_files.items():
        ftxt = (fileset / fpath).read_text('utf-8')
        assert ftxt == tw.dedent(text)
