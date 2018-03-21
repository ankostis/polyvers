#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import cmdlets, errlog
from polyvers._vendor.traitlets import traitlets as trt
from tests.conftest import clearlog
import logging
import re

import pytest


log = logging.getLogger(__name__)


@pytest.fixture
def forceable():
    class Processor(cmdlets.Forceable, trt.HasTraits):
        pass

    return Processor()


def test_ErrLog(forceable):
    erl = errlog.ErrLog(forceable, IOError, ValueError, doing='fire')
    #TODO assert not erl._build_error_message()

    with erl(token='gg') as erl2:
        assert erl2.token == 'gg'
        assert erl.token is None
    assert erl.token is None
    assert erl.log_level is logging.WARNING

    ## TODO: check stacked erl messages


def test_ErrLog_non_forced_errors(caplog, forceable):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    clearlog(caplog)

    erl = errlog.ErrLog(forceable, IOError, ValueError)
    with erl:
        raise IOError("Wrong!")
    assert len(erl._enforced_error_tuples) == 1
    with erl(doing='burning'):  # check default `token` value
        raise IOError("Wrong!")
    assert len(erl._enforced_error_tuples) == 2
    assert re.search('DEBUG +Collecting delayed error', caplog.text)

    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException,
                       match="Collected 2 error") as ex_info:
        erl.report_errors()
    assert '"forced"' not in str(ex_info.value)
    assert 'while burning' in str(ex_info.value)
    assert not erl._enforced_error_tuples

    ## Mixed case still raises
    #
    clearlog(caplog)
    forceable.force = [True]
    with erl():  # check default `token` value
        raise IOError("Wrong!")
    with erl(token=True):
        raise IOError()
    assert len(erl._enforced_error_tuples) == 2

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
