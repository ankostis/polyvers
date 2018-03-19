#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from os import pathsep as PS
from polyvers import cmdlets
from polyvers._vendor.traitlets import config as trc
from polyvers._vendor.traitlets import traitlets as trt
from polyvers._vendor.traitlets.traitlets import Int
from polyvers.cli import ydumps
from polyvers.logconfutils import init_logging
import logging
import os
import tempfile

from ruamel.yaml.comments import CommentedMap
import pytest

from py.path import local as P  # @UnresolvedImport
import os.path as osp
import textwrap as tw

from .conftest import touchpaths


init_logging(level=logging.DEBUG, logconf_files=[])

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


def test_Replaceable():
    class C(trt.HasTraits, cmdlets.Replaceable):
        a = Int()

    c = C(a=1)
    assert c.a == 1

    cc = c.replace(a=2)
    assert cc.a == 2


def test_Replaceable_Configurable():
    c = trc.Config()
    c.C.a = 1
    c.C.b = 1

    class C(trc.Configurable, cmdlets.Replaceable):
        a = Int(config=1)
        b = Int(config=1)

    c1 = C(config=c)
    assert c1.a == c1.b == 1

    c2 = c1.replace(b=2)
    assert c2.a == 1
    assert c2.b == 2


def test_Printable():
    class C(trt.HasTraits, cmdlets.Printable):
        c = Int()

    c = C(c=1)
    assert c._decide_printable_traits() == ['c']
    assert str(c) == 'C(c=1)'

    class D(C):
        d = Int()
    assert set(D()._decide_printable_traits()) == {'c', 'd'}
    assert str(D()) == 'D(d=0, c=0)'  # mro trait definition

    D.d.metadata['printable'] = True
    assert set(D()._decide_printable_traits()) == {'d'}
    del D.d.metadata['printable']

    D.printable_traits = '*'
    assert set(D()._decide_printable_traits()) == {'c', 'd'}

    D.printable_traits = ('c', )
    assert set(D()._decide_printable_traits()) == {'c'}
    D.printable_traits = ('d', )
    assert set(D()._decide_printable_traits()) == {'d'}

    ## Mention in superclass subclass trait to print!

    D.printable_traits = ()
    C.printable_traits = ('c', 'd')
    assert set(D()._decide_printable_traits()) == {'c', 'd'}


