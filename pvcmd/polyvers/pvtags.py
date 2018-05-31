#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Git code to make/inspect sub-project "(p)vtags" and respective commits in (mono)repos.

There are 3 important methods/functions calling Git:

- :meth:`Project.git_describe()` that fetches the same version-id
  that :func:`polyversion.polyversion()` would return, but with more options.
- :meth:`Project.last_commit_tstamp()`, same as above.
- :func:`populate_pvtags_history()` that populates *pvtags* on the given
  project instances; certain pvtag-related Project methods would fail if
  this function has not been applies on a project instance.
"""

from typing import List, Dict, Sequence, Optional
import contextlib
import logging

import polyversion as pvlib
import subprocess as sbp

from . import pvproject
from .cmdlet import cmdlets
from .utils.oscmd import cmd, PopenCmd


MONOREPO = '<monorepo>'
MONO_PROJECT = '<mono-project>'


log = logging.getLogger(__name__)


class GitError(cmdlets.CmdException):
    "A (maybe benign) git-related error"
    pass


class GitVoidError(GitError):
    "Sub-project has not yet been version with a *pvtag*. "
    pass


class NoGitRepoError(GitError):
    "Command needs a git repo in CWD. "
    pass


@contextlib.contextmanager
def git_project_errors_handled(pname):
    """Report `pname` involved to the user in case tags are missing."""
    try:
        yield
    except sbp.CalledProcessError as ex:
        err = ex.stderr
        if any(msg in err
               for msg in [
                   "does not have any commits yet",
                   "No names found",
                   "No annotated tags",
                   "No tags can describe"]):
            raise GitVoidError("Project '%s': %s" % (pname, err)) from ex
        raise


def _git_current_branch() -> Optional[str]:
    CUR_BRANCH_PREFIX = '* '

    branches = cmd.git.branch()
    for br_line in branches.split('\n'):
        if br_line.startswith(CUR_BRANCH_PREFIX):
            cur_branch = br_line.lstrip(CUR_BRANCH_PREFIX)

            return cur_branch


def _parse_ref_pairs_list(reflines: str) -> Dict[str, str]:
    "parses the output of ``git show-ref`` as a dict"
    return {ref: sha
            for sha, ref in (l.split()
                             for l in reflines.split('\n'))}


def _restore_refs(old_refs: Dict[str, str], new_refs: Dict[str, str]):
    ## See https://git-scm.com/docs/git-update-ref
    to_del = new_refs.keys() - old_refs.keys()
    to_add = old_refs.keys() - new_refs.keys()
    to_upd = old_refs.keys() & new_refs.keys()

    cmd_lines = ['delete %s %s' % (ref, new_refs[ref])
                 for ref in to_del]
    cmd_lines.extend('create %s %s' % (ref, old_refs[ref])
                     for ref in to_add)
    cmd_lines.extend('update %s %s %s' % (ref, old_refs[ref], new_refs[ref])
                     for ref in to_upd
                     if old_refs[ref] != new_refs[ref])
    if cmd_lines:
        cmd_text = '\n'.join(cmd_lines) + '\n'
        log.debug("Restoring git-refs: \n%s" % cmd_text)
        PopenCmd(input=cmd_text.encode(),
                 universal_newlines=False,
                 encoding=None, encoding_errors=None
                 ).git.update_ref(stdin=True)


@contextlib.contextmanager
def git_restore_point(restore_head=False, heads=True, tags=True):
    """
    Restored checked out branch to previous state in case of errors (or if forced).

    :param restore:
        if true, force restore at exit, otherwise, restore only on errors
    """
    show_ref_kw = {'heads': heads or None, 'tags': tags or None}

    cur_branch = _git_current_branch()
    original_commit_id = cmd.git.rev_parse.HEAD()
    if heads or tags:
        old_refs = _parse_ref_pairs_list(cmd.git.show_ref(**show_ref_kw))
    ok = False
    try:
        yield
        ok = True
    finally:
        if not ok or restore_head:
            if cur_branch:
                cmd.git.checkout(cur_branch, force=True)
            cmd.git.reset._(hard=True)(original_commit_id)
            if heads or tags:
                new_refs = _parse_ref_pairs_list(cmd.git.show_ref(**show_ref_kw))
                _restore_refs(old_refs, new_refs)


def make_pvtag_project(pname: str = MONOREPO,
                       **project_kw) -> pvproject.Project:
    """
    Make a :class:`Project` for a subprojects hosted at git monorepos.

    - Project versioned with *pvtags* like ``foo-project-v0.1.0``.
    """
    return pvproject.Project(
        pname=pname,
        tag_vprefixes=pvlib.tag_vprefixes,
        pvtag_format=pvlib.pvtag_format,
        pvtag_regex=pvlib.pvtag_regex,
        **project_kw)


def make_match_all_pvtags_project(**project_kw) -> pvproject.Project:
    """
    Make a :class:`Project` capturing any *pvtag*.

    Useful as a "catch-all" last project in :func:`populate_pvtags_history()`,
    to capture *pvtags* not captured by any other project.
    """
    # Note: `pname` ignored by patterns, used only for labeling.
    return pvproject.Project(
        pname='<PVTAG>',
        tag_vprefixes=pvlib.tag_vprefixes,
        pvtag_format='*-v*',
        pvtag_regex=r"""(?xmi)
            ^(?P<pname>[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9])
            -
            v(?P<version>\d[^-]*)
            (?:-(?P<descid>\d+-g[a-f\d]+))?$
        """,
        **project_kw)


def make_vtag_project(pname: str = MONO_PROJECT,
                      **project_kw) -> pvproject.Project:
    """
    Make a :class:`Project` for a single project hosted at git repos root (not "monorepos").

    - Project versioned with tags simple *vtags* (not *pvtags*) like ``v0.1.0``.
    """
    simple_project = pvproject.Project(
        pname=pname,
        tag_vprefixes=pvlib.tag_vprefixes,
        pvtag_format=pvlib.vtag_format,
        pvtag_regex=pvlib.vtag_regex,
        **project_kw)

    return simple_project


def make_match_all_vtags_project(**project_kw) -> pvproject.Project:
    """
    Make a :class:`Project` capturing any simple *vtag* (e.g. ``v0.1.0``).

    Useful as a "catch-all" last project in :func:`populate_pvtags_history()`,
    to capture *vtags* not captured by any other project.
    """
    # Note: `pname` ignored by patterns, used only for labeling.
    return make_vtag_project(pname='<VTAG>',
                             **project_kw)


def _fetch_all_tags(tag_patterns: List[str],
                    pnames_msg: str):
    with git_project_errors_handled(pnames_msg):
        out = cmd.git.tag._(sort='-taggerdate')('--list', *tag_patterns)

    return out and out.split('\n') or ()


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


def _fetch_annotated_tags(tag_patterns: Sequence[str],
                          pnames_msg: str) -> List[str]:
    """
    Collect only non-annotated tags (those pointing to tag-objects).

    From https://stackoverflow.com/a/21032332/548792
    """
    tag_patterns = ['refs/tags/' + pat for pat in tag_patterns]
    with git_project_errors_handled(pnames_msg):
        out = cmd.git.for_each_ref(*tag_patterns,
                                   format='%(objecttype) %(refname:short)',
                                   sort='-taggerdate')

    if not out:
        return []

    tag_ref_lines = out.split('\n')
    tags = _parse_git_tag_ref_lines(tag_ref_lines)

    return tags


def _replace_pvtags_in_projects(
        projects: List[pvproject.Project],
        pvtags_by_pname: Dict[str, List[str]]) -> List[pvproject.Project]:
    "Merge the 2 inputs in a list of cloned Projects with their pvtags replaced."
    cloned_projects = [proj.replace(
        _pvtags_collected=pvtags_by_pname[proj.pname]) for proj in projects]

    return cloned_projects


def populate_pvtags_history(*projects: pvproject.Project,
                            include_lightweight=False,
                            is_release=False):
    """
    Updates :attr:`pvtags_history` on given `projects` (if any) in ascending order.

    :param projects:
        the projects to search *pvtags* for
    :param include_lightweight:
        fetch also non annotated tags; note that by default, ``git-describe``
        does consider lightweight tags unless ``--tags`` given.
    :param is_release:
        `False` for version-tags, `True` for release-tags
    :raise sbp.CalledProcessError:
        if `git` executable not in PATH

    .. Note::
       Internally, *pvtags* are populated in :attr:`_pvtags_collected` which
       by default it is ``None``.  After this call, it will be a (possibly empty)
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
            tag_patterns.append(proj.tag_fnmatch(is_release))

    pnames_msg = ', '.join(p.pname for p in projects)
    if include_lightweight:
        tags = _fetch_all_tags(tag_patterns, pnames_msg)
    else:
        tags = _fetch_annotated_tags(tag_patterns, pnames_msg)

    for proj in projects:
        proj._pvtags_collected = []

    assign_tags_to_projects(tags, projects)


def assign_tags_to_projects(tags: Sequence[str],
                            projects: Sequence[pvproject.Project]):
    for pvtag in tags:
        ## Attempt all projects to parse tags.
        # and assign it to the 1st one to manage it.
        #
        for proj in projects:
            version = proj.version_from_pvtag(pvtag)
            if version:
                proj._pvtags_collected.append(pvtag)
                break
