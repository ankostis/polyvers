#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Python code to report sub-project "vtags" in Git *polyvers* monorepos."""

from collections import defaultdict
import logging
import os
from polyvers import oscmd, polyverslib, cmdlets
import re

import subprocess as sbp


vtag_regex = re.compile(r'^([-.\w]+)-v(\d.+)$', re.IGNORECASE)


def find_all_subproject_vtags(*projects):
    """
    Return the all ``proj-v0.0.0``-like tags, per project, if any.

    :param projects:
        project-names; fetch all vtags if none given.
    :return:
        a {proj: [vtags]}, possibly incomplete for projects without any vtag
    :raise subprocess.CalledProcessError:
        if `git` executable not in PATH
    """
    tag_patterns = [polyverslib.vtag_fnmatch_frmt % p
                    for p in projects or ('*', )]
    cmd = 'git tag --merged HEAD -l'.split() + tag_patterns
    res = oscmd.exec_cmd(cmd, check_stdout=True, check_stderr=True)
    out = res.stdout
    tags = out and out.strip().split('\n') or []

    project_versions = defaultdict(list)
    for t in tags:
        m = vtag_regex.match(t)
        if m:
            pname, ver = m.groups()
            project_versions[pname].append(ver)

    return project_versions


def get_subproject_versions(*projects):
    """
    Return the last vtag for any project, if any.

    :param projects:
        project-names; return any versions found if none given.
    :return:
        a {proj: version}, possibly incomplete for projects without any vtag
    :raise subprocess.CalledProcessError:
        if `git` executable not in PATH
    """
    vtags = find_all_subproject_vtags(*projects)
    return {proj: (versions and versions[-1])
            for proj, versions in vtags.items()}


class GitVoidError(cmdlets.CmdException):
    "Sub-project has not yet been version with a *vtag*. "
    pass


def git_describe(project):
    """
    Gets sub-project's version as derived from ``git describe`` on its *vtag*.

    :param str project:
        Used as the prefix of vtags when searching them.
    :return:
        the *vtag* or raise
    :raise GitVoidError:
        if sub-project is not *vtagged* or CWD not within a git repo.
    :raise sbp.CalledProcessError:
        for any other error while executing *git*.

    .. NOTE::
       There is also the python==2.7 & python<3.6 safe :func:`polyvers.polyversion()``
       for extracting just the version part from a *vtag*; use this one
       from within project sources.

    .. INFO::
       Same results can be retrieved by this `git` command::

           git describe --tags --match <PROJECT>-v*

       where ``--tags`` is needed to consider also unannotated tags,
       as ``git tag`` does.
    """
    vtag = None
    tag_pattern = polyverslib.vtag_fnmatch_frmt % project  # TODO: from project.
    cmd = 'git describe --tags --match'.split() + [tag_pattern]
    try:
        res = oscmd.exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        vtag = out and out.strip()

        return vtag
    except sbp.CalledProcessError as ex:
        err = ex.stderr
        if "does not have any commits yet" in err or "No names found" in err:
            raise GitVoidError(
                "No *vtag* for sub-project '%s'!" % project) from ex
        elif "Not a git repository" in err:
            raise GitVoidError(err) from ex
        else:
            raise


def last_commit_tstamp():
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
    cdate = None
    try:
        log_cmd = "git log -n1 --format=format:%cD".split()
        res = oscmd.exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        cdate = out and out.strip()

        return cdate
    except sbp.CalledProcessError as ex:
        err = ex.stderr
        if "does not have any commits yet" in err:
            raise GitVoidError("No commits yet!") from ex
        elif 'Not a git repository' in err:
            raise GitVoidError(
                "Current-dir '%s' is not within a git repository!" %
                os.curdir) from ex
        else:
            raise


def main(*args):
    """
    List vtags for the given sub-project, or all if none given.

    :param args:
        usually ``*sys.argv[1:]``
    """
    import os.path as osp
    import sys

    for o in ('-h', '--help'):
        if o in args:
            doc = main.__doc__.split('\n')[1].strip()
            cmdname = osp.basename(sys.argv[0])
            print("%s\n\nUsage: %s [-v|--verbose] [PROJ-1]..." %
                  (doc, cmdname))
            exit(0)

    verbose = False
    for o in ('-v', '--verbose'):
        if o in args:
            verbose = True
            args.remove(o)

    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    vdict = get_subproject_versions(*args)
    res = '\n'.join('%s: %s' % pair
                    for pair in vdict.items())

    if res:
        print(res)


if __name__ == '__main__':
    import sys

    main(*sys.argv[1:])
