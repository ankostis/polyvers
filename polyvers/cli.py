# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
""" Bump independently PEP-440 versions of sub-project in Git monorepos. """

from collections import ChainMap
from datetime import datetime
import os

import os.path as osp

from . import APPNAME
from . import __version__
from ._vendor import traitlets as trt
from . import fileutils as fu
## Explictely imported to stop code-analysis complains.
from ._vendor.traitlets import List, Bool, Unicode  # @UnresolvedImport
from ._vendor.traitlets import config as trc
from .autoinstance_traitlet import AutoInstance
from .strexpand_traitlet import StrExpand
from . import cmdutils as cu


####################
## Config sources ##
####################
CONFIG_VAR_NAME = '%s_CONFIG_PATHS' % APPNAME


def default_config_fname():
    """The config-file's basename (no path or extension) to search when not explicitly specified."""
    return '%s_config.py' % APPNAME


def default_config_dir():
    """The folder of user's config-file."""
    return fu.convpath('~/.%s' % APPNAME)


def default_config_fpaths():
    """The full path of to user's config-file, without extension."""
    return [osp.join(default_config_dir(), default_config_fname())]
#######################


class Base(cu.Spec):
    " Common base for configurables and apps."

    #: A stack of 3 dics used by `interpolation_context_factory()` class-method,
    #: listed with 1st one winning over:
    #:   0. vcs-info: writes affect this one only,
    #:   1. time: (now, utcnow), always updated on access,
    #:   2. env-vars, `$`-prefixed.
    interpolation_context = ChainMap([{}, {}, {}])

    @classmethod
    def interpolation_context_factory(cls, obj, trait, text):
        maps = cls.interpolation_context
        if not maps:
            maps[2].update({'$' + k: v for k, v in os.environ.items()})
        maps[1].update({
            'now': datetime.now(),
            'utcnow': datetime.utcnow(),
        })

        return cls.interpolation_context


class Project(Base):
    tag = Bool(
        config=True,
        help="""
        Enable tagging, per-project.

        Adds a signed tag with name/msg from `tag_name`/`message` (commit implied).

        """)
    sign_tags = Bool(
        config=True,
        help="Enable PGP-signing of tags (see also `sign_user`)."
    )

    sign_user = Unicode(
        config=True,
        help="The signing PGP user (email, key-id)."
    )

    message = StrExpand(
        "chore(ver): bump {current_version} → {new_version}",
        config=True,
        help="""
            The message for commits and per-project tags.

            Available interpolations:
            - `{current_version}`
            - `{new_version}`
            - `{now}`
            - `{utcnow:%d.%m.%Y}`
            - <`{$ENV_VAR}`>
        """)


class PolyversCmd(cu.Cmd, Project):
    """
    Bump independently PEP-440 versions of sub-project in Git monorepos.

    SYNTAX:
      %(cmd_chain)s <sub-cmd> ...
    """
    version = __version__
    examples = Unicode("""
        - Let it guess the configurations for your monorepo::
              %(cmd_chain)s init
          You may specify different configurations paths with:
              %(cmd_chain)s --config-paths /foo/bar/:~/.%(appname)s.yaml:.

        - Use then the main sub-commands::
              %(cmd_chain)s status
              %(cmd_chain)s setver 0.0.0.dev0 -c '1st commit, untagged'
              %(cmd_chain)s bump -t 'Mostly model changes, tagged'

        PEP-440 Version Samples:
        - Pre-releases: when working on new features:
            X.YbN               # Beta release
            X.YrcN  or  X.YcN   # Release Candidate
            X.Y                 # Final release
        - Post-release:
            X.YaN.postM         # Post-release of an alpha release
            X.YrcN.postM        # Post-release of a release candidate
        - Dev-release:
            X.YaN.devM          # Developmental release of an alpha release
            X.Y.postN.devM      # Developmental release of a post-release
    """)
    classes = [Project]

    projects = List(
        AutoInstance(Project),
        config=True)

    use_leaf_releases = Bool(
        True,
        config=True,
        help="""
            Version-ids statically engraved in-trunk when false, otherwise in "leaf" commits.

            - Limit branches considered as "in-trunk" using `in_trunk_branches` param.
            - Select the name of the Leaf branch with `leaf_branch` param.

            Leaf release-commits avoid frequent merge-conflicts in files containing
            the version-ids.
    """)

    amend = Bool(
        config=True,
        help="Amend the last bump-version commit, if any.")

    commit = Bool(
        config=True,
        help="""
            Commit after engraving with a commit-message describing version bump.

            - If false, no commit created, just search'n replace version-ids.
              Related params: out_of_trunk, message.
            - False make sense only if `use_leaf_releases=False`
        """)

    def _my_text_interpolations(self):
        d = super()._my_text_interpolations()
        d.update({'appname': APPNAME})
        return d

    @trt.default('config_basename')
    def _config_basename(self):
        return default_config_fname()

    @trt.default('config_paths')
    def _config_fpaths(self):
        return default_config_fpaths()

