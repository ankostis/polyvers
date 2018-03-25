#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import cmdlets, errlog
from polyvers._vendor.traitlets import traitlets as trt
from polyvers.errlog import _ErrNode, ErrLog
from tests.conftest import clearlog
import logging
import re

import pytest

import textwrap as tw


CollectedErrors = errlog.ErrLog.CollectedErrors


@pytest.fixture
def forceable():
    class Processor(cmdlets.Forceable, trt.HasTraits):
        pass

    return Processor()


@pytest.mark.parametrize('fields, exp', [
    ({}, 'ELN()'),
    ({'doing': '1'}, 'ELN(1, None, None, [])'),
    ({'is_forced': True}, 'ELN(None, True, None, [])'),
    ({'is_forced': False}, 'ELN(None, False, None, [])'),
    ({'err': ValueError()}, 'ELN(None, None, ValueError(), [])'),

    ({'doing': '1', 'is_forced': True, 'err': ValueError()},
     'ELN(1, True, ValueError(), [])'),

    ({'cnodes': [_ErrNode()]}, 'ELN(None, None, None, ...)'),

])
def test_ErrNode_str(fields, exp):
    node = _ErrNode(**fields)
    assert str(node).startswith(exp)
    assert repr(node).startswith(exp)


_err = ValueError()
_err2 = KeyError()


@pytest.mark.parametrize('fields, exp', [
    ({}, None),
    ({'doing': '1', 'is_forced': True}, None),

    ({'err': ValueError()}, "delayed: ValueError"),
    ({'err': ValueError('hi')}, "delayed: ValueError: hi"),
    ({'doing': 'rafting', 'err': _err}, "delayed while rafting: ValueError"),
    ({'is_forced': True, 'err': _err}, "ignored: ValueError"),
    ({'doing': 'rafting', 'is_forced': True, 'err': _err},
     "ignored while rafting: ValueError"),


    ({'err': _err, 'cnodes': [_ErrNode(err=_err2)]},
     tw.dedent("""\
        delayed: ValueError
          - delayed: KeyError""")),

    ({'err': _err, 'cnodes': [_ErrNode(err=_err2),
                              _ErrNode(),
                              _ErrNode(err=_err)]},
     tw.dedent("""\
        delayed: ValueError
          - delayed: KeyError
          - delayed: ValueError""")),

    ({'doing': 'parsing', 'err': _err, 'cnodes': [_ErrNode(err=_err2,
                                                           doing='opening')]},
     tw.dedent("""\
        delayed while parsing: ValueError
          - delayed while opening: KeyError""")),

    ({'err': _err, 'cnodes': [_ErrNode(err=_err2),
                              _ErrNode(cnodes=[_ErrNode(), _ErrNode()])]},  # ignore empty
     tw.dedent("""\
        delayed: ValueError
          - delayed: KeyError""")),

    ({'err': _err, 'cnodes': [_ErrNode(),
                              _ErrNode(err=_err2,
                                       cnodes=[_ErrNode(),
                                               _ErrNode(err=_err)])]},
     tw.dedent("""\
        delayed: ValueError
          - delayed: KeyError
            - delayed: ValueError""")),
])
def test_ErrNode_tree_text(fields, exp):
    node = _ErrNode(**fields)
    #print(node.tree_text())
    assert node.tree_text() == exp


def test_ErrLog_str(forceable):
    exp = r'ErrLog\(root=ELN\(\)@\w+, node=ELN\(\)@\w+, coords=\[\]\)'
    erl = ErrLog(forceable)
    assert re.search(exp, str(erl))
    assert re.search(exp, repr(erl))

    exp = r"""(?x)
        ErrLog\(root=ELN\(,\ False,\ None,\ ...\)@\w+,
        \ node=ELN\(,\ False,\ None,\ ...\)@\w+,
        \ coords=\[\]\)@\w+\)
        """
    with erl(token='golf'):
        assert re.search(exp, str(erl))
        assert re.search(exp, repr(erl))


def test_ErrLog_properties(forceable):
    with pytest.raises(trt.TraitError, match='not Forceable'):
        ErrLog(object())

    erl = ErrLog(forceable)
    assert erl.token is erl.doing is None
    assert erl.exceptions == []
    assert erl.is_root and not erl.is_armed

    erl = ErrLog(forceable, IOError, ValueError)
    assert erl.token is erl.doing is None
    assert erl.exceptions == [IOError, ValueError]
    assert erl.is_root and not erl.is_armed

    erl2 = erl(token='water')
    assert erl2.token == 'water'
    assert erl.token is None
    assert erl.doing is erl2.doing is None
    assert erl.exceptions == erl2.exceptions == [IOError, ValueError]
    assert erl.is_root and not erl.is_armed

    erl = ErrLog(forceable)
    with erl() as erl2:
        assert erl2 is not erl
        assert erl.is_root and erl.is_armed
        assert erl2.token is erl.token is None
        assert erl2.doing is erl.doing is None


def test_ErrLog_no_errors(caplog, forceable):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    erl = ErrLog(forceable, ValueError, ValueError)

    clearlog(caplog)
    with erl:
        pass
    assert not caplog.text
    assert erl.is_good
    assert not erl.is_armed

    ## Check re-use clean errlogs.
    #
    clearlog(caplog)
    with erl:
        pass
    assert not caplog.text
    assert not erl.is_armed
    assert erl.is_good


def test_ErrLog_root(forceable, caplog):
    with pytest.raises(CollectedErrors, match="Collected 1 errors:"):
        with ErrLog(forceable, ValueError):
            raise ValueError()
    assert re.search('DEBUG +Collecting delayed', caplog.text)

    forceable.force.append(True)
    with ErrLog(forceable, ValueError, token=True):
        raise ValueError()
    assert "Ignored 1 errors:" in caplog.text
    assert re.search('DEBUG +Collecting ignored', caplog.text)

    clearlog(caplog)
    with pytest.raises(KeyError, match="bad key"):
        with ErrLog(forceable, ValueError):
            raise KeyError('bad key')
    assert not caplog.text


def test_ErrLog_nested(caplog, forceable):
    erl = ErrLog(forceable, ValueError, KeyError)

    clearlog(caplog)
    with pytest.raises(ErrLog.CollectedErrors) as ex_info:
        with erl(doing="burning"):
            with erl(doing="looting"):
                raise ValueError("Wrong!")
    exp = tw.dedent("""\
        delayed while parsing: ValueError
          - delayed while opening: KeyError""")
    assert ex_info.value == exp


def test_ErrLog_decorator(caplog):
    class C(cmdlets.Spec):
        @errlog.errlogged(Exception, token=True)
        def f_log(self):
            assert self.f_log.errlog
            raise Exception

        @errlog.errlogged(ValueError)
        def f_raise(self):
            assert self.f_raise.errlog
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
