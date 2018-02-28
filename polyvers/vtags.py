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


def rfc2822_now():
    from datetime import datetime
    import email.utils as emu

    return emu.format_datetime(datetime.now())


class NoVersionError(cmdlets.CmdException):
    "Sub-project has not yet been version with a *vtag*. "
    pass


def describe_project(project, default=None, tag_date=False):
    """
    A ``git describe`` replacement based on sub-project's vtags, if any.

    :param str project:
        Used as the prefix of vtags when searching them.
    :param str default:
        What *version* to return on failutes (no project vtags or no git repo).
        If that is `None`, any git command failure gets raised.
    :param bool tag_date:
        return 2-tuple(version-id, last commit's date).  If cannot derive it
        from git, report now!
        RFC2822 sample: 'Thu, 09 Mar 2017 10:50:00 -0000'
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

    :raise NoVersionError:
        if sub-project is not *vtagged*, and no `default` given.
    :raise sbp.CalledProcessError:
        for any other error while executing *git*.

    .. NOTE::
       There is also the python==2.7 & python<3.6 safe :func:`polyvers.polyversion()``
       for extracting just the version part from a *vtag*; use this one
       from within project sources.

    .. TIP::
       Same results also retrieved by `git` command::

           git describe --tags --match <PROJECT>-v*

       ``--tags`` needed to consider also unannotated tags, as ``git tag`` does.
    """
    version = cdate = None
    tag_pattern = polyverslib.vtag_fnmatch_frmt % project
    cmd = 'git describe --tags --match'.split() + [tag_pattern]
    try:
        res = oscmd.exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        version = out and out.strip()
    except sbp.CalledProcessError as ex:
        if default is not None:
            version = default
        else:
            err = ex.stderr
            if 'No annotated tags' in err or 'No names found' in err:
                raise NoVersionError(
                    "No *vtag* for sub-project '%s'!" % project) from ex
            else:
                raise

    if tag_date:
        try:
            log_cmd = "git log -n1 --format=format:%cD".split()
            res = oscmd.exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
            out = res.stdout
            cdate = out and out.strip()
        except:  # noqa;  E722
            if default is not None:
                cdate = rfc2822_now()
            else:
                raise

        return (version, cdate)

    return version


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
