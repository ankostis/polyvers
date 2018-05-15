#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers._vendor.traitlets import traitlets as trt
from polyvers.cmdlet import cmdlets, errlog
from polyvers.cmdlet.errlog import _ErrNode, ErrLog, CollectedErrors
from tests.conftest import check_text
import logging
import re

import pytest

import textwrap as tw


ErrLogException = errlog.ErrLog.ErrLogException


@pytest.fixture
def forceable():
    class Processor(cmdlets.Forceable, trt.HasTraits):
        pass

    return Processor()


@pytest.fixture
def logcollector():
    logs = []

    def log_collector(msg, *args, **_kwd):
        logs.append(msg % args)

    log_collector.logs = logs

    return log_collector


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
    ({'doing': '1', 'is_forced': True, 'token': 'abc'}, None),

    ({'err': ValueError()}, "while ??:\n  delayed: ValueError"),
    ({'err': ValueError('hi'), 'doing': "zing"},
     "while zing:\n  delayed: ValueError: hi"),
    ({'doing': 'rafting', 'err': _err}, "while rafting:\n  delayed: ValueError"),
    ({'is_forced': True, 'err': _err}, "while ??:\n  ignored: ValueError"),
    ({'token': True, 'err': _err}, "while ??:\n  delayed (--force=True): ValueError"),
    ({'is_forced': True, 'token': 'abc', 'err': _err},
     "while ??:\n  ignored (--force=abc): ValueError"),
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
        ErrLog<rot=ELN<\[ELN<NF,\ 'golf'>@\w{5}\]>@\w{5},
        \ anc=ELN<\+>@\w{5},
        \ crd=,
        \ act=None>@\w{5}
    """
    exp2 = r"""(?x)
        ErrLog<rot=ELN<\[ELN<NF,\ 'golf'>@\w{5}\]>@\w{5},
        \ anc=ELN<NF,\ 'golf'>@\w{5},
        \ crd=0,
        \ act=None>@\w{5}
    """
    with erl(token='golf') as erl2:
        assert re.search(exp1, str(erl))
        assert re.search(exp1, repr(erl))

        assert re.search(exp2, str(erl2))
        assert re.search(exp2, repr(erl2))


def test_ErrLog_properties(forceable, logcollector):
    with pytest.raises(ValueError, match='not Forceable'):
        ErrLog(object())

    erl = ErrLog(forceable)
    assert erl.token is erl.doing is None
    assert erl.exceptions == [Exception]
    assert erl.is_root and not erl.is_armed

    erl = ErrLog(forceable, OSError, ValueError, info_log=logcollector)
    assert erl.token is erl.doing is None
    assert erl.exceptions == [OSError, ValueError]
    assert erl.is_root and not erl.is_armed

    erl2 = erl(token='water', doing='something')
    assert erl.exceptions == [OSError, ValueError]
    assert erl2.exceptions == [Exception]
    assert erl2.token == 'water'
    assert erl2.doing == 'something'
    assert erl.doing is erl.doing is None
    assert erl.is_root and not erl.is_armed
    assert erl.info_log is erl2.info_log is logcollector

    erl3 = erl2()
    assert erl3.token is erl3.doing is None
    assert erl3.exceptions == [Exception]

    assert erl3(token=True)().token is True
    erl = ErrLog(forceable, ValueError)
    with erl as erl2:
        assert erl2 is not erl
        assert erl.is_root and erl.is_armed
        assert erl().is_armed
        assert not erl2.is_root and not erl2.is_armed
        assert erl.exceptions == erl2.exceptions == [ValueError]
        assert erl2.token is erl.token is None
        assert erl2.doing is erl.doing is None


def test_ErrLog_no_errors(caplog, forceable, logcollector):
    level = logging.DEBUG
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)

    erl = ErrLog(forceable, ValueError, ValueError)

    caplog.clear()
    with erl:
        pass
    assert not caplog.text
    assert erl.is_good
    assert not erl.is_armed

    ## Check re-use clean errlogs.
    #
    caplog.clear()
    with erl(doing='0', info_log=logcollector) as erl2:
        with erl2(doing='01'):
            pass
        with erl2(doing='02') as erl3:
            with erl3(doing='021') as erl4:
                with erl4(doing='0211'):
                    pass
        with erl2(doing='03') as erl3:
            pass
    assert not caplog.text
    assert not erl.is_armed
    assert erl.is_good
    info_text = '\n'.join(logcollector.logs)
    exp_info = tw.dedent("""\
        2.1. Finished 01.
        2.2.1.1. Finished 0211.
        2.2.1. Finished 021 (1 subtasks).
        2.2. Finished 02 (1 subtasks).
        2.3. Finished 03.
        2. Finished 0 (3 subtasks).""")
    assert exp_info in info_text

    logcollector.logs.clear()
    with erl(doing='redoing', info_log=logcollector):
        pass
    info_text = '\n'.join(logcollector.logs)
    assert "3. Finished redoing." in info_text


def test_ErrLog_root(forceable, caplog, logcollector):
    with pytest.raises(CollectedErrors, match="Collected 1 errors while"):
        with ErrLog(forceable, ValueError):
            raise ValueError()
    assert re.search('DEBUG +Collecting ValueError', caplog.text)

    logcollector.logs.clear()
    forceable.force.append(True)
    with ErrLog(forceable, ValueError, token=True, warn_log=logcollector):
        raise ValueError()
    text = '\n'.join(logcollector.logs)
    assert "Ignored 1 errors while" in text
    assert re.search('DEBUG +Collecting ValueError', caplog.text)

    erl = ErrLog(forceable, ValueError, warn_log=logcollector)
    logcollector.logs.clear()
    with pytest.raises(KeyError, match="bad key"):
        with erl:
            raise KeyError('bad key')
    assert not logcollector.logs

    ## test re-using failed one.
    #
    with erl:
        pass


def test_ErrLog_nested_all_captured_and_info(caplog, logcollector, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, info_log=logcollector)

    caplog.clear()
    with erl(doing="starting") as erl2:
        with erl2(doing="notting"):
            pass

        with erl2(doing="doing-1", token=True):
            raise ValueError("Wrong-1!")

        with erl2(doing="doing-2", token=True) as erl3:
            with erl3(AssertionError, doing="do-doing", token=True):
                raise AssertionError("Good-do-do")
            raise ValueError("better-2")

    exp_warn = tw.dedent("""\
        Ignored 3 errors while starting:
          - while doing-1:
            ignored (--force=True): ValueError: Wrong-1!
          - while doing-2:
            - while do-doing:
              ignored (--force=True): AssertionError: Good-do-do
            ignored (--force=True): ValueError: better-2""")
    #print(caplog.text)
    assert exp_warn in caplog.text

    exp_info = tw.dedent("""\
        1.1. Finished notting.
        1. Finished starting (3 subtasks, 2 errors ignored).""")
    text = '\n'.join(logcollector.logs)
    assert exp_info in text


def test_ErrLog_nested_reuse(caplog, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, token=True)

    with pytest.raises(ValueError):
        with erl(KeyError):
            raise ValueError()

    caplog.clear()
    with erl(ValueError, doing="starting"):
        raise ValueError("HiHi")
    assert "HiHi" in caplog.text


def test_ErrLog_nested_warn_while_raising(caplog, forceable):
    forceable.force.append(True)
    erl = ErrLog(forceable, ValueError, token=True)
    ## Re-use non-failed errlog, and fail it.
    #
    caplog.clear()
    with pytest.raises(KeyError):
        with erl(ValueError, doing="starting") as erl2:
            with erl2(ValueError, doing="doing-1"):
                raise ValueError("Wrong-1!")

            with erl2(ValueError, doing="doing-3"):
                raise KeyError("Wrong-3")
    exp = tw.dedent("""\
        Ignored 1 errors while starting:
          - while doing-1:
            ignored (--force=True): ValueError: Wrong-1!
    """)
    assert exp in caplog.text


def test_ErrLog_nested_forced(forceable, caplog):
    forceable.force.extend([True, 'abc'])  # `True` must do nothing.
    erl = ErrLog(forceable)
    with pytest.raises(CollectedErrors) as exinfo:
        with erl(ValueError, KeyError, doing="starting", token='abc') as erl2:
            with erl2(ValueError, doing="doing-1", token='abc'):
                raise ValueError("Wrong-1!")

            with erl2(KeyError):
                raise KeyError()

            with erl2(KeyError,
                      doing="doing-2",
                      token='BAD',
                      raise_immediately=True):
                raise KeyError("Wrong-2")

            pytest.fail("Should have raised immediately, above.")

    exp = tw.dedent("""\
        Collected 4 errors (2 ignored) while starting:
          - while doing-1:
            ignored (--force=abc): ValueError: Wrong-1!
          - while ??:
            delayed: KeyError
          - while doing-2:
            delayed (--force=BAD): KeyError: 'Wrong-2'
          ignored (--force=abc): KeyError: 'Wrong-2'""")
    #print(exinfo.value)
    check_text(str(exinfo.value), exp)


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

    caplog.clear()
    with pytest.raises(cmdlets.CmdException, match='Collected 1 error'):
        C().f_log()

    obj = C(force=[True])
    caplog.clear()
    obj.f_log()
    assert "Ignored 1 error" in caplog.text

    with pytest.raises(ValueError):
        obj.f_raise()
