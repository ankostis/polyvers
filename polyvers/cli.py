# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""The code of *polyvers* shell-commands."""

from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, Tuple
import io
import logging

from . import APPNAME, __version__, __updated__, cmdlets, \
    pvtags, engrave, fileutils as fu
from . import logconfutils as lcu
from ._vendor import traitlets as trt
from ._vendor.traitlets import config as trc
from ._vendor.traitlets.traitlets import List, Bool, Unicode
from .autoinstance_traitlet import AutoInstance


# TODO: after pvlib split, move NOTICE level into package.
NOTICE = 25
lcu.patch_new_level_in_logging(NOTICE, 'NOTICE')
lcu.default_logging_level = NOTICE

log = logging.getLogger(__name__)

#: YAML dumper used to serialize command's outputs.
_Y = None


def ydumps(obj):
    "Dump any false objects as empty string, None as nothing, or as YAML. "
    global _Y

    if not _Y:
        from ruamel import yaml
        from ruamel.yaml.representer import RoundTripRepresenter

        for d in [OrderedDict, defaultdict]:
            RoundTripRepresenter.add_representer(
                d, RoundTripRepresenter.represent_dict)
        _Y = yaml.YAML()

    if obj is None:
        return
    if not obj:
        return ''

    sio = io.StringIO()
    _Y.dump(obj, sio)
    return sio.getvalue().strip()


####################
## Config sources ##
####################
CONFIG_VAR_NAME = '%s_CONFIG_PATHS' % APPNAME
#######################


