#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.oscmd import cmd

import pytest


def test_cmd(ok_repo):
    ok_repo.chdir()

    cmdlist = cmd.python._(c=True)._("print('a')")._cmdlist
    assert cmdlist == "python -c print('a')".split()

    res = cmd.date()
    assert isinstance(res, str) and res

    res = cmd.python._(c=True)._("print('a')")()
    assert res.strip() == 'a'

    res = cmd.git.log(n=1)
    assert res.count('\n') >= 4


def test_negate_single_letter():
    with pytest.raises(ValueError, match='cmd: foo'):
        cmd.foo(h=False)
