#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers.oscmd import oscmd


def test_cmd():
    cmdlist = oscmd.python._(c=True)._("print('a')").cmdlist
    assert cmdlist == "python -c print('a')".split()

    res = oscmd.date()
    assert isinstance(res, str) and res

    res = oscmd.python._(c=True)._("print('a')")()
    assert res.strip() == 'a'
