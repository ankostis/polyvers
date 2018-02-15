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
from .conftest import touchpaths
import pytest
from py.path import local as P  # @UnresolvedImport

import os.path as osp


init_logging(level=logging.DEBUG, logconf_files=[])

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


def mix_dics(d1, d2):
    d = d1.copy()
    d.update(d2)
    return d


def test_CfgFilesRegistry_consolidate_posix_1():
    visited = [
        ('/d/foo/bar/.appname', None),
        ('/d/foo/bar/.appname', 'appname_config.py'),
        ('/d/foo/bar/.appname', 'appname_config.json'),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
    ]
    c = cmdutils.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('/d/foo/bar/.appname', ['appname_config.py', 'appname_config.json']),
        ('/d/foo\Bar/dooba/doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp, visited


def test_CfgFilesRegistry_consolidate_posix_2():
    visited = [
        ('/c/Big/BEAR/.appname', 'appname_persist.json'),
        ('/c/Big/BEAR/.appname', 'appname_config.py'),
        ('/c/Big/BEAR/.appname', None),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
        ('/d/foo\Bar/dooba/doo', None),
    ]
    c = cmdutils.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('/c/Big/BEAR/.appname', ['appname_persist.json', 'appname_config.py']),
        ('/d/foo\Bar/dooba/doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp, visited


def test_CfgFilesRegistry_consolidate_win_1():
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
    #print('FF\n', cons)
    assert cons == exp, visited


def test_CfgFilesRegistry_consolidate_win_2():
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


def test_CfgFilesRegistry(tmpdir):
    tdir = tmpdir.mkdir('cfgregistry')
    tdir.chdir()
    paths = """
    ## loaded
    #
    conf.py
    conf.json
    conf.d/a.json
    conf.d/a.py

    ## ignored
    #
    conf
    conf.bad
    conf.d/conf.bad
    conf.d/bad
    conf.py.d/a.json
    conf.json.d/a.json
    """
    touchpaths(tdir, paths)

    cfr = cmdutils.CfgFilesRegistry()
    fpaths = cfr.collect_fpaths(['conf'])
    fpaths = [P(p).relto(tdir).replace('\\', '/') for p in fpaths]
    assert (fpaths ==
            'conf.json conf.py conf.d/a.json conf.d/a.py'.split()), fpaths

    cfr = cmdutils.CfgFilesRegistry()
    fpaths = cfr.collect_fpaths(['conf.py'])
    fpaths = [P(p).relto(tdir).replace('\\', '/') for p in fpaths]
    assert (fpaths ==
            'conf.py conf.py.d/a.json conf.d/a.json conf.d/a.py'.split()), fpaths


def test_no_default_config_paths():
    cmd = cmdutils.Cmd()
    cmd.initialize([])
    print(cmd._cfgfiles_registry.config_tuples)
    assert len(cmd.loaded_config_files) == 0


def test_default_loaded_paths():
    with tempfile.TemporaryDirectory(prefix=__name__) as tdir:
        class MyCmd(cmdutils.Cmd):
            ""
            @trt.default('config_paths')
            def _config_paths(self):
                return [tdir]

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
    (['c'], None, ['c.json', 'c.py']),

    (['c.json', 'c.py'], None, ['c.json', 'c.py']),
    (['c.json;c.py'], None, ['c.json', 'c.py']),

    (['c', 'c.json;c.py'], None, ['c.json', 'c.py']),
    (['c;c.json', 'c.py'], None, ['c.json', 'c.py']),

    (['a', 'b'], None, ['a.py', 'b.json']),
    (['b', 'a'], None, ['b.json', 'a.py']),
    (['c'], None, ['c.json', 'c.py']),
    (['a', 'c'], None, ['a.py', 'c.json', 'c.py']),
    (['a', 'c'], None, ['a.py', 'c.json', 'c.py']),
    (['a;c'], None, ['a.py', 'c.json', 'c.py']),
    (['a;b', 'c'], None, ['a.py', 'b.json', 'c.json', 'c.py']),

    ('b', 'a', ['b.json']),
]


@pytest.mark.parametrize('param, var, exp', test_paths)
def test_collect_static_fpaths(param, var, exp, tmpdir):
    tdir = tmpdir.mkdir('collect_paths')

    touchpaths(tdir, """
        a.py
        b.json
        c.py
        c.json
    """)

    try:
        cmd = cmdutils.Cmd()
        if param is not None:
            cmd.config_paths = [str(tdir / ff)
                                for f in param
                                for ff in f.split(os.pathsep)]
        if var is not None:
            os.environ['POLYVERS_CONFIG_PATHS'] = os.pathsep.join(
                osp.join(tdir, ff)
                for f in var
                for ff in f.split(os.pathsep))

        paths = cmd._collect_static_fpaths()
        paths = [P(p).relto(tdir).replace('\\', '/') for p in paths]
        assert paths == exp, (param, var, exp)
    finally:
        try:
            del os.environ['POLYVERS_CONFIG_PATHS']
        except Exception as _:
            pass
