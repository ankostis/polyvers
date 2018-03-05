#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.oscmd import cmd

import pytest


def test_cmd_building(ok_repo):
    ok_repo.chdir()

    c = cmd.foo._(c=True).Bang_bar._("any_thing'", flag_dang=True, no=False)
    cmdlist = c._cmdlist
    assert cmdlist == ['foo', '-c', 'Bang-bar', "any_thing'", '--flag-dang', '--no-no']

    assert cmd.cmd._(*'abc', J=3, K='3')._cmdlist == 'cmd a b c -J3 -K3'.split()

    assert cmd.cmd._(flag='', f='').top._cmdlist == 'cmd --flag= -f top'.split()


def test_to_str():
    assert str(cmd.cmd._(flag='', f='').top) == 'Cli(cmd --flag= -f top)'


def test_negate_single_letter():
    with pytest.raises(ValueError, match='cmd: foo'):
        cmd.foo(h=False)


def test_cmd_exec(ok_repo):
    res = cmd.date()
    assert isinstance(res, str) and res

    res = cmd.python._(c=True)._("print('a')")()
    assert res.strip() == 'a'

    res = cmd.git.log(n=1)
    assert res.count('\n') >= 4
