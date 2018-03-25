#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import cmdlets, errlog
from polyvers._vendor.traitlets import traitlets as trt
from polyvers.logconfutils import init_logging
from tests.conftest import clearlog
import logging
import re

import pytest

import os.path as osp


init_logging(level=logging.DEBUG, logconf_files=[])

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


@pytest.fixture
def forceable():
    class Processor(cmdlets.Forceable, trt.HasTraits):
        pass

    return Processor()


def test_ErrLog(forceable):
    with pytest.raises(trt.TraitError, match='not Forceable'):
        errlog.ErrLog(object())

    erl = errlog.ErrLog(forceable)
    assert erl.token == erl.doing is None
    assert erl.exceptions == []

    erl = errlog.ErrLog(forceable, IOError, ValueError)
    assert erl.token is None
    assert erl.exceptions == [IOError, ValueError]
    erl2 = erl(token='water')
    assert erl2.token == 'water'
    assert erl.token is None
    assert erl.doing == erl2.doing is None
    assert erl.exceptions == erl2.exceptions == [IOError, ValueError]

    erl(doing='fine')

    erl = errlog.ErrLog(forceable, IOError, doing='fine')
    with erl(token='gg') as erl2:
        assert erl2 is not erl
        assert erl2.token == 'gg'
        assert erl.token is None
    with erl as erl2:
        assert erl2 is not erl  # NOT the same!
        assert erl2.token is None
    assert erl.token is None
    assert erl.doing == 'fine'
    assert erl.log_level is logging.WARNING

    ## TODO: check stacked erl messages


def test_ErrLog_non_forced_errors(caplog, forceable):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    erl = errlog.ErrLog(forceable, IOError, ValueError)

    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException,
                       match="Collected 1 error") as ex_info:
        with erl:
            raise IOError("Wrong!")
    assert len(erl._enforced_error_tuples) == 0
    assert re.search('DEBUG +Collecting delayed error', caplog.text)
    assert '"forced"' not in str(ex_info.value)
    assert 'delayed' in str(ex_info.value)

    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException,
                       match="Collected 1 error") as ex_info:
        with erl(doing='burning'):  # check default `token` value
            raise IOError("Wrong!")
    assert not erl._enforced_error_tuples
    assert 'while burning' in str(ex_info.value)


def test_ErrLog_mixed_errors(caplog, forceable):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    erl = errlog.ErrLog(forceable, IOError, ValueError)
    ## Mixed case still raises
    #
    clearlog(caplog)
    forceable.force = [True]
    with erl:
        erl2 = erl.stack('foo')
        with erl2:  # check default `token` value
            raise IOError("Wrong!")
        with erl2(token=True):
            raise IOError()
        assert len(erl._enforced_error_tuples) == 2
    assert len(erl._enforced_error_tuples) == 0

    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException) as ex_info:
        erl.report_errors()
    assert "Collected 2 error" in str(ex_info.value)

    clearlog(caplog)
    with erl(token=True):
        raise IOError()
    assert re.search('DEBUG +Collecting "forced" error', caplog.text)
    erl.report_errors(no_raise=True)
    assert re.search("WARNING +Bypassed 1 error", caplog.text)
    assert not erl._enforced_error_tuples

    ## Check raise_immediately
    #
    with erl(token=False, raise_immediately=True):
        with pytest.raises(IOError) as ex_info:
            raise IOError("STOP!")
    assert "Collected" not in str(ex_info.value)


def test_ErrLog_forced_errors(caplog, forceable):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    erl = errlog.ErrLog(forceable, Exception, token='kento')

    forceable.force = ['kento']
    with erl():
        raise Exception()
    forceable.force.append(True)
    with erl(doing='looting', token=True):
        raise Exception()
    assert len(erl._enforced_error_tuples) == 2
    assert re.search('DEBUG +Collecting "forced" error', caplog.text)

    clearlog(caplog)
    erl.report_errors()
    assert re.search(r'WARNING +Bypassed 2 error', caplog.text)
    assert 'while looting' in caplog.text
    assert not re.search("WARNING +Delayed ", caplog.text)
    assert not erl._enforced_error_tuples


def test_ErrLog_decorator(caplog):
    class C(cmdlets.Spec):
        @cmdlets.errlogged(Exception, token=True)
        def f_log(self):
            assert self.f_log.erl
            raise Exception

        @cmdlets.errlogged(ValueError)
        def f_raise(self):
            assert self.f_raise.erl
            raise ValueError

    C(force=[True]).f_log()
    assert "Collected 1 error" in caplog.text

    with pytest.raises(cmdlets.CmdException, match='Collected 1 error'):
        C().f_log()

    obj = C(force=[True])
    clearlog(caplog)
    obj.f_log()
    assert "Collected 1 error" in caplog.text

    with pytest.raises(cmdlets.CmdException, match='Collected 1 error'):
        obj.f_raise()
