#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from polyvers import cli, __version__, __updated__, pvproject, pvtags
from polyvers._vendor.traitlets import config as trc
from polyvers.cmdlet import cmdlets
from polyvers.utils import yamlutil as yu
from polyvers.utils.mainpump import ListConsumer
from polyvers.utils.oscmd import cmd
import re

import pytest

import textwrap as tw

from .conftest import check_text, dict_eq, make_setup_py


all_cmds = [c
            for c in cli.PolyversCmd().all_app_configurables
            if issubclass(c, cmdlets.Cmd)]


@pytest.mark.parametrize('cmd', all_cmds)
def test_all_cmds_help_smoketest(cmd):
    cmd.class_get_help()
    cmd.class_config_section()
    cmd.class_config_rst_doc()

    c = cmd()
    c.print_help()
    c.document_config_options()
    c.print_alias_help()
    c.print_flag_help()
    c.print_options()
    c.print_subcommands()
    c.print_examples()
    #assert len(list(c.emit_examples())) > 1  TODO: Require cmd examples
    c.print_help()


@pytest.mark.parametrize('cmd', all_cmds)
def test_all_cmds_help_version(cmd, capsys):
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['help'])

    ## Check cmdlet interpolations work.
    #
    out, err = capsys.readouterr()
    assert not err
    assert '{cmd_chain}' not in out
    assert '{appname}' not in out

    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--help-all'])
    with pytest.raises(SystemExit):
        cmd.make_cmd(argv=['--version'])


@pytest.mark.parametrize('cmd, match, illegal', [
    ('config infos', ['version: %s' % __version__,
                      'updated: %s' % __updated__], ['config_paths: null']),
    ('config desc', ['--Cmd.config_paths=', 'StatusCmd'],
     'log_format log_level log_datefmt'.split()),
    ('config desc bump -c', ['Increase or set the version of project', 'BumpCmd'], []),
    ('config show Project', ['Project(Replaceable'], []),
    ('config show Project.tag', ["tag_vprefixes = ('v', 'r')"], []),
])
def test_config_cmd(cmd, match, illegal):
    ## VERY IMPORTANT TCs FOR ConfigCmd!!!
    lc = ListConsumer()
    rc = cli.run(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    check_text(lc.items, match, illegal)
    #print('\n'.join(lc.items))


def test_bootstrapp_projects_explicit(no_repo, empty_repo, caplog):
    no_repo.chdir()

    ## No GIT
    #
    cmd = cli.PolyversCmd()
    with pytest.raises(pvtags.NoGitRepoError):
        cmd.bootstrapp_projects()

    empty_repo.chdir()

    ## Specify: nothing
    #
    cmd = cli.PolyversCmd()
    caplog.clear()
    with pytest.raises(cmdlets.CmdException,
                       match="Cannot auto-discover versioning scheme"):
        cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])

    ## Specify: VScheme
    #
    cfg = trc.Config()
    cfg.Project.pvtag_frmt = cfg.Project.pvtag_regex = 'some'
    cmd = cli.PolyversCmd(config=cfg)
    caplog.clear()
    with pytest.raises(cmdlets.CmdException,
                       match="Cannot auto-discover \(sub-\)project"):
        cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])

    ## Specify: VScheme + 1xPRojects
    #
    cfg.PolyversCmd.projects = [pvproject.Project()]
    cmd = cli.PolyversCmd(config=cfg)
    caplog.clear()
    cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])

    ## Specify: VScheme + 1xPRojects
    #
    cfg.PolyversCmd.projects = [pvproject.Project(), pvproject.Project()]
    cmd = cli.PolyversCmd(config=cfg)
    caplog.clear()
    cmd.bootstrapp_projects()
    check_text(
        caplog.text,
        require=[
        ], forbid=[
            r" Auto-discovered versioning scheme",
            r"Auto-discovered \d+ sub-project",
            r"Cannot auto-discover versioning scheme"
            r"Cannot auto-discover \(sub-\)project",
            r"Incompatible \*vtags\* version-scheme",
        ],
        is_regex=True)

    ## Specify: VScheme + 1+PData
    #
    del cfg.PolyversCmd['projects']
    cfg.PolyversCmd.pdata = {'foo': 'foo_path', 'bar': 'bar_path'}
    cmd = cli.PolyversCmd(config=cfg)
    caplog.clear()
    cmd.bootstrapp_projects()
    assert len(cmd.projects) == 2
    check_text(
        caplog.text,
        require=[
        ], forbid=[
            r" Auto-discovered versioning scheme",
            r"Auto-discovered \d+ sub-project",
            r"Cannot auto-discover versioning scheme"
            r"Cannot auto-discover \(sub-\)project",
            r"Incompatible \*vtags\* version-scheme",
        ],
        is_regex=True)


