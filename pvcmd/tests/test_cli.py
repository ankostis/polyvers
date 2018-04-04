#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
from collections import OrderedDict, defaultdict
import io

import pytest

from polyvers import cli, __version__, __updated__, pvproject, pvtags
from polyvers.__main__ import main
from polyvers._vendor.traitlets import config as trc
from polyvers.cli import PolyversCmd
from polyvers.cmdlet import cmdlets
from polyvers.utils.mainpump import ListConsumer
from polyvers.utils.oscmd import cmd

from .conftest import (
    check_text, clearlog, dict_eq,
    make_setup_py)


@pytest.mark.parametrize('inp, exp', [
    (None, ''),
    ({}, ''),
    ([], ''),
    (OrderedDict(a=1), "a: 1"),
    (defaultdict(list, a='1'), "a: '1'"),

])
def test_yaml_dump(inp, exp):
    got = cli.ydumps(inp)
    assert got == exp

    sio = io.StringIO()
    cli.ydumps(inp, sio)
    got = sio.getvalue()
    assert got.strip() == exp


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
    ('config desc', ['--Cmd.config_paths=', 'StatusCmd'], []),
    ('config desc bump -c', ['Increase or set the version of project', 'BumpCmd'], []),
    ('config show Project', ['Project(Replaceable'], []),
    ('config show Project.tag', ["tag_vprefixes = ('v', 'r')"], []),
])
def test_config_cmd(cmd, match, illegal):
    ## VERY IMPORTANT TCs FOR ConfigCmd!!!
    lc = ListConsumer()
    rc = main(cmd.split(), cmd_consumer=lc)
    assert rc == 0
    check_text(lc.items, match, illegal)
    #print('\n'.join(lc.items))


def test_bootstrapp_projects_explicit(no_repo, empty_repo, caplog):
    no_repo.chdir()

    cmd = PolyversCmd()
    with pytest.raises(pvtags.NoGitRepoError):
        cmd.bootstrapp_projects()

    empty_repo.chdir()

    cmd = PolyversCmd()
    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException,
                       match="Cannot auto-discover versioning scheme"):
        cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])

    cfg = trc.Config()
    cfg.Project.pvtag_frmt = cfg.Project.pvtag_regex = 'some'
    cmd = PolyversCmd(config=cfg)
    clearlog(caplog)
    with pytest.raises(cmdlets.CmdException,
                       match="Cannot auto-discover \(sub-\)project"):
        cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])

    cfg.PolyversCmd.projects = [pvproject.Project()]
    cmd = PolyversCmd(config=cfg)
    clearlog(caplog)
    cmd.bootstrapp_projects()
    assert all(t not in caplog.text for t in [
        "Auto-discovered 2 sub-project(s)",
        "Auto-discovered versioning scheme",
    ])


def check_bootstrapp_projects_autodiscover(myrepo, caplog, vscheme):
    myrepo.chdir()
    caplog.set_level(0)

    cmd = PolyversCmd()
    clearlog(caplog)
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
    cmd = PolyversCmd()
    clearlog(caplog)
    clearlog(caplog)
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
    cmd = PolyversCmd()
    clearlog(caplog)
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


def test_status_cmd_vtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## setup.py + --monorepo
    #
    clearlog(caplog)
    make_setup_py(mutable_repo, 'simple')

    rc = main('status --mono-project -v'.split())
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

    rc = main('status --mono-project --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert 'simple:\n  version:\n  history: []\n  basepath: .\n' == out

    ##############
    ## TAG REPO
    #
    clearlog(caplog)

    cmd.git.tag('v0.1.0', m='annotate!')
    rc = main('status -v'.split())
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
    assert {'simple': {'version': 'v0.1.0'}} == cli.yloads(out)

    rc = main('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = cli.yloads("""
        simple:
          version: v0.1.0
          history:
          - v0.1.0
          basepath: .
    """)
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all simple'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all simple foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all foobar'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not cli.yloads(out)


def test_status_cmd_pvtags(mutable_repo, caplog, capsys):
    mutable_repo.chdir()

    ##############
    ## setup.py + --monorepo
    #
    clearlog(caplog)
    make_setup_py(mutable_repo, 'base')
    make_setup_py(mutable_repo / 'foo_project', 'foo')

    rc = main('status --monorepo -v'.split())
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
    assert {'base': {'version': None}, 'foo': {'version': None}} == cli.yloads(out)

    rc = main('status --monorepo --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = cli.yloads('base:\n  version:\n  history: []\n  basepath: .\n'
                     'foo:\n  version:\n  history: []\n  basepath: foo_project\n')
    assert dict_eq(exp, cli.yloads(out))

    ##############
    ## TAG REPO
    #
    clearlog(caplog)

    cmd.git.tag('base-v0.1.0', m='annotate!')
    rc = main('status -v'.split())
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
    exp = cli.yloads("base:\n  version: base-v0.1.0\nfoo:\n  version:\n")
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    exp = cli.yloads("""
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
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all base foo'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all base foo BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert dict_eq(exp, cli.yloads(out))

    rc = main('status --all BAD'.split())
    assert rc == 0
    out, err = capsys.readouterr()
    assert not out

    rc = main('status --all foo BAD'.split())
    assert rc == 0
    exp = cli.yloads("""
    foo:
      version:
      history: []
      basepath: foo_project
    """)
    out, err = capsys.readouterr()
    assert dict_eq(exp, cli.yloads(out))
