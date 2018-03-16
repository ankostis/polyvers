# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""The code of *polyvers* shell-commands."""

from collections import OrderedDict, defaultdict, Mapping
from pathlib import Path
from typing import Dict, Set  # noqa: F401, @UnusedImport  flake not seeing Set usage
import io
import logging

from . import APPNAME, __version__, __updated__, cmdlets, pvtags, engrave, \
    polyverslib as pvlib, fileutils as fu
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


####################
## Config sources ##
####################
CONFIG_VAR_NAME = '%s_CONFIG_PATHS' % APPNAME.upper()
#######################


#: YAML dumper used to serialize command's outputs.
_Y = None


def _get_yamel():
    global _Y

    if not _Y:
        from ruamel import yaml
        from ruamel.yaml.representer import RoundTripRepresenter

        for d in [OrderedDict, defaultdict]:
            RoundTripRepresenter.add_representer(
                d, RoundTripRepresenter.represent_dict)
        _Y = yaml.YAML()

    return _Y


def ydumps(obj):
    "Dump any false objects as empty string, None as nothing, or as YAML. "

    if obj is None:
        return
    if not obj:
        return ''

    sio = io.StringIO()
    _get_yamel().dump(obj, sio)
    return sio.getvalue().strip()


def yloads(text):
    "Dump any false objects as empty string, None as nothing, or as YAML. "

    if not text:
        return

    return _get_yamel().load(text)


def merge_dict(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None

    Adapted from: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    """
    for k in merge_dct.keys():
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], Mapping)):
            merge_dict(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


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

    _git_root: Path = None

    @property
    def git_root(self) -> Path:
        if self._git_root is None:
            self._git_root = fu.find_git_root()

            if not self._git_root:
                raise pvtags.NoGitRepoError(
                    "Current-dir '%s' is not inside a git-repo!" %
                    Path().resolve())

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
        - Screams if discovered samek project-name with conflicting basepaths.
        """)

    def _autodiscover_project_basepaths(self) -> Dict[str, Path]:
        """
        Invoked when no config exists (or asked to updated it) to guess projects.

        :return:
            a mapping of {pnames: basepaths}
        """
        file_hits = self.projects_scan.scan_hits(mybase=self.git_root)

        project_paths = {
            (fspec.grafts[0].hits[0].groupdict()['pname'], fpath.parent)
            for fpath, fspec in file_hits.items()
            if fspec.nhits == 1}

        ## check basepath conflicts.
        #
        projects: Dict[str, Path] = {}
        dupe_projects: Dict[str, Set[Path]] = defaultdict(set)
        for pname, basepath in project_paths:
            dupe_basepath = projects.get(pname)
            if dupe_basepath and dupe_basepath != basepath:
                dupe_projects[pname].add(basepath)
            else:
                projects[pname] = basepath

        if dupe_projects:
            raise cmdlets.CmdException(
                "Discovered conflicting project-basepaths: %s" %
                ydumps(dupe_basepath))

        return projects

    def _autodiscover_versioning_scheme(self):
        """
        Guess whether *monorepo* or *mono-project* versioning schema applies.

        :return:
            one of :func:`pvtags.make_vtag_project`, :func:`pvtags.make_pvtag_project`
        """
        pvtag_proj, vtag_proj = pvtags.collect_standard_versioning_tags(parent=self)

        if bool(pvtag_proj.pvtags_history) ^ bool(vtag_proj.pvtags_history):
            return (pvtags.make_pvtag_project(parent=self)
                    if pvtag_proj.pvtags_history else
                    pvtags.make_vtag_project(parent=self))
        else:
            raise cmdlets.CmdException(
                "Cannot auto-discover versioning scheme, "
                "missing or contradictive versioning-tags:\n%s"
                "\n\n  Try --monorepo/--mono-project flags." %
                ydumps({'pvtags': pvtag_proj.pvtags_history,
                        'vtags': vtag_proj.pvtags_history}))

    def bootstrapp_projects(self) -> None:
        """
        Ensure valid configuration exist for monorepo/mono-project(s).

        :raise CmdException:
            if cwd not inside a git repo
        """
        git_root = self.git_root

        template_project = pvtags.Project(parent=self)
        has_template_project = (template_project.tag_vprefixes and
                                template_project.pvtag_frmt and
                                template_project.pvtag_regex)

        if not has_template_project:
            template_project = self._autodiscover_versioning_scheme()
            log.info("Auto-discovered versioning scheme: %s",
                     template_project.pname)

        has_subprojects = bool(self.projects)
        if not has_subprojects:
            proj_paths: Dict[str, Path] = self._autodiscover_project_basepaths()
            if not proj_paths:
                raise cmdlets.CmdException(
                    "Cannot auto-discover (sub-)project path(s)!"
                    "\n  Please use `ìnit` cmd to specify sub-projects explicitly.")

            log.info(
                "Auto-discovered %i sub-project(s) in git-root '%s': \n%s",
                len(proj_paths), git_root.resolve(),
                ydumps({k: str(v) for k, v in proj_paths.items()}))

            self.projects = [template_project.replace(pname=name,
                                                      basepath=basepath,
                                                      _pvtags_collected=None)
                             for name, basepath in proj_paths.items()]

        return self.projects