def check_bootstrapp_projects_autodiscover(myrepo, caplog, vscheme):
    myrepo.chdir()
    caplog.set_level(0)

    cmd = cli.PolyversCmd()
    caplog.clear()
    with pytest.raises(cmdlets.CmdException,
                       match="Cannot auto-discover \(sub-\)project"):
        cmd.bootstrapp_projects()
    check_text(
        caplog.text,
        require=[
            r" Auto-discovered versioning scheme: %s" % vscheme,
        ], forbid=[
            r"Auto-discovered \d+ sub-project\(s\)",
            r"Cannot auto-discover versioning scheme"
        ],
        is_regex=True)

    make_setup_py(myrepo, 'simple')
    cmd = cli.PolyversCmd()
    caplog.clear()
    caplog.clear()
    cmd.bootstrapp_projects()
    assert len(cmd.projects) == 1
    assert cmd.projects[0].basepath.samefile(str(myrepo))
    check_text(
        caplog.text,
        require=[
            r" Auto-discovered versioning scheme: %s" % vscheme,
            r"Auto-discovered 1 sub-project\(s\)",
        ], forbid=[
            r"Cannot auto-discover versioning scheme"
            r"Cannot auto-discover \(sub-\)project",
        ],
        is_regex=True)

    prj2_basepath = myrepo / 'extra' / 'project'
    make_setup_py(prj2_basepath, 'extra')
    cmd = cli.PolyversCmd()
    caplog.clear()
    cmd.bootstrapp_projects()
    assert len(cmd.projects) == 2
    assert cmd.projects[0].basepath.samefile(str(myrepo))
    assert cmd.projects[1].basepath.samefile(str(prj2_basepath))
    check_text(
        caplog.text,
        require=[
            r" Auto-discovered versioning scheme: %s" % vscheme,
            r"Auto-discovered 2 sub-project\(s\)",
        ], forbid=[
            r"Cannot auto-discover versioning scheme"
            r"Cannot auto-discover \(sub-\)project",
        ],
        is_regex=True)


def test_bootstrapp_projects_autodiscover_mono_project(mutable_vtags_repo, caplog):
    check_bootstrapp_projects_autodiscover(mutable_vtags_repo, caplog,
                                           pvtags.MONO_PROJECT)
    check_text(
        caplog.text,
        require=["Incompatible *vtags* version-scheme with 2 sub-projects"])


def test_bootstrapp_projects_autodiscover_monorepo(mutable_pvtags_repo, caplog):
    check_bootstrapp_projects_autodiscover(mutable_pvtags_repo, caplog,
                                           pvtags.MONOREPO)


