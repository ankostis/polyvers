#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.oscmd import cmd, _Cli, PopenCmd

import pytest


def test_Cli_building(ok_repo):
    ok_repo.chdir()

    c = _Cli({}, 'foo')._(c=True).Bang_bar._("any_thing'", flag_dang='hi there', no=False)
    cmdlist = c._cmdlist
    assert cmdlist == ['foo', '-c', 'Bang-bar', "any_thing'",
                       '--flag-dang', 'hi there', '--no-no']

    assert _Cli({}, 'cmd')._(*'abc', J=3, K='3')._cmdlist == 'cmd a b c -J 3 -K 3'.split()

    assert cmd.cmd._(null='', f='', none=None).top._cmdlist == [
        'cmd', '--null', '', '-f', '', 'top']


def test_Cli_to_str():
    assert str(_Cli({}, 'cmd')._(flag=True, null='', f='').top) == \
        "Cli(cmd --flag --null '' -f '' top)"


def test_Cmd_negate_single_letter():
    with pytest.raises(ValueError, match='cmd: foo'):
        cmd.foo(h=False)


def test_Cmd_no_stdout():
    assert PopenCmd(check_stdout=False).git.log(n=1) is None


def test_cmd_exec(ok_repo):
    res = cmd.date()
    assert isinstance(res, str) and res

    res = cmd.python._(c=True)._("print('a')")()
    assert res == 'a'

    res = cmd.git.log(n=1)
    assert res.count('\n') >= 4