class _SubCmd(PolyversCmd):
    def __init__(self, *args, **kw):
        self.subcommands = {}
        super().__init__(*args, **kw)


class InitCmd(_SubCmd):
    """Generate configurations based on directory contents."""

    def _find_config_file_path(self, rootapp) -> Path:
        """
        Log if no config-file has been loaded.
        """
        git_root = rootapp.git_root

        for p in self._cfgfiles_registry.collected_paths:
            p = Path(p)
            try:
                if p.relative_to(git_root):
                    return p
            except ValueError as _:
                ## Ignored, probably program defaults.
                pass

    def run(self, *args):
        if len(args) > 0:
            raise cmdlets.CmdException(
                "Cmd %r takes no arguments, received %d: %r!"
                % (self.name, len(args), args))

        self.bootstrapp_projects()
        cfgpath = self._find_config_file_path(self)
        if cfgpath:
            yield "TODO: update config-file '%s'...." % cfgpath
        else:
            cfgpath = Path(self.git_root) / ('%s.yaml' % self.config_basename)
            yield "TODO: create new config-file in '%s'." % cfgpath


_status_all_help = """
    When true, fetch also all version-tags, otherwise just project version-id(s).
"""


class StatusCmd(_SubCmd):
    """
    List the versions of project(s).

    SYNTAX:
        {cmd_chain} [OPTIONS] [<project>]...
    """
    all = Bool(  # noqa: A003
        config=True,
        help=_status_all_help)

    flags = {'all': ({'StatusCmd': {'all': True}}, _status_all_help)}

    def _fetch_versions(self, projects):
        def git_describe(proj):
            try:
                return proj.git_describe()
            except pvtags.GitVoidError as _:
                return None

        versions = {p.pname: {'version': git_describe(p)}
                    for p in projects}
        return versions

    def _fetch_all(self, projects):
        ## TODO: extract method to classify pre-populated histories.
        pvtags.populate_pvtags_history(*projects)
        ## TODO: YAMLable Project (apart from Printable) with metadata Print/header
        pinfos = {p.pname: {'history': p.pvtags_history,
                            'basepath': str(p.basepath)}
                  for p in projects}
        return pinfos

    def run(self, *pnames):
        projects = self.bootstrapp_projects()

        if pnames:
            projects = [p for p in projects
                        if p.pname in pnames]

        res = self._fetch_versions(projects)

        if self.all:
            merge_dict(res, self._fetch_all(projects))

        if res:
            return ydumps(res)


class BumpCmd(_SubCmd):
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


class LogconfCmd(_SubCmd):
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
        {'Project': {
            'pvtag_frmt': pvlib.pvtag_frmt,
            'pvtag_regex': pvlib.pvtag_regex,
        }},
        "Use *pvtags* for versioning sub-projects in this git monorepo."
    ),
    'mono-project': (
        {'Project': {
            'pvtag_frmt': pvlib.vtag_frmt,
            'pvtag_regex': pvlib.vtag_regex,
        }},
        "Use plain *vtags* for versioning a single project in this git repo."
    ),
}

PolyversCmd.aliases = {  # type: ignore
    ('m', 'message'): 'Project.message',
    ('u', 'sign-user'): 'Project.sign_user',
    ('f', 'force'): 'Spec.force',
}