class PolyversCmd(cmdlets.Cmd):
    """
    Bump independently PEP-440 versions of sub-project in Git monorepos.

    SYNTAX:
      {cmd_chain} <sub-cmd> ...
    """
    version = __version__
    examples = Unicode("""
        - Let it guess the configurations for your monorepo::
              {cmd_chain} init
          You may specify different configurations paths with:
              {cmd_chain} --config-paths /foo/bar/:~/.%(appname)s.yaml:.

        - Use then the main sub-commands::
              {cmd_chain} status
              {cmd_chain} setver 0.0.0.dev0 -c '1st commit, untagged'
              {cmd_chain} bump -t 'Mostly model changes, tagged'

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
    classes = [pvtags.Project]

    #: Interrogated by all Project instances by searching up their parent chain.
    default_project = AutoInstance(
        pvtags.Project,
        allow_none=True,
        config=True,
        help="""
        Set version-schema (monorepo/monoproject) by enforcing defaults for all Project instances.

        Installed by configuration, or auto-discover when no configs loaded.
        """)

    projects = List(
        AutoInstance(pvtags.Project),
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

    @trt.default('subcommands')
    def _subcommands(self):
        subcmds = cmdlets.build_sub_cmds(InitCmd, StatusCmd,
                                         BumpCmd,
                                         LogconfCmd)
        subcmds['config'] = (
            'polyvers.cfgcmd.ConfigCmd',
            "Commands to inspect configurations and other cli infos.")

        return subcmds

    def collect_app_infos(self):
        """Provide extra infos to `config infos` subcommand."""
        return {
            'version': __version__,
            'updated': __updated__,
            ## TODO: add more app-infos.
        }

    @trt.default('all_app_configurables')
    def _all_app_configurables(self):
        return [type(self),
                pvtags.Project,
                InitCmd, StatusCmd, BumpCmd, LogconfCmd,
                engrave.Engrave, engrave.GraftSpec,
                ]

    @trt.default('config_paths')
    def _config_paths(self):
        basename = self.config_basename
        paths = []

        git_root = fu.find_git_root()
        if git_root:
            paths.append(str(git_root / basename))
        else:
            paths.append('.')

        paths.append('~/%s' % basename)

        return paths

    def check_project_configs_exist(
            self,
            ## Needed bc it is subcmd that load configs, not root-app.
            cfgfiles_registry: cmdlets.CfgFilesRegistry,
            skip_conf_scream=False) -> Tuple[bool, bool, bool]:
        """
        Checks if basic config-properties are given (from config-file or cmd-line flags)

        and optionally warn if config-file is missing from Git repo.

        :return:
            a 2-tuple ``(has_conf_file, has_template_project, has_subprojects)``:

            - has_conf_file: true when a per-repo config-file exists
            - has_template_project: true when :attr:`PolyversCmd.default_project` defined
              e.g. from cmd-line flag --monorepo or from config-file.
            - has_subprojects: true when :attr:`PolyversCmd.projects` defined.

        :raise CmdException:
            if cwd not inside a git repo
        """
        git_root = self.git_root
        if not git_root:
            raise cmdlets.CmdException(
                "Current-dir '%s' is not inside a git-repo!" % Path().resolve())

        app = self.root()  # type: ignore
        has_template_project = app.default_project is not None
        has_subprojects = bool(app.projects)

        has_conf_file = False
        for p in cfgfiles_registry.collected_paths:
            try:
                if Path(p).relative_to(git_root):
                    has_conf_file = True
            except ValueError as _:
                pass

        ## TODO: Check if template-project & projects exist!

        if not (skip_conf_scream or has_conf_file):
            self.log.info(
                "No '%s' config-file(s) found!\n"
                "  Invoke `polyvers init` to create it and stop this warning.",
                git_root / self.config_basename)

        return (has_conf_file, has_template_project, has_subprojects)

    _git_root: Path = None

    @property
    def git_root(self) -> Path:
        if self._git_root is None:
            self._git_root = fu.find_git_root()
        return self._git_root

    projects_scan = AutoInstance(
        engrave.Engrave,
        default_value={
            'globs': ['**/setup.py'],
            'grafts': [
                {'regex': r'''(?x)
                    \b(name|PROJECT|APPNAME|APPLICATION)
                    \ *=\ *
                    (['"])
                        (?P<pname>[\w\-.]+)
                    \2
                '''}
            ]
        },
        config=True,
        help="""
        Glob-patterns and regexes to auto-discover project basepaths and names.

        - The glob-patterns are used to locate files in project roots.
          For every file collected, its dirname becomes as "project-root.
        - Regex(es) to extract project-name.
          If none, or more than one, match, project detection fails.
        - Used when auto-discovering projects, to construct the configuration file,
          or when no configuration file exists.
        """)

    pvtags_scan = List(
        AutoInstance(pvtags.Project),
        default_value=[
            pvtags.make_match_all_pvtags_project(),
            pvtags.make_match_all_vtags_project(),
        ],
        config=True,
        help="""
        Patterns and regexps to search for *pvtags* or plain *vtags* in git repo.

        - Used when auto-discovering projects, to construct new or update
          a configuration file.
        """)

    def autodiscover_project_basepaths(self) -> Dict[str, Path]:
        """
        Invoked when no config exists (or asked to updated it) to guess projects.

        :return:
            a mapping of {pnames: basepaths}
        """
        file_hits = self.projects_scan.scan_all_hits(mybase=self.git_root)

        projects: Dict[str, Path] = {
            fspec.grafts[0].hits[0].groupdict()['pname']: fpath.parent
            for fpath, fspec in file_hits.items()
            if fspec.nhits == 1}

        return projects

    def autodiscover_tags(self):
        """
        Guess whether *pvtags* or *vtags* apply.
        """
        pvtag_proj, vtag_proj = pvtags.collect_standard_versioning_tags()

        if bool(pvtag_proj.pvtags_history) ^ bool(vtag_proj.pvtags_history):
            return pvtag_proj.pvtags_history and pvtag_proj or vtag_proj
        else:
            raise cmdlets.CmdException(
                "Cannot auto-discover versioning scheme, "
                "confusing or no versioning-tags:\n%s"
                "\n\n  Try --monorepo/--monoproject flags." %
                ydumps({'pvtags': pvtag_proj.pvtags_history,
                        'vtags': vtag_proj.pvtags_history}))


class InitCmd(cmdlets.Cmd):
    """Generate configurations based on directory contents."""

    def run(self, *args):
        if len(args) > 0:
            raise cmdlets.CmdException(
                "Cmd %r takes no arguments, received %d: %r!"
                % (self.name, len(args), args))

        res = self.check_project_configs_exist(self._cfgfiles_registry,
                                               skip_conf_scream=True)
        has_conf_file, _, __ = res

        if not self.force and has_conf_file:
            raise cmdlets.CmdException(
                "Polyvers already initialized!"
                "\n  Use --force if you must, and also check those files:"
                "\n    %s" %
                '\n    '.join(self._cfgfiles_registry.collected_paths))

        yield "Init would be created...."


class StatusCmd(cmdlets.Cmd):
    """
    List the versions of project(s).

    SYNTAX:
        {cmd_chain} [OPTIONS] [<project>]...
    """
    def run(self, *args):
        git_root = fu.find_git_root()
        rootapp = self.root()

        res = rootapp.check_project_configs_exist(self._cfgfiles_registry)
        _, has_template_project, has_subprojects = res

        if not has_template_project:
            guessed_project = rootapp.autodiscover_tags()
            rootapp.default_project = guessed_project.replace(parent=self)
            log.info("Auto-discovered versioning scheme: %s", guessed_project.pname)

        if has_subprojects:
            projects = rootapp.projects
        else:
            proj_paths: Dict[str, Path] = rootapp.autodiscover_project_basepaths()
            if not proj_paths:
                raise cmdlets.CmdException(
                    "Cannot auto-discover (sub-)project path(s)!"
                    "\n  Please use `ìnit` cmd to specify sub-projects explicitly.")

            ## TODO: report mismatch of project-names/vtags.
            ## TODO: extract method to classify pre-populated histories.

            log.info(
                "Auto-discovered %i sub-project(s) in git-root '%s': \n%s",
                len(proj_paths), git_root.resolve(),
                ydumps({k: str(v) for k, v in proj_paths.items()}))

            projects = [pvtags.Project(parent=self, pname=name, basepath=basepath)
                        for name, basepath in proj_paths.items()]

            rootapp.projects = projects

        try:
            yield ydumps({'versions': {p.pname: p.git_describe()}
                          for p in projects})
        except pvtags.GitVoidError as ex:
            log.warning("Failed fetching versions for projects '%s' due to: %s "
                        "\n  Inspecting any *pvtags* instead.",
                        ', '.join(p.pname for p in projects), ex)

            ## TODO: extract method to classify pre-populated histories.
            pvtags.populate_pvtags_history(*projects)
            ## TODO: YAMLable Project (apart from Strable) with metadata Print/header
            tags = {'tags': {p.pname: {'basepath': str(p.basepath),
                                       'history': p.pvtags_history}}
                    for p in projects}
            yield ydumps(tags)


class BumpCmd(cmdlets.Cmd):
    """
    Increase the version of project(s) by the given offset.

    SYNTAX:
        {cmd_chain} [OPTIONS] [<version-offset>] [<project>]...
        {cmd_chain} [OPTIONS] --part <offset> [<project>]...

    - If no <version-offset> specified, increase the last part (e.g 0.0.dev0-->dev1).
    - If no project(s) specified, increase the versions for all projects.
    - Denied if version for some projects is backward-in-time or has jumped parts;
      use --force if you might.
    - Don't add a 'v' prefix!
    """
    def run(self, *args):
        self.check_project_configs_exist(self._cfgfiles_registry)


class LogconfCmd(cmdlets.Cmd):
    """Write a logging-configuration file that can filter logs selectively."""
    def run(self, *args):
        pass


# TODO: Will work when patched: https://github.com/ipython/traitlets/pull/449
PolyversCmd.config_paths.tag(envvar=CONFIG_VAR_NAME)
trc.Application.raise_config_file_errors.tag(config=True)
trc.Application.raise_config_file_errors.help = \
    'Whether failing to load config files should prevent startup.'

PolyversCmd.flags = {  # type: ignore
    ## Copied from Application
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
        cmdlets.Spec.verbose.help
    ),
    ('f', 'force'): (
        {'Spec': {'force': True}},
        cmdlets.Spec.force.help
    ),
    ('n', 'dry-run'): (
        {'Spec': {'dry_run': True}},
        cmdlets.Spec.dry_run.help
    ),
    ('d', 'debug'): ({
        'Spec': {
            'debug': True,
        }, 'Application': {
            'show_config': True,
            'raise_config_file_errors': True,
        }},
        cmdlets.Spec.debug.help
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
        pvtags.Project.tag.help
    ),
    ('s', 'sign-tags'): (
        {'Project': {'sign_tags': True}},
        pvtags.Project.sign_tags.help
    ),

    'monorepo': (
        {'PolyversCmd': {'default_project': pvtags.make_pvtag_project()}},
        "Use *pvtags* for versioning sub-projects in this git monorepo."
    ),
    'monoproject': (
        {'PolyversCmd': {'default_project': pvtags.make_vtag_project()}},
        "Use plain *vtags* for versioning a single project in this git repo."
    ),
}

PolyversCmd.aliases = {  # type: ignore
    ('m', 'message'): 'Project.message',
    ('u', 'sign-user'): 'Project.sign_user',
}