@pytest.mark.parametrize('force, token, exp', [
    (None, 'abc', False),
    (None, 1, False),
    (None, None, False),
    (False, 'abc', False),
    (False, 1, False),
    (False, None, False),
    (True, 'abc', True),
    (True, 1, True),
    (True, None, True),


    ('abc', 'abc', True),
    (1, 1, True),
    ('2', 2, False),
    (3, '3', False),
    ('abc', None, True),

    (None, 'abc', False),
    (None, 1, False),
    (None, None, False),

    (' abc ', 'abc', True),
    (' abc ', ' abc ', True),
    (' abc def', ' abc ', True),

    ('ad, bb,tt gg', 'ad', True),
    ('ad, bb,tt gg', 'bb', True),
    ('ad, bb,tt gg', 'tt', True),
    ('ad, bb,tt gg', 'gg', True),

    ('aa bb', 'aa bb', False),
])
def test_Spec_is_forced(force, token, exp):
    sp = cmdlets.Spec(force=force)
    assert sp.is_forced(token) is exp


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
    c = cmdlets.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('/d/foo/bar/.appname', ['appname_config.py', 'appname_config.json']),
        ('/d/foo\Bar/dooba/doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp


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
    c = cmdlets.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('/c/Big/BEAR/.appname', ['appname_persist.json', 'appname_config.py']),
        ('/d/foo\Bar/dooba/doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp


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
    c = cmdlets.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('D:\\foo\\bar\\.appname', ['appname_config.py', 'appname_config.json']),
        ('d:\\foo\Bar\\dooba\\doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp


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
    c = cmdlets.CfgFilesRegistry()
    cons = c._consolidate(visited)

    exp = [
        ('C:\\Big\\BEAR\\.appname', ['appname_persist.json', 'appname_config.py']),
        ('D:\\foo\Bar\\dooba\\doo', []),
    ]
    #print('FF\n', cons)
    assert cons == exp


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

    cfr = cmdlets.CfgFilesRegistry()
    fpaths = cfr.collect_fpaths(['conf'])
    fpaths = [P(p).relto(tdir).replace('\\', '/') for p in fpaths]
    assert fpaths == 'conf.json conf.py conf.d/a.json conf.d/a.py'.split()

    cfr = cmdlets.CfgFilesRegistry()
    fpaths = cfr.collect_fpaths(['conf.py'])
    fpaths = [P(p).relto(tdir).replace('\\', '/') for p in fpaths]
    assert fpaths == 'conf.py conf.py.d/a.json conf.d/a.json conf.d/a.py'.split()


def test_no_default_config_paths(tmpdir):
    cwd = tmpdir.mkdir('cwd')
    cwd.chdir()

    home = tmpdir.mkdir('home')
    os.environ['HOME'] = str(home)

    c = cmdlets.Cmd()
    c.initialize([])
    print(c._cfgfiles_registry.config_tuples)
    assert len(c.loaded_config_files) == 0


def test_default_loaded_paths():
    with tempfile.TemporaryDirectory(prefix=__name__) as tdir:
        c = cmdlets.Cmd(config_paths=[tdir])
        c.initialize([])
        print(c._cfgfiles_registry.config_tuples)
        assert len(c.loaded_config_files) == 1


test_paths0 = [
    ([], []),
    (['cc', 'cc.json'], ['cc', 'cc.json']),
    (['c.json%sc.py' % PS], ['c.json', 'c.py']),
    (['c', 'c.json%sc.py' % PS, 'jjj'], ['c', 'c.json', 'c.py', 'jjj']),
]


@pytest.mark.parametrize('inp, exp', test_paths0)
def test_PathList_trait(inp, exp):
    from pathlib import Path

    class C(trt.HasTraits):
        p = cmdlets.PathList()

    c = C()
    c.p = inp
    assert c.p == exp

    c = C()
    c.p = [Path(i) for i in inp]
    assert c.p == exp


test_paths1 = [
    (None, None, []),
    (['cc', 'cc.json'], None, []),


    ## Because of ext-stripping.
    (['b.py', 'a.json'], None, ['b.json', 'a.py']),
    (['c.json'], None, ['c.json']),

    ([''], None, []),
    (None, 'a', []),
    (None, 'a%s' % PS, []),

    (['a'], None, ['a.py']),
    (['b'], None, ['b.json']),
    (['c'], None, ['c.json', 'c.py']),

    (['c.json', 'c.py'], None, ['c.json', 'c.py']),
    (['c.json%sc.py' % PS], None, ['c.json', 'c.py']),

    (['c', 'c.json%sc.py' % PS], None, ['c.json', 'c.py']),
    (['c%sc.json' % PS, 'c.py'], None, ['c.json', 'c.py']),

    (['a', 'b'], None, ['a.py', 'b.json']),
    (['b', 'a'], None, ['b.json', 'a.py']),
    (['c'], None, ['c.json', 'c.py']),
    (['a', 'c'], None, ['a.py', 'c.json', 'c.py']),
    (['a', 'c'], None, ['a.py', 'c.json', 'c.py']),
    (['a%sc' % PS], None, ['a.py', 'c.json', 'c.py']),
    (['a%sb' % PS, 'c'], None, ['a.py', 'b.json', 'c.json', 'c.py']),

    ('b', 'a', ['b.json']),
]


@pytest.mark.parametrize('param, var, exp', test_paths1)
def test_collect_static_fpaths(param, var, exp, tmpdir):
    tdir = tmpdir.mkdir('collect_paths')

    touchpaths(tdir, """
        a.py
        b.json
        c.py
        c.json
    """)

    try:
        c = cmdlets.Cmd()
        if param is not None:
            c.config_paths = [str(tdir / ff)
                              for f in param
                              for ff in f.split(os.pathsep)]
        if var is not None:
            os.environ['POLYVERS_CONFIG_PATHS'] = os.pathsep.join(
                osp.join(tdir, ff)
                for f in var
                for ff in f.split(os.pathsep))

        paths = c._collect_static_fpaths()
        paths = [P(p).relto(tdir).replace('\\', '/') for p in paths]
        assert paths == exp
    finally:
        try:
            del os.environ['POLYVERS_CONFIG_PATHS']
        except Exception as _:
            pass


def test_help_smoketest():
    cls = cmdlets.Cmd
    cls.class_get_help()
    cls.class_config_section()
    cls.class_config_rst_doc()

    c = cls()
    c.print_help()
    c.document_config_options()
    c.print_alias_help()
    c.print_flag_help()
    c.print_options()
    c.print_subcommands()
    c.print_examples()
    c.print_help()


def test_all_cmds_help_version(capsys):
    c = cmdlets.Cmd
    with pytest.raises(SystemExit):
        c.make_cmd(argv=['help'])

    ## Check cmdlet interpolations work.
    #
    out, err = capsys.readouterr()
    assert not err
    assert '{cmd_chain}' not in out
    assert '{appname}' not in out

    with pytest.raises(SystemExit):
        c.make_cmd(argv=['--help'])
    with pytest.raises(SystemExit):
        c.make_cmd(argv=['--help-all'])
    with pytest.raises(SystemExit):
        c.make_cmd(argv=['--version'])


def test_yaml_config(tmpdir):
    tdir = tmpdir.mkdir('yamlconfig')
    conf_fpath = tdir / '.polyvers.yaml'
    conf = """
    Cmd:
      verbose:
        true
    """
    with open(conf_fpath, 'wt') as fout:
        fout.write(tw.dedent(conf))

    c = cmdlets.Cmd()
    c.config_paths = [conf_fpath]
    c.initialize(argv=[])
    assert c.verbose is True


def test_Configurable_simple_yaml_generation():
    class C(trc.Configurable):
        "Class help"
        a = trt.Int(1, config=True, help="Trait help test")
        b = trt.Int(1, config=True, help="2nd trait help test")

    cfg = CommentedMap()
    C.class_config_yaml(cfg)

    ## EXPECTED
    """
        # ############################################################################
        # C(Configurable) configuration
        # ############################################################################
        # Class help
        #

        # Trait help test
        # Default: 1
          a: 1

        # 2nd trait help test
          b: 1
    """
    cfg_str = ydumps(cfg)
    #print(cfg_str)
    msgs = ['# Class help', '# Trait help test', '# 2nd trait help test',
            'a: 1', 'b: 1']
    assert all(m in cfg_str for m in msgs)


def test_Application_yaml_generation():
    class C(trc.Configurable):
        "Class help"
        a = trt.Int(1, config=True, help="Trait help test")
        b = trt.Int(1, config=True, help="2nd trait help test")

    class MyApp(trc.Application):
        classes = [C]

    cfg = MyApp().generate_config_file_yaml()

    cfg_str = ydumps(cfg)
    print(cfg_str)

    ## EXPECTED
    """
        Application:
        # ############################################################################
        # Application(SingletonConfigurable) configuration
        # ############################################################################
        # This is an application.
        #

        # The date format used by logging formatters for %(asctime)s
        # Default: '%Y-%m-%d %H:%M:%S'
          log_datefmt: '%Y-%m-%d %H:%M:%S'
        ...
        C:
        # ############################################################################
        # C(Configurable) configuration
        # ############################################################################
        # Class help
        ...
    """
    cfg_str = ydumps(cfg)
    #print(cfg_str)
    msgs = ['# Application(SingletonConfigurable) configuration',
            '# C(Configurable) configuration']
    assert all(m in cfg_str for m in msgs)


def test_Cmd_subcmd_configures_parents(tmpdir):
    tdir = tmpdir.mkdir('yamlconfig')
    tdir.chdir()

    conf_fpath = tdir / '.config.yaml'
    conf_fpath.write_text(
        "RootCmd:\n  b:\n    2\nSubCmd:\n  s:\n    -1",
        'utf-8')

    class SubCmd(cmdlets.Cmd):
        s = trt.Int(config=True)

    class RootCmd(cmdlets.Cmd):
        subcommands = {'sub': (SubCmd, "help string")}
        a = trt.Int(config=True)
        b = trt.Int(config=True)

    r = RootCmd(config=trc.Config({'Cmd': {'config_paths': ['.config']}}),
                raise_config_file_errors=True)
    r.initialize('sub --RootCmd.a=1'.split())

    assert SubCmd.instance().s == -1
    assert r.a == 1
    assert r.b == 2