#     @trt.default('all_app_configurables')
#     def _all_app_configurables(self):
#         from .cfgcmd import WriteCmd, InfosCmd, ShowCmd, DescCmd,
#
#         return WriteCmd, InfosCmd, ShowCmd, DescCmd


class VersionSubcmd(cu.Cmd):
    pass


class InitCmd(cu.Cmd):
    """Generate configurations based on directory contents."""
    def run(self, *args):
        pass


class StatusCmd(VersionSubcmd):
    """
    List the versions of project(s).

    SYNTAX:
        %(cmd_chain)s [OPTIONS] [<project>]...
    """
    def run(self, *args):
        pass


class SetverCmd(VersionSubcmd):
    """
    Set the version of project(s) exacty as given.

    SYNTAX:
        %(cmd_chain)s [OPTIONS] <version> [<project>]...

    - If no <version-offset> specified, increase the last part (e.g 0.0.dev0-->dev1).
    - If no project(s) specified, increase the versions for all projects.
    - Denied if version for some projects is backward-in-time or has jumped parts;
      use --force if you might.
    - Prefer not to add a 'v' prefix!
    """


class BumpCmd(VersionSubcmd):
    """
    Increase the version of project(s) by the given offset.

    SYNTAX:
        %(cmd_chain)s [OPTIONS] [<version-offset>] [<project>]...
        %(cmd_chain)s [OPTIONS] --part <offset> [<project>]...

    - If no <version-offset> specified, increase the last part (e.g 0.0.dev0-->dev1).
    - If no project(s) specified, increase the versions for all projects.
    - Denied if version for some projects is backward-in-time or has jumped parts;
      use --force if you might.
    - Don't add a 'v' prefix!
    """
    def run(self, *args):
        pass


class Logconf(cu.Cmd):
    """Write a logging-configuration file that can filter logs selectively."""
    def run(self, *args):
        pass


subcmds = cu.build_sub_cmds(InitCmd, StatusCmd,
                            SetverCmd, BumpCmd,
                            Logconf)
subcmds['config'] = ('polyvers.cfgcmd.ConfigCmd',
                     "Commands to inspect configurations and other cli infos.")

PolyversCmd.subcommands = subcmds

PolyversCmd.flags = {
    ## Inherited from Application
    #
    'show-config': ({
        'Application': {
            'show_config': True,
        },
    }, trc.Application.show_config.help),
    'show-config-json': ({
        'Application': {
            'show_config_json': True,
        },
    }, trc.Application.show_config_json.help),

    ## Consulted by main.init_logging() if in sys.argv.
    #
    ('v', 'verbose'): (
        {'Spec': {'verbose': True}},
        cu.Spec.verbose.help
    ),
    ('f', 'force'): (
        {'Spec': {'force': True}},
        cu.Spec.force.help
    ),
    ('n', 'dry-run'): (
        {'Spec': {'force': True}},
        cu.Spec.dry_run.help
    ),
    ('c', 'commit'): (
        {},
        PolyversCmd.commit.help
    ),
    ('a', 'amend'): (
        {'Polyvers': {'amend': True}},
        PolyversCmd.amend.help
    ),
    ('t', 'tag'): (
        {'Project': {'tag': True}},
        Project.tag.help
    ),
    ('s', 'sign-tags'): (
        {'Project': {'sign_tags': True}},
        Project.sign_tags.help
    ),
}

PolyversCmd.aliases = {
    ('m', 'message'): 'Project.message',
    ('u', 'sign-user'): 'Project.sign_user',
}

# TODO: Will work when patched: https://github.com/ipython/traitlets/pull/449
PolyversCmd.config_paths.metadata['envvar'] = CONFIG_VAR_NAME
