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
from typing import Dict
from typing import Tuple, Set, List, Optional  # noqa: F401 @UnusedImport, flake8 blind in funcs
import logging

from boltons.setutils import IndexedSet as iset

import os.path as osp
import polyversion as pvlib
import textwrap as tw

from . import APPNAME, __version__, __updated__, pvtags, pvproject
from ._vendor import traitlets as trt
from ._vendor.traitlets import config as trc
from ._vendor.traitlets.traitlets import (
    List as ListTrait, Tuple as TupleTrait, Dict as DictTrait)
from ._vendor.traitlets.traitlets import Bool, Unicode
from .cmdlet import cmdlets, autotrait
from .utils import fileutil as fu, yamlutil as yu


log = logging.getLogger(__name__)


####################
## Config sources ##
####################
CONFIG_VAR_NAME = '%s_CONFIG_PATHS' % APPNAME.upper()
#######################


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


class PolyversCmd(cmdlets.Cmd, yu.YAMLable):
    """
    Bump independently PEP-440 versions of sub-project in Git monorepos.

    SYNTAX:
      {cmd_chain} <sub-cmd> ...
    """
    version = __version__  # type: ignore  # mypy complains with engraved value??g.
    examples = Unicode("""
        - Let it guess the configurations for your monorepo::
              {cmd_chain} init
          You may specify different configurations paths with::
              {cmd_chain} --config-paths /foo/bar/:~/{config_basename}.yaml:.

        - Use then the main sub-commands::
              {cmd_chain} init    # (optional) use it once, or to update configs.
              {cmd_chain} status
              {cmd_chain} bump 0.0.1.dev0 -c '1st commit, untagged'
              {cmd_chain} bump -t 'Mostly model changes, tagged'
    """)
    classes = [pvproject.Project]

    projects = ListTrait(
        autotrait.AutoInstance(pvproject.Project),
        config=True)

    @trt.default('subcommands')
    def _subcommands(self):
        subcmds = OrderedDict()
        subcmds['bump'] = ('polyvers.bumpcmd.BumpCmd',
                           "Increase or set (sub-)project version(s).")
        subcmds.update(cmdlets.build_sub_cmds(InitCmd, StatusCmd, LogconfCmd))
        subcmds['config'] = (
            'polyvers.cmdlet.cfgcmd.ConfigCmd',
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
        from . import bumpcmd
        return [type(self),
                pvproject.Project,
                InitCmd, StatusCmd, bumpcmd.BumpCmd, LogconfCmd,
                pvproject.Engrave, pvproject.Graft,
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

    curdir = Unicode(
        config=True,
        help="Work as if changed in the given current-dir.")

    @trc.catch_config_error
    def parse_command_line(self, argv=None):
        super().parse_command_line.__wrapped__(self, argv)  # not to re-catch_config_error

        ## Chdir as soon as possible.
        #
        if self.curdir:
            self.log.info('Switching to dir: %s', self.curdir)
            import os
            try:
                os.chdir(self.curdir)
            except Exception as ex:
                raise cmdlets.CmdException(
                    "Cannot switch to dir '%s' due to: %s" %
                    (self.curdir, ex)) from ex

    _git_root: Optional[Path] = None

    @property
    def git_root(self) -> Path:
        if self._git_root is None:
            self._git_root = fu.find_git_root()

            if not self._git_root:
                raise pvtags.NoGitRepoError(
                    "Current-dir '%s' is not inside a git-repo!" %
                    Path().resolve())

        return self._git_root

    pdata = DictTrait(
        key_trait=Unicode(),
        value_trait=Unicode(),
        config=True,
        help="""
        Pairs of (pname: basepath) for the projects in the repo.

        - This param exists only when specifying those data from cmdline; otherwise,
          in configuration files prefer to specify directly `PolyversCmd.projects`.
        - example:: --pdata foo=foo/fpath
        """)

    autodiscover_subproject_projects = ListTrait(
        autotrait.AutoInstance(pvproject.Project),
        default_value=[{
            'engraves': [{
                'globs': ['**/setup.py'],
                'grafts': [{
                    'regex': tw.dedent(r'''
                        (?xm)
                            \b(name|PROJECT|APPNAME|APPLICATION)
                            \ *=\ *
                            (['"])
                                (?P<pname>[\w\-.]+)
                            \2
                    '''),
                    'slices': -1
                }]
            }]
        }],
        allow_none=True,
        config=True,
        help="""
        Projects with globs/regexes that can autodiscover sub-project basepaths/names.

        - Needed when no configuration file is given (or has partial infos).
        - The glob-patterns contained in this `Project[Engrave[Graft]]`
          should match files in the root dir of auto-discovered-projects
          (`Graft.subst` is not used here).
        - `Project.basepath` must denote the project-root relative to the globbed
           file's dir ('.' assumed).
        - Project name(s) must be captured by the `Graft`.
          If none (or different ones) match, project detection fails.
        - A Project is identified only if file(s) are globbed AND regexp(s) matched.
        - User should fallback to --data if it fails.
        """)

    autodiscover_version_scheme_projects = TupleTrait(
        autotrait.AutoInstance(pvproject.Project), autotrait.AutoInstance(pvproject.Project),
        default_value=({
            'pname': '<PVTAG>',
            'tag_vprefixes': pvlib.tag_vprefixes,
            'pvtag_frmt': '*-v*',
            'pvtag_regex': tw.dedent(r"""
                (?xmi)
                    ^(?P<pname>[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9])
                    -
                    v(?P<version>\d[^-]*)
                    (?:-(?P<descid>\d+-g[a-f\d]+))?$
            """)}, {
            'pname': '<VTAG>',
            'tag_vprefixes': pvlib.tag_vprefixes,
            'pvtag_frmt': pvlib.vtag_frmt,
            'pvtag_regex': pvlib.vtag_regex,
        }),
        config=True,
        help="""
        A pair of Projects with patterns/regexps matching *pvtags* or *vtags*, respectively.

        - Needed when a) no configuration file is given (or has partial infos),
          and b) when constructing/updating the configuration file.
        - Screams if discovered same project-name with conflicting basepaths.
        """)

    def _autodiscover_project_basepaths(self) -> Dict[str, Path]:
        """
        Invoked when no config exists (or asked to updated it) to guess projects.

        :return:
            a mapping of {pnames: basepaths}
        """
        from . import engrave

        if not self.autodiscover_subproject_projects:
            raise cmdlets.CmdException(
                "No `Polyvers.autodiscover_subproject_projects` param given!")

        fproc = engrave.FileProcessor(parent=self)
        with self.errlogged(doing='discovering project paths',
                            info_log=self.log.info):
            scan_projects = self.autodiscover_subproject_projects
            #: Dict[Path,
            #: List[Tuple[pvproject.Project, Engrave, Graft, List[Match]]]]
            match_map = fproc.scan_projects(scan_projects)

        ## Accept projects only if one, and only one,
        #  pair (pname <--> path) matched.
        #
        pname_path_pairs: List[Tuple[str, Path]] = [
            (m.groupdict()['pname'].decode('utf-8'),
             fpath.parent / (prj.basepath or '.'))
            for fpath, mqruples in match_map.items()
            for prj, _eng, _graft, matches in mqruples
            for m in matches]
        unique_pname_paths = iset(pname_path_pairs)

        ## check basepath conflicts.
        #
        projects: Dict[str, Path] = {}
        dupe_projects: Dict[str, Set[Path]] = defaultdict(set)
        for pname, basepath in unique_pname_paths:
            dupe_basepath = projects.get(pname)
            if dupe_basepath and dupe_basepath != basepath:
                dupe_projects[pname].add(basepath)
            else:
                projects[pname] = basepath

        if dupe_projects:
            raise cmdlets.CmdException(
                "Discovered conflicting project-basepaths: %s" %
                yu.ydumps(dupe_basepath))

        return projects

    def _autodiscover_versioning_scheme(self):
        """
        Guess whether *monorepo* or *mono-project* versioning schema applies.

        :return:
            one of :func:`pvtags.make_vtag_project`, :func:`pvtags.make_pvtag_project`
        """
        pvtag_proj, vtag_proj = self.autodiscover_version_scheme_projects
        pvtags.populate_pvtags_history(pvtag_proj, vtag_proj)

        if bool(pvtag_proj.pvtags_history) ^ bool(vtag_proj.pvtags_history):
            return (pvtags.make_pvtag_project(parent=self)
                    if pvtag_proj.pvtags_history else
                    pvtags.make_vtag_project(parent=self))
        else:
            raise cmdlets.CmdException(
                "Cannot auto-discover versioning scheme, "
                "missing or contradictive versioning-tags:\n%s"
                "\n\n  Try --monorepo/--mono-project flags." %
                yu.ydumps({'pvtags': pvtag_proj.pvtags_history,
                          'vtags': vtag_proj.pvtags_history}))

    def bootstrapp_projects(self) -> None:
        """
        Ensure valid configuration exist for monorepo/mono-project(s).

        :raise CmdException:
            if cwd not inside a git repo
        """
        git_root = self.git_root

        template_project = pvproject.Project(parent=self)
        has_template_project = template_project.is_good()

        if not has_template_project:
            template_project = self._autodiscover_versioning_scheme()
            self.log.info("Auto-discovered versioning scheme: %s",
                          template_project.pname)

        ## Store template-project for InitCmd.
        self._template_project = template_project

        has_subprojects = bool(self.projects)
        if not has_subprojects:
            pdata: Dict[str, Path] = {pname: Path(basepath)
                                      for pname, basepath in self.pdata.items()}

            if not pdata:
                pdata = self._autodiscover_project_basepaths()

                if not pdata:
                    raise cmdlets.CmdException(
                        "Cannot auto-discover (sub-)project path(s)!"
                        "\n  Please use `--pdata <pname>=<basepath> ...` "
                        "to specify sub-project(s) explicitly.")

                self.log.info(
                    "Auto-discovered %i sub-project(s) in git-root '%s': \n%s",
                    len(pdata), git_root.resolve(),
                    yu.ydumps({k: str(v) for k, v in pdata.items()}))

            self.projects = [template_project.replace(pname=pname,
                                                      basepath=basepath,
                                                      _pvtags_collected=None)
                             for pname, basepath in pdata.items()]
            ## Set discovered projects in `config` for InitCmd.
            self.config.PolyversCmd.projects = [
                {'pname': pname, 'basepath': basepath}
                for pname, basepath in pdata.items()]

        if len(self.projects) > 1 and template_project.pname == pvtags.MONO_PROJECT:
            self.log.warning(
                "Incompatible *vtags* version-scheme with %s sub-projects!"
                "\n  You may ether switch to *pvtags* (see `--monorepo`) or "
                "\n  override projects to a single one (see `--pdata`). "
                "\n\n  You can then make the choice permanent using `init` cmd.",
                len(self.projects))
        return self.projects


class _SubCmd(PolyversCmd):
    def __init__(self, *args, **kw):
        self.subcommands = {}
        super().__init__(*args, **kw)


_init_update_help = \
    "Update existing configs, excluding user's home folder and those overriden by cmd-line options"
_init_doc_help = \
    "Include class/param descriptions/defaults in the dumped yaml."


class InitCmd(_SubCmd):
    """Generate configurations based on directory contents."""

    update = Bool(
        config=True,
        help=_init_update_help)

    doc = Bool(
        config=True,
        help=_init_doc_help)

    flags = {  # type: ignore
        ('u', 'update'):
        ({'InitCmd':
          {'update': True}}, _init_update_help),
        'doc': ({'InitCmd': {'doc': True}}, _init_doc_help),
    }

    def _read_non_user_configs(self) -> trc.Config:
        "Avoid writting user-specific configs as project ones."
        config_paths = [p for p in self.config_paths
                        if not p.startswith('~')]
        return self.read_config_files(config_paths)

    @trc.catch_config_error
    def initialize(self, argv=None):
        ## Overridden, to skip configs-loading unless --update given.

        self.update_interp_context()
        self.parse_command_line.__wrapped__(self, argv)  # not to re-catch_config_error

        if self.update:
            config = self._read_non_user_configs()
            config.merge(self.cli_config)

            if self.show_config or self.show_config_json:
                self._dump_config()

            while self:
                self.update_config(config)
                self = self.parent

    def _cleaned_config(self):
        config = self.config
        clean_keys = [
            'InitCmd.update',
            'InitCmd.doc',
            'Spec.*',
            '*.verbose',
            '*.debug',
            '*.dry_run',
            '*.force',
        ]
        for path in clean_keys:
            sec, tname = path.split('.')
            if sec == '*' or sec in config:
                if tname == '*':
                    del config[sec]
                else:
                    sec = config[sec]
                    if tname in sec:
                        del sec[tname]

        return config

    def _make_yaml_config(self) -> trc.Config:
        old_config = self._cleaned_config()
        tproj = self._template_project
        assert tproj and tproj.is_good(), "Bootstrap template: %s" % tproj

        ## Create explicetely `Project` into config,
        #  bc program has does not hold such toplevel class.
        self.config.Project = trc.Config({
            'tag_vprefixes': tproj.tag_vprefixes,
            'pvtag_frmt': tproj.pvtag_frmt,
            'pvtag_regex': tproj.pvtag_regex,
        })

        _t = yu._dump_trait_help.set(self.doc)
        try:
            return self.generate_config_file_yaml(  # type: ignore # meth monkeypatched
                self.all_app_configurables, old_config)
        finally:
            yu._dump_trait_help.reset(_t)

    def run(self, *args):
        if len(args) > 0:
            raise cmdlets.CmdException(
                "Cmd %r takes no arguments, received %d: %r!"
                % (self.name, len(args), args))

        import io

        self.bootstrapp_projects()

        new_config = self._make_yaml_config()

        cfgpath = Path(self.git_root) / ('%s.yaml' % self.config_basename)

        if self.log.isEnabledFor(logging.DEBUG):
            from pprint import pformat
            self.log.debug("Writing config to yaml file '%s': \n%s",
                           cfgpath, pformat(new_config))

        if self.dry_run:
            sink = io.StringIO()
            yu.ydumps(new_config, sink, trait_help=self.doc)
            self.log.warning('PRETEND init: %s' % sink.getvalue())
        else:
            with io.open(cfgpath, 'wt', encoding='utf-8') as fout:
                yu.ydumps(new_config, fout, trait_help=self.doc)

        self.log.notice("Created a %s config-file '%s' for %i projects: %s",
                        self._template_project.pname, cfgpath, len(self.projects),
                        ''.join('\n  - %s: %s' % (p.pname, p.basepath)
                                for p in self.projects))


_status_all_help = """
    When true, fetch also all version-tags, otherwise just project version-id(s).
"""


def _git_desc_without_screams(proj):
    try:
        return proj.git_describe()
    except pvtags.GitVoidError as _:
        return None


class StatusCmd(_SubCmd):
    """
    List the versions of project(s).

    SYNTAX:
        {cmd_chain} [OPTIONS] [<project>]...
    """
    all = Bool(  # noqa: A003
        config=True,
        help=_status_all_help)

    flags = {('a', 'all'): ({'StatusCmd': {'all': True}}, _status_all_help)}  # type: ignore

    def _describe_projects(self, projects):
        return [_git_desc_without_screams(p) or p.pname
                for p in projects]

    def _fetch_all(self, projects):
        ## TODO: YAMLable Project (apart from Printable) with metadata Print/header
        return [{'pname': p.pname,
                 'basepath': str(p.basepath),
                 'gitver': _git_desc_without_screams(p),
                 'history': p.pvtags_history}
                for p in projects]

    def run(self, *pnames):
        projects = self.bootstrapp_projects()

        if pnames:
            ## TODO: use _filter_projects_by_name()
            projects = [p for p in projects
                        if p.pname in pnames]

        ## TODO: extract method to classify pre-populated histories.
        pvtags.populate_pvtags_history(*projects)
        if self.all:
            res = self._fetch_all(projects)
        else:
            res = self._describe_projects(projects)

        if res:
            return yu.ydumps(res)


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

    'monorepo': (
        {'Project': {  # type: ignore
            'pname': pvtags.MONOREPO,
            'pvtag_frmt': pvlib.pvtag_frmt,
            'pvtag_regex': pvlib.pvtag_regex,
        }},
        """
        Select *pvtags* version-scheme, suitable for monorepos hosting multiple sub-projects.
        """
        ## TODO: Conflicting vscheme flags possible!
    ),
    'mono-project': (
        {'Project': {  # type: ignore
            'pname': pvtags.MONO_PROJECT,
            'pvtag_frmt': pvlib.vtag_frmt,
            'pvtag_regex': pvlib.vtag_regex,
        }},
        """
        Select *vtags* version-scheme, suitable for repos hosting a single project.

        - Flag may be required if autodiscovery of version-scheme fails because
          none (or both) vatgs/pvatgs exist in git repo.
        - Use `init` cmd not to give this flag on every command run.
        """
        ## TODO: Conflicting vscheme flags possible!
    ),
}

PolyversCmd.aliases = {  # type: ignore
    ('C', 'curdir'): 'PolyversCmd.curdir',
    ('f', 'force'): 'Spec.force',
    ('p', 'pdata'): 'PolyversCmd.pdata',
}


cmdlets.Spec.force.help += """
Supported tokens:
  'fread'     : don't stop engraving on file-reading errors.
  'fwrite'    : don't stop engraving on file-writting errors.
  'foverwrite': overwrite existing file.
  'glob'      : keep-going even if glob-patterns are invalid.
  'tag'       : replace existing tag.
"""


def run(argv=(), cmd_consumer=None, **app_init_kwds):
    """
    Handle some exceptions politely and return the exit-code.

    :param argv:
        Cmd-line arguments, nothing assumed if nohing given.
    :param cmd_consumer:
        Specify a different main-mup, :class:`mpu.PrintConsumer` by default.
        See :func:`mpu.pump_cmd()`.
    """
    ## At these early stages, any log cmd-line option
    #  enable DEBUG logging ; later will be set by `baseapp` traits.
    from .utils import logconfutils as mlu
    log_level, argv = mlu.log_level_from_argv(
        argv,
        start_level=25,  # 20=INFO, 25=NOTICE (when patched), 30=WARNING
        eliminate_quiet=True)

    log = logging.getLogger('%s.main' % APPNAME)
    logconf_yaml = osp.join('~', '.%s-logconf.yaml' % APPNAME)
    mlu.init_logging(level=log_level, logconf=logconf_yaml)

    ## Imports in separate try-block due to CmdException.
    #
    try:
        from .utils import mainpump as mpu
        from ._vendor.traitlets import TraitError
        from .cmdlet.errlog import CollectedErrors
    except Exception as ex:
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)

    try:
        cmd = PolyversCmd.make_cmd(argv, **app_init_kwds)  # @UndefinedVariable
        return mpu.pump_cmd(cmd.start(), consumer=cmd_consumer) and 0
    except (cmdlets.CmdException, TraitError) as ex:
        log.debug('App exited due to: %r', ex, exc_info=1)
        ## Suppress stack-trace for "expected" errors but exit-code(1).
        msg = str(ex)
        ## Hide some exception-names:
        #    - CmdEx: does not offer anything
        #    - CollectedErrors: msg start with "Collected 2 errors..."
        if type(ex) not in (cmdlets.CmdException, CollectedErrors):
            msg = '%s: %s' % (type(ex).__name__, ex)
        return mlu.exit_with_pride(msg, logger=log)
    except Exception as ex:
        ## Log in DEBUG not to see exception x2, but log it anyway,
        #  in case log has been redirected to a file.
        log.debug('App failed due to: %r', ex, exc_info=1)
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)
