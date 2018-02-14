#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

import io
import logging
import os
from polyvers import cmdutils
from polyvers._vendor import traitlets as trt
from polyvers.logconfutils import init_logging
import tempfile

import pytest

import os.path as osp


init_logging(level=logging.DEBUG, logconf_files=[])

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


def mix_dics(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d


def test_consolidate_1():
    visited = [
        ('D:\\foo\\bar\\.appname', None),
        ('D:\\foo\\bar\\.appname', 'appname_config.py'),
        ('D:\\foo\\bar\\.appname', 'appname_config.json'),
        ('d:\\foo\Bar\\dooba\\doo', None),
        ('d:\\foo\Bar\\dooba\\doo', None),
        ('d:\\foo\Bar\\dooba\\doo', None),
        ('d:\\foo\Bar\\dooba\\doo', None),
    ]
    c = cmdutils.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('D:\\foo\\bar\\.appname', ['appname_config.py', 'appname_config.json']),
        ('d:\\foo\Bar\\dooba\\doo', []),
    ]
    print('FF\n', cons)
    assert cons == exp, visited


def test_consolidate_2():
    visited = [
        ('C:\\Big\\BEAR\\.appname', 'appname_persist.json'),
        ('C:\\Big\\BEAR\\.appname', 'appname_config.py'),
        ('C:\\Big\\BEAR\\.appname', None),
        ('D:\\foo\Bar\\dooba\\doo', None),
        ('D:\\foo\Bar\\dooba\\doo', None),
        ('D:\\foo\Bar\\dooba\\doo', None),
        ('D:\\foo\Bar\\dooba\\doo', None),
    ]
    c = cmdutils.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('C:\\Big\\BEAR\\.appname', ['appname_persist.json', 'appname_config.py']),
        ('D:\\foo\Bar\\dooba\\doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp, visited


def test_no_default_config_paths():
    cmd = cmdutils.Cmd()
    cmd.initialize([])
    print(cmd._cfgfiles_registry.config_tuples)
    assert len(cmd.loaded_config_files) == 0


def test_default_loaded_paths():
    basename = 'foo'

    with tempfile.TemporaryDirectory(prefix=__name__) as tdir:
        class MyCmd(cmdutils.Cmd):
            ""
            @trt.default('config_basename')
            def _config_basename(self):
                return basename

            @trt.default('config_paths')
            def _config_fpaths(self):
                return [tdir]

        f = osp.join(tdir, '%s.py' % basename)
        io.open(f, 'w').close()

        cmd = MyCmd()
        cmd.initialize([])
        print(cmd._cfgfiles_registry.config_tuples)
        assert len(cmd.loaded_config_files) == 1


test_paths = [
    (None, None, []),
    (['cc', 'cc.json'], None, []),


    ## Because of ext-stripping.
    (['b.py', 'a.json'], None, ['b.json', 'a.py']),
    (['c.json'], None, ['c.json']),

    ([''], None, []),
    (None, 'a', []),
    (None, 'a;', []),

    (['a'], None, ['a.py']),
    (['b'], None, ['b.json']),
    (['c'], None, ['c.py', 'c.json']),

    (['c.json', 'c.py'], None, ['c.json', 'c.py']),
    (['c.json;c.py'], None, ['c.json', 'c.py']),

    (['c', 'c.json;c.py'], None, ['c.py', 'c.json']),
    (['c;c.json', 'c.py'], None, ['c.py', 'c.json']),

    (['a', 'b'], None, ['a.py', 'b.json']),
    (['b', 'a'], None, ['b.json', 'a.py']),
    (['c'], None, ['c.py', 'c.json']),
    (['a', 'c'], None, ['a.py', 'c.py', 'c.json']),
    (['a', 'c'], None, ['a.py', 'c.py', 'c.json']),
    (['a;c'], None, ['a.py', 'c.py', 'c.json']),
    (['a;b', 'c'], None, ['a.py', 'b.json', 'c.py', 'c.json']),

    ('b', 'a', ['b.json']),
]


@pytest.mark.parametrize('param, var, exp', test_paths)
def test_collect_static_fpaths(param, var, exp):
    basename = 'c'

    with tempfile.TemporaryDirectory(prefix=__name__) as tdir:
        class MyCmd(cmdutils.Cmd):
            ""
            @trt.default('config_basename')
            def _config_basename(self):
                return basename

            @trt.default('config_paths')
            def _config_fpaths(self):
                return [tdir]

        for f in ('a.py', 'b.json', 'c.py', 'c.json'):
            io.open(osp.join(tdir, f), 'w').close()

        try:
            exp = [osp.join(tdir, f) for f in exp]

            cmd = cmdutils.Cmd()
            if param is not None:
                cmd.config_paths = [osp.join(tdir, ff)
                                    for f in param
                                    for ff in f.split(os.pathsep)]
            if var is not None:
                os.environ['POLYVERS_CONFIG_PATHS'] = os.pathsep.join(
                    osp.join(tdir, ff)
                    for f in var
                    for ff in f.split(os.pathsep))

            paths = cmd._collect_static_fpaths()
            assert paths == exp, (param, var, exp)
        finally:
            try:
                del os.environ['POLYVERS_CONFIG_PATHS']
            except:
                pass
