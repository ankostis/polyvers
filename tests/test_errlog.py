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
ErrLogException = errlog.ErrLog.ErrLogException


@pytest.fixture
def forceable():
    class Processor(cmdlets.Forceable, trt.HasTraits):
        pass

    return Processor()


@pytest.mark.parametrize('fields, exp_str, exp_repr', [
    ({}, 'ELN', None),
    ({'doing': '1'}, "ELN<'1'>", None),
    ({'is_forced': True}, 'ELN<F>', None),
    ({'is_forced': False}, 'ELN<NF>', None),
    ({'err': ValueError()}, 'ELN<ValueError()>', None),

    ({'doing': 'well', 'is_forced': True, 'err': ValueError()},
     "ELN<'well', F, ValueError()>", None),

    ({'cnodes': [_ErrNode()]}, 'ELN<+>', 'ELN<[ELN'),
])
def test_ErrNode_str(fields, exp_str, exp_repr):
    node = _ErrNode(**fields)
    assert str(node).startswith(exp_str)
    assert repr(node).startswith(exp_repr or exp_str)


_err = ValueError()
_err2 = KeyError()


@pytest.mark.parametrize('fields, exp', [
    ({}, None),
    ({'doing': '1', 'is_forced': True}, None),

    ({'err': ValueError()}, "while ??:\n  delayed: ValueError"),
    ({'err': ValueError('hi'), 'doing': "zing"},
     "while zing:\n  delayed: ValueError: hi"),
    ({'doing': 'rafting', 'err': _err}, "while rafting:\n  delayed: ValueError"),
    ({'is_forced': True, 'err': _err}, "while ??:\n  ignored: ValueError"),
    ({'doing': 'rafting', 'is_forced': True, 'err': _err},
     "while rafting:\n  ignored: ValueError"),


    ({'err': _err, 'cnodes': [_ErrNode(err=_err2)]},
     tw.dedent("""\
        while ??:
          - while ??:
            delayed: KeyError
          delayed: ValueError""")),

    ({'err': _err, 'cnodes': [_ErrNode(err=_err2, doing='sing'),
                              _ErrNode(doing='jjj'),
                              _ErrNode(err=_err)]},
     tw.dedent("""\
        while ??:
          - while sing:
            delayed: KeyError
          - while ??:
            delayed: ValueError
          delayed: ValueError""")),

    ({'doing': 'parsing', 'err': _err, 'cnodes': [_ErrNode(err=_err2,
                                                           doing='opening')]},
     tw.dedent("""\
        while parsing:
          - while opening:
            delayed: KeyError
          delayed: ValueError""")),

    ({'err': _err, 'cnodes': [_ErrNode(err=_err2),
                              _ErrNode(cnodes=[_ErrNode(), _ErrNode()])]},  # ignore empty
     tw.dedent("""\
        while ??:
          - while ??:
            delayed: KeyError
          delayed: ValueError""")),

    ({'err': _err, 'cnodes': [_ErrNode(),
                              _ErrNode(err=_err2,
                                       cnodes=[_ErrNode(),
                                               _ErrNode(err=_err)])]},
     tw.dedent("""\
        while ??:
          - while ??:
            - while ??:
              delayed: ValueError
            delayed: KeyError
          delayed: ValueError""")),
])
def test_ErrNode_tree_text(fields, exp):
    node = _ErrNode(**fields)
    #print(node.tree_text())
    assert node.tree_text() == exp


def test_ErrLog_str(forceable):
    exp = r'ErrLog<rot=ELN@\w{5}, anc=ELN@\w{5}, crd=, act=None>'
    erl = ErrLog(forceable)
    assert re.search(exp, str(erl))
    assert re.search(exp, repr(erl))

    exp1 = r"""(?x)
        ErrLog<rot=ELN<\[ELN<NF>@\w{5}\]>@\w{5},
        \ anc=ELN<\+>@\w{5},
        \ crd=,
        \ act=None>@\w{5}
    """
    exp2 = r"""(?x)
        ErrLog<rot=ELN<\[ELN<NF>@\w{5}\]>@\w{5},
        \ anc=ELN<NF>@\w{5},
        \ crd=0,
        \ act=None>@\w{5}
    """
    with erl(token='golf') as erl2:
        assert re.search(exp1, str(erl))
        assert re.search(exp1, repr(erl))

        assert re.search(exp2, str(erl2))
        assert re.search(exp2, repr(erl2))


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
    with erl as erl2:
        assert erl2 is not erl
        assert erl.is_root and erl.is_armed
        assert erl().is_armed
        assert not erl2.is_root and not erl2.is_armed
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
    with pytest.raises(CollectedErrors, match="Collected 1 errors while"):
        with ErrLog(forceable, ValueError):
            raise ValueError()
    assert re.search('DEBUG +Collecting ValueError', caplog.text)

    clearlog(caplog)
    forceable.force.append(True)
    with ErrLog(forceable, ValueError, token=True):
        raise ValueError()
    assert "Ignored 1 errors while" in caplog.text
    assert re.search('DEBUG +Collecting ValueError', caplog.text)

    clearlog(caplog)
    with pytest.raises(KeyError, match="bad key"):
        with ErrLog(forceable, ValueError):
            raise KeyError('bad key')
    assert not caplog.text


def test_ErrLog_nested_all_captured(caplog, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, ValueError, token=True)

    clearlog(caplog)
    with erl(doing="starting") as erl2:
        with erl2(doing="notting"):
            pass

        with erl2(doing="doing-1"):
            raise ValueError("Wrong-1!")

        with erl2(doing="doing-2") as erl3:
            with erl3(doing="do-doing"):
                raise ValueError("Good-do-do")
            raise ValueError("better-2")

    exp = tw.dedent("""\
        Ignored 3 errors while starting:
          - while doing-1:
            ignored: ValueError: Wrong-1!
          - while doing-2:
            - while do-doing:
              ignored: ValueError: Good-do-do
            ignored: ValueError: better-2""")
    #print(caplog.text)
    assert exp in caplog.text


def test_ErrLog_nested_reuse(caplog, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, token=True)

    with pytest.raises(ValueError):
        with erl:
            raise ValueError()

    clearlog(caplog)
    with erl(ValueError, doing="starting"):
        raise ValueError("HiHi")
    assert "HiHi" in caplog.text


def test_ErrLog_nested_complex_msg(caplog, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, ValueError, token=True)
    ## Re-use non-failed errlog, and fail it.
    #
    clearlog(caplog)
    with pytest.raises(KeyError):
        with erl(doing="starting") as erl2:
            with erl2(doing="doing-1"):
                raise ValueError("Wrong-1!")

            with erl2(doing="doing-3"):
                raise KeyError("Wrong-3")
    exp = tw.dedent("""\
        Ignored 1 errors while starting:
          - while doing-1:
            ignored: ValueError: Wrong-1!
    """)
    assert exp in caplog.text


def test_ErrLog_decorator(caplog):
    class C(cmdlets.Spec):
        @errlog.errlogged(KeyError, token=True)
        def f_log(self):
            assert self.f_log.errlog  # installed by decorator
            raise KeyError()

        @errlog.errlogged(KeyError)
        def f_raise(self):
            assert self.f_raise.errlog  # installed by decorator
            raise ValueError()

    C(force=[True]).f_log()
    assert "Collecting KeyError" in caplog.text
    assert "Ignored 1 errors while ??" in caplog.text

    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException, match='Collected 1 error'):
        C().f_log()

    obj = C(force=[True])
    clearlog(caplog)
    obj.f_log()
    assert "Ignored 1 error" in caplog.text

    with pytest.raises(ValueError):
        obj.f_raise()
