#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Make/inspect sub-project "pvtags" and respective commits in Git monorepos.

There are 3 important methods/functions calling Git:
- :method:`Project.git_describe()` that fetches the same version-id
  that :func:`polyversion.polyversion()` would return, but with more options.
- :method:`Project.last_commit_tstamp()`, same as above.
- :func:`populate_pvtags_history()` that populates *pvtags* on the given
  project instances; certain pvtag-related Project methods would fail if
  this function has not been applies on a project instance.
"""

import contextlib
import glob
import logging
import os
from pathlib import Path
import re
from typing import List, Dict, Optional

import subprocess as sbp

from . import polyverslib as pvlib, cmdlets, interpctxt
from ._vendor.traitlets import traitlets as trt
from ._vendor.traitlets.traitlets import Bool, Unicode, Instance, \
    List as ListTrait  # @UnresolvedImport
from .oscmd import cmd


log = logging.getLogger(__name__)


class GitVoidError(cmdlets.CmdException):
    "Sub-project has not yet been version with a *pvtag*. "
    pass


class NoGitRepoError(cmdlets.CmdException):
    "Command needs a git repo in CWD. "
    pass


@contextlib.contextmanager
def _git_errors_handler(pname):
    try:
        yield
    except sbp.CalledProcessError as ex:
        err = ex.stderr
        if any(msg in err
               for msg in [
                   "does not have any commits yet",
                   "No names found",
                   "No annotated tags"]):
            raise GitVoidError("Project '%s': %s" % (pname, err)) from ex

        elif "Not a git repository" in err:
            raise NoGitRepoError(
                "Current-dir '%s' is not within a git repository!" %
                os.curdir) from ex
        else:
            raise


class _EscapedObjectDict(interpctxt._HasTraitObjectDict):
    def __init__(self, _obj: trt.HasTraits, escape_func) -> None:
        super().__init__(_obj)
        self._escape_func = escape_func

    def __getitem__(self, key):
        if self._obj.has_trait(key):
            v = getattr(self._obj, key)
            if isinstance(v, str):
                v = self._escape_func(v)

            return v
        else:
            raise KeyError(key)


class Project(cmdlets.Spec, cmdlets.Replaceable):
    pname = Unicode()
    basepath = Instance(Path, default_value=None, allow_none=True, castable=str)

    pvtag_frmt = Unicode(
        help="""
        The pattern to generate new *pvtags*.

        It is interpolated with this class's traits as :pep:`3101` parameters;
        among others ``{pname}`` and ``{version}``; use ``{ikeys}`` to receive
        all available keys.

        .. WARNING::
           If you change this, ensure the :func:`polyversion.polyversion()`
           gets invoked from project's sources with the same value
           in `pvtag_frmt` kw-arg.
    """).tag(config=True)

    @trt.default('pvtag_frmt')
    def _pvtag_frmt_from_root(self):
        default_project = getattr(self.root(), 'default_project', None)
        if default_project and default_project is not self:
            return default_project.pvtag_frmt
        return ''

    @property
    def pvtag_fnmatch_frmt(self):
        """
        The glob-pattern finding *pvtags* with ``git describe --match <pattern>`` cmd.

        By default, it is interpolated with two :pep:`3101` parameters::

            {pname}   <-- this Project.pname
            {version} <-- '*'
        """
        with self.interpolations.ikeys(_EscapedObjectDict(self, glob.escape),
                                       version='*') as ictxt:
            pvtag_fnmatch_frmt = self.pvtag_frmt.format_map(ictxt)
        return pvtag_fnmatch_frmt

    pvtag_regex = Unicode(
        help="""
        The regex pattern breaking *pvtags* and/or ``git-describe`` output
        into 3 named capturing groups:
        - ``pname``,
        - ``version`` (without the 'v'),
        - ``descid`` (optional) anything following the dash('-') after
          the version in ``git-describe`` result.

        It is interpolated with this class's traits as :pep:`3101` parameters;
        among others ``{pname}``, and **maybe** ``{version}``; use ``{ikeys}``
        to receive all available keys.
        See :pep:`0426` for project-name characters and format.

        .. WARNING::
           If you change this, ensure the :func:`polyversion.polyversion()`
           gets invoked from project's sources with the same value
           in `pvtag_regex` kw-arg.
    """).tag(config=True)

    @trt.validate('pvtag_regex')
    def _is_valid_pvtag_regex(self, proposal):
        value = proposal.value
        try:
            re.compile(value.format(pname='pname'))
        except Exception as ex:
            proposal.trait.error(None, value, ex)
        return value

    @trt.default('pvtag_regex')
    def _pvtag_regex_from_root(self):
        default_project = getattr(self.root(), 'default_project', None)
        if default_project and default_project is not self:
            return default_project.pvtag_regex
        return ''

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

    message = Unicode(
        "chore(ver): bump {{current_version}} → {{new_version}}",
        config=True,
        help="""
            The message for commits and per-project tags.

            Available interpolations (apart from env-vars prefixed with '$'):
            {ikeys}
        """)

    @property
    def _pvtag_regex_resolved(self):
        "Interpolate and compile as regex."
        with self.interpolations.ikeys(
                _EscapedObjectDict(self, re.escape)) as ictxt:
            pvtag_regex = re.compile(self.pvtag_regex.format_map(ictxt))
        return pvtag_regex

    _pvtags_collected = ListTrait(
        Unicode(), allow_none=True, default_value=None,
        help="Populated internally by `populate_pvtags_history()`.")

    @property
    def pvtags_history(self) -> List[str]:
        """
        Return the full *pvtag* history for the project, if any.

        :raise AssertionError:
           If used before :func:`populate_pvtags_history()` applied on this project.
        """
        if self._pvtags_collected is None:
            raise AssertionError("Call first `populate_pvtags_history()` on %s!")
        return self._pvtags_collected

    def version_from_pvtag(self, pvtag: str) -> Optional[str]:
        """Extract the version from a *pvtag*."""
        m = self._pvtag_regex_resolved.match(pvtag)
        if m:
            mg = m.groupdict()
            if mg['descid']:
                log.warning(
                    "Ignoring pvtag '%s', it has `git-describe` suffix '%s'!",
                    pvtag, mg['descid'])

            return mg['version']

    def git_describe(self, *git_args: str,
                     include_lightweight=False,
                     **git_flags: str):
        """
        Gets sub-project's version as derived from ``git describe`` on its *pvtag*.

        :param include_lightweight:
            Consider also non-annotated tags when derriving description;
            equivalent to ``git describe --tags`` flag.
        :param git_args:
            CLI options passed to ``git describe`` command.
            See :class:`.oscmd.PopenCmd` on how to specify cli options
            using python functions, e.g. ``('*-v*', '*-r*')``
        :param git_flags:
            CLI flags passed to ``git describe`` command.
            - See :class:`.oscmd.PopenCmd` on how to specify cli flags
              using python functions, e.g. ``(all=True)``.
            - See https://git-scm.com/docs/git-describe
        :return:
            the *pvtag* of the current project, or raise
        :raise GitVoidError:
            if sub-project is not *pvtagged*.
        :raise NoGitRepoError:
            if CWD not within a git repo.
        :raise sbp.CalledProcessError:
            for any other error while executing *git*.

        .. NOTE::
           There is also the python==2.7 & python<3.6 safe :func:`polyvers.polyversion()``
           for extracting just the version part from a *pvtag*; use this one
           from within project sources.

        .. INFO::
           Same results can be retrieved by this `git` command::

               git describe --tags --match <PROJECT>-v*

           where ``--tags`` is needed to consider also non-annotated tags,
           as ``git tag`` does.
        """
        pname = self.pname
        tag_pattern = self.pvtag_fnmatch_frmt

        cli = cmd.git.describe
        if include_lightweight:
            cli._(tags=True)

        with _git_errors_handler(pname):
            out = cli._(*git_args, **git_flags)(match=tag_pattern)

        return out and out.strip()

    def last_commit_tstamp(self):
        """
        Report the timestamp of the last commit of the git repo.

        :return:
            last commit's timestamp in :rfc:`2822` format

        :raise GitVoidError:
            if there arn't any commits yet or CWD not within a git repo.
        :raise sbp.CalledProcessError:
            for any other error while executing *git*.

        .. INFO::
           Same results can be retrieved by this `git` command::

               git describe --tags --match <PROJECT>-v*

           where ``--tags`` is needed to consider also unannotated tags,
           as ``git tag`` does.
        """
        with _git_errors_handler(self.pname):
            out = cmd.git.log(n=1, format='format:%cD')  # TODO: traitize log-date format

        return out and out.strip()


def make_pvtag_project(**project_kw) -> Project:
    """
    Make a :class:`Project` for a subprojects hosted at git monorepos.

    - Project versioned with *pvtags* like ``foo-project-v0.1.0``.
    - Used as a template for :attr:`PolyversCmd.default_project`.
    """
    return Project(
        pvtag_frmt=pvlib.pvtag_frmt,
        pvtag_regex=pvlib.pvtag_regex,
        **project_kw)


def make_match_all_pvtags_project(**project_kw) -> Project:
    """
    Make a :class:`Project` capturing any *pvtag*.

    Useful as a "catch-all" last project in :func:`populate_pvtags_history()`,
    to capture *pvtags* not captured by any other project.
    """
    # Note: `pname` ignored by patterns, used only for labeling.
    return Project(
        pname='*',
        pvtag_frmt='*-v*',
        pvtag_regex=r"""(?xi)
            ^(?P<pname>[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9])
            -
            v(?P<version>\d[^-]*)
            (?:-(?P<descid>\d+-g[a-f\d]+))?$
        """,
        **project_kw)


def make_vtag_project(**project_kw) -> Project:
    """
    Make a :class:`Project` for a single project hosted at git repos root (not "monorepos").

    - Project versioned with tags simple *vtags* (not *pvtags*) like ``v0.1.0``.
    - Used as a template for :attr:`PolyversCmd.default_project`.
    """
    simple_project = Project(
        pvtag_frmt=pvlib.vtag_frmt,
        pvtag_regex=pvlib.vtag_regex,
        **project_kw)

    return simple_project


def make_match_all_vtags_project(**project_kw) -> Project:
    """
    Make a :class:`Project` capturing any simple *vtag* (e.g. ``v0.1.0``).

    Useful as a "catch-all" last project in :func:`populate_pvtags_history()`,
    to capture *vtags* not captured by any other project.
    """
    # Note: `pname` ignored by patterns, used only for labeling.
    return make_vtag_project(pname='*',
                             **project_kw)


def _fetch_all_tags(cli, tag_patterns: List[str],
                    pnames_msg: str):
    cli.tag

    with _git_errors_handler(pnames_msg):
        out = cli('--list', *tag_patterns)

    return out and out.strip().split('\n') or ()


def _parse_git_tag_ref_lines(tag_ref_lines: List[str],
                             keep_lightweight=False) -> List[str]:
    """
    :param keep_lightweight:
        if true, keep also lightweight tags
    """
    tag_specs = [t.split() for t in tag_ref_lines]
    if keep_lightweight:
        tags = [t[1] for t in tag_specs]
    else:
        tags = [t[1] for t in tag_specs if t[0] == 'tag']

    return tags


def _fetch_annotated_tags(cli, tag_patterns: List[str],
                          pnames_msg: str) -> List[str]:
    """
    Collect only non-annotated tags (those pointing to tag-objects).

    From https://stackoverflow.com/a/21032332/548792
    """
    cli.for_each_ref._('refs/tags/', format='%(objecttype) %(refname:short)')
    with _git_errors_handler(pnames_msg):
        out = cli(*tag_patterns)

    tag_ref_lines = out and out.strip().split('\n')
    tags = _parse_git_tag_ref_lines(tag_ref_lines)

    return tags or []


def _replace_pvtags_in_projects(
        projects: List[Project],
        pvtags_by_pname: Dict[str, List[str]]) -> List[Project]:
    "Merge the 2 inputs in a list of cloned Projects with their pvtags replaced."
    cloned_projects = [proj.replace(
        _pvtags_collected=pvtags_by_pname[proj.pname]) for proj in projects]

    return cloned_projects


def populate_pvtags_history(*projects: Project,
                            include_lightweight=False):
    """
    Updates :attr:`pvtags_history` on given `projects` (if any) in ascending order.

    :param projects:
        the projects to search *pvtags* for
    :param include_lightweight:
        fetch also non annotated tags; note that by default, ``git-describe``
        does consider lightweight tags unless ``--tags`` given.
    :raise sbp.CalledProcessError:
        if `git` executable not in PATH

    .. Info::
       Internally, *pvtags* are populated in :attr:`_pvtags_collected` which
       by default it is ``None`.  After this call, it will be a (possibly empty)
       list.  Any pre-existing *pvtags* are removed from all projects
       before collecting them anew.

    .. Tip::
       To collect all *pvtags* OR *vtags* only, use pre-defined projects
       generated by ``make_project_matching_*()`` functions.
    """
    if not projects:
        return []

    tag_patterns = []
    for proj in projects:
        with proj.interpolations.ikeys(pname=proj.pname):
            tag_patterns.append(proj.pvtag_fnmatch_frmt)

    pnames_msg = ', '.join(p.pname for p in projects)
    cli = cmd.git
    if include_lightweight:
        tags = _fetch_all_tags(cli, tag_patterns, pnames_msg)
    else:
        tags = _fetch_annotated_tags(cli, tag_patterns, pnames_msg)

    for proj in projects:
        proj._pvtags_collected = []

    for pvtag in tags:
        ## Attempt all projects to parse tags.
        # and assign it to the 1st one to manage it.
        #
        for proj in projects:
            version = proj.version_from_pvtag(pvtag)
            if version:
                proj._pvtags_collected.append(pvtag)
                break
