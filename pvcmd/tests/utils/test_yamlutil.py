#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from collections import OrderedDict, defaultdict
from polyvers.utils import yamlutil as yu
import io

import pytest

import textwrap as tw


@pytest.mark.parametrize('inp, exp', [
    (None, ''),
    ({}, ''),
    ([], ''),
    (OrderedDict(a=1), "a: 1"),
    (defaultdict(list, a='1'), "a: '1'"),

])
def test_yaml_dump(inp, exp):
    got = yu.ydumps(inp)
    assert got == exp

    sio = io.StringIO()
    yu.ydumps(inp, sio)
    got = sio.getvalue()
    assert got.strip() == exp


def test_YAMLable():
    from polyvers.pvproject import Project

    #assert Project in yu._get_yamel().representer.yaml_representers  # @UndefinedVariable

    prj = Project(pname='a', basepath='b')
    ystr = yu.ydumps([prj])
    print(ystr)
    exp = tw.dedent(r"""
    - amend: false
      basepath: b
      default_version_bump: ^1
      engraves:
      - globs:
        - setup.py
        grafts:
        - encoding: utf-8
          regex: |-
            (?xm)
                \bversion
                (\ *=\ *)
                .+?(,
                \ *[\n\r])+
          slices: []
      - globs:
        - __init__.py
        grafts:
        - encoding: utf-8
          regex: |-
            (?xm)
                \b__version__
                (\ *=\ *)
                (.+[\r\n])
          slices: []
        - encoding: utf-8
          regex: |-
            (?xm)
                \b__updated__
                (\ *=\ *)
                (.+[\r\n])
          slices: []
      - globs:
        - README.rst
        grafts:
        - encoding: utf-8
          regex: \|version\|
          slices: []
        - encoding: utf-8
          regex: \|today\|
          slices: []
      message_body: ''
      message_summary: '{pname}-{current_version} -> {version}'
      pname: a
      pvtag_frmt: ''
      pvtag_regex: ''
      start_version_id: 0.0.0
      tag: false
      tag_vprefixes:
      - v
      - r""")
    assert ystr == exp[1:]