def test_init_cmd_mono_project(mutable_vtags_repo):
    mutable_vtags_repo.chdir()

    rc = cli.run('init --mono-project --pdata f=g -v'.split())
    assert rc == 0

    cfg = trc.Config()
    cfg.Project.pvtag_frmt = cfg.Project.pvtag_regex = 'some'
    cfg.PolyversCmd.pdata = {'foo': 'foo_path'}
    cmd = cli.InitCmd(config=cfg)
    cmd.run()

    exp_fpath = (mutable_vtags_repo / '.polyvers.yaml')
    got = exp_fpath.read_text('utf-8')
    print(got)
    cleaned_text = '# Spec(LoggingConfigurable) configuration'
    assert cleaned_text not in got

    exp_hierarchy = tw.dedent("""\
        # ############################################################################
        # Configuration hierarchy for `polyvers`:
        #   InitCmd     --> _SubCmd
        #   Project     --> Spec
        #   StatusCmd   --> _SubCmd
        #   BumpCmd     --> _SubCmd
        #   LogconfCmd  --> _SubCmd
        #   _SubCmd     --> PolyversCmd
        #   PolyversCmd --> Cmd
        #   Cmd         --> Application, Spec
        #   Application\\s*
        #   Engrave     --> Spec
        #   Graft       --> Spec
        #   Spec\\s*
        # ############################################################################
        #""")
    assert re.search(exp_hierarchy, got)

    exp_headers = tw.dedent("""\
        # ############################################################################
        # Project(Spec) configuration
        # ############################################################################
        # Configurations for projects, in general, and specifically for each one.""")
    assert exp_headers in got

    exp_help = tw.dedent("""\
        # ############################################################################
        # PolyversCmd(Cmd) configuration
        # ############################################################################
        # Bump independently PEP-440 versions of sub-project in Git monorepos.
        # SYNTAX:
        #   {cmd_chain} <sub-cmd> ...
        #""")
    assert exp_help in got

    exp_value = tw.dedent(r'''
        |-
            (?xmi)
                ^(?P<pname>)
                {vprefix}(?P<version>\d[^-]*)
                (?:-(?P<descid>\d+-g[a-f\d]+))?$''')
    assert exp_value[1:] in got


# def test_init_cmd_monorepo(mutable_repo):
#     mutable_repo.chdir()


def test_status_cmd_vtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## setup.py + --monorepo
    #
    caplog.clear()
    make_setup_py(mutable_repo, 'simple')

    rc = cli.run('status --mono-project -v'.split())
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            "Auto-discovered 1 sub-project(s)",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert 'simple:\n  version:\n' == out

    rc = cli.run('status --mono-project --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert 'simple:\n  version:\n  history: []\n  basepath: .\n' == out

    ##############
    ## TAG REPO
    #
    caplog.clear()

    cmd.git.tag('v0.1.0', m='annotate!')
    rc = cli.run('status -v'.split())
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            "Auto-discovered 1 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert {'simple': {'version': 'v0.1.0'}} == yu.yloads(out)

    rc = cli.run('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = yu.yloads("""
        simple:
          version: v0.1.0
          history:
          - v0.1.0
          basepath: .
    """)
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all simple'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all simple foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not yu.yloads(out)


def test_status_cmd_pvtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## setup.py + --monorepo
    #
    caplog.clear()
    make_setup_py(mutable_repo, 'base')
    make_setup_py(mutable_repo / 'foo_project', 'foo')

    rc = cli.run('status --monorepo -v'.split())
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            "Auto-discovered 2 sub-project(s)",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    assert {'base': {'version': None}, 'foo': {'version': None}} == yu.yloads(out)

    rc = cli.run('status --monorepo --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = yu.yloads('base:\n  version:\n  history: []\n  basepath: .\n'
                    'foo:\n  version:\n  history: []\n  basepath: foo_project\n')
    assert dict_eq(exp, yu.yloads(out))

    ##############
    ## TAG REPO
    #
    caplog.clear()

    cmd.git.tag('base-v0.1.0', m='annotate!')
    rc = cli.run('status -v'.split())
    assert rc == 0
    check_text(
        caplog.text,
        require=[
            "Auto-discovered 2 sub-project(s)",
            "Auto-discovered versioning scheme",
        ], forbid=[
            "Cannot auto-discover (sub-)project",
            "Cannot auto-discover versioning scheme,"
        ])
    out, err = capsys.readouterr()
    assert not err
    exp = yu.yloads("base:\n  version: base-v0.1.0\nfoo:\n  version:\n")
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = yu.yloads("""
    base:
      version: base-v0.1.0
      history:
      - base-v0.1.0
      basepath: .
    foo:
      version:
      history: []
      basepath: foo_project
    """)
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all base foo'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all base foo BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, yu.yloads(out))

    rc = cli.run('status --all BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not out

    rc = cli.run('status --all foo BAD'.split())
    assert rc == 0
    exp = yu.yloads("""
    foo:
      version:
      history: []
      basepath: foo_project
    """)
    out, err = capsys.readouterr()
    assert dict_eq(exp, yu.yloads(out))
