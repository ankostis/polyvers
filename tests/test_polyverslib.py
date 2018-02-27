#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
from polyvers import polyverslib as pvlib
import re

import pytest

import subprocess as sbp


proj1 = 'proj1'
proj2 = 'proj-2'


def rfc2822_today():
    ## TCs may fail if run when day changes :-)
    return pvlib.rfc2822_now()[:12]  # till hour


##############
## DESCRIBE ##
##############

def test_describe_project_p1(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    v = pvlib.describe_project(proj1,)
    assert v.startswith('proj1-v0.0.1')
    v = pvlib.describe_project(proj1, default='<unused>')
    assert v.startswith('proj1-v0.0.1')
    v, d = pvlib.describe_project(proj1, tag_date=True)
    assert v.startswith('proj1-v0.0.1') and d.startswith(rfc2822_today())
    v, d = pvlib.describe_project(proj1, default='<unused>', tag_date=True)
    assert v.startswith('proj1-v0.0.1') and d.startswith(rfc2822_today())

    untagged_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project('foo')
    v = pvlib.describe_project('foo', default='<unused>')
    assert v == '<unused>'
    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project('foo', tag_date=True)
    v, d = pvlib.describe_project('foo', default=(1, 2), tag_date=True)
    assert v == (1, 2) and d.startswith(rfc2822_today())

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project(proj1)
    v = pvlib.describe_project(proj1, default='<unused>')
    assert v == '<unused>' and d.startswith(rfc2822_today())

    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project('foo', tag_date=True)
    v, d = pvlib.describe_project('foo', default='123', tag_date=True)
    assert v == '123' and d.startswith(rfc2822_today())


def test_describe_project_p2(ok_repo):
    ok_repo.chdir()

    v = pvlib.describe_project(proj2)
    assert v.startswith('proj-2-v0.2.1')
    v, d = pvlib.describe_project(proj2, tag_date=True)
    assert d.startswith(rfc2822_today())


def test_describe_project_BAD(ok_repo, untagged_repo, no_repo):
    ok_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project('foo')
    v = pvlib.describe_project('foo', default='<unused>')
    assert v == '<unused>'
    with pytest.raises(sbp.CalledProcessError):
        pvlib.describe_project('foo', tag_date=True)
    v, d = pvlib.describe_project('foo', default='a', tag_date=True)
    assert v == 'a' and d.startswith(rfc2822_today())


##############
##   MAIN   ##
##############

def test_MAIN_describe_projects(ok_repo, untagged_repo, no_repo,
                                capsys):
    ok_repo.chdir()

    pvlib.main()
    out, err = capsys.readouterr()
    assert not out and not err

    pvlib.main(proj1)
    out, err = capsys.readouterr()
    assert out.startswith('proj1-v0.0.1') and not err
    pvlib.main(proj2)
    out, err = capsys.readouterr()
    assert out.startswith('proj-2-v0.2.1')
    #assert not caplog.text()

    pvlib.main(proj1, proj2, 'foo')
    out, err = capsys.readouterr()
    assert re.match(
        r'proj1: proj1-v0.0.1-2-\w+\nproj-2: proj-2-v0.2.1\nfoo: ', out)
    #assert 'No names found' in caplog.text()

    untagged_repo.chdir()

    pvlib.main()
    out, err = capsys.readouterr()
    assert not out and not err
    with pytest.raises(sbp.CalledProcessError):
        pvlib.main('foo')
    pvlib.main('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n'
    #assert 'No names found' in caplog.text()

    no_repo.chdir()

    with pytest.raises(sbp.CalledProcessError):
        pvlib.main(proj1)
    pvlib.main('foo', 'bar')
    out, err = capsys.readouterr()
    assert out == 'foo: \nbar: \n'
    #assert caplog.records()
