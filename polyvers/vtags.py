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
import sys

import polyvers.polyverslib as pvlib


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
    tag_patterns = [pvlib.vtag_fnmatch_frmt % p
                    for p in projects or ('*', )]
    cmd = 'git tag --merged HEAD -l'.split() + tag_patterns
    res = pvlib.exec_cmd(cmd, check_stdout=True, check_stderr=True)
    out = res.stdout
    tags = out and out.strip().split('\n') or []

    project_versions = defaultdict(list)
    for t in tags:
        m = pvlib.vtag_regex.match(t)
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


def describe_project(project, tag_date=False, debug=False):
    """
    A ``git describe`` replacement based on project's vtags, if any.

    :param str project:
        Used as the prefix of vtags when searching them.
    :param bool debug:
        Version id(s) contain error?
    :param bool tag_date:
        return 2-uple(version-id, last commit's date)
    :return:
        when `tag_date` is false:
            the version-id (possibly null), or '<git-error>' if ``git`` command
            failed.
        otherwise:
            the tuple (version, commit-RFC2822-date)

    .. TIP::
        It is to be used in ``__init__.py`` files like this::

            __version__ = describe_project('myproj')

        ...or::

            __version__, __updated__ = describe_project('myproj', date=True)


    Same results also retrieved by `git` command::

        git describe --tags --match <PROJECT>-v*

    ``--tags`` needed to consider also unannotated tags, as ``git tag`` does.
    """
    import subprocess as sbp

    vid = cdate = None
    tag_pattern = pvlib.vtag_fnmatch_frmt % project
    cmd = 'git describe --tags --match'.split() + [tag_pattern]
    try:
        res = pvlib.exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        vid = out and out.strip()

        if tag_date:
            log_cmd = "git log -n1 --format=format:%cD".split()
            res = pvlib.exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
            out = res.stdout
            cdate = out and out.strip()
    except sbp.CalledProcessError as ex:
        err = ex.stderr
        if 'No annotated tags' in err or 'No names found' in err:
            vid = None
        else:
            if debug:
                vid = '<git-error: %s>' % err.strip().replace('\n', ' # ')
            else:
                vid = '<git-error>'

    return (vid, cdate) if tag_date else vid


def main(*args):
    """
    List vtags for the given sub-project, or all if none given.

    :param args:
        usually ``*sys.argv[1:]``
    """
    import os.path as osp

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
    main(*sys.argv[1:])
