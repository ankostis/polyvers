#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Python-2.7 safe code to discover sub-project versions in Git *polyvers* monorepos.

The *polyvers* version-configuration tool is generating **vtags** like::

    proj-foo-v0.1.0

And assuming :func:`polyversion()` is invoked from within a Git repo, it may return
either ``0.1.0`` or ``0.1.0+2.gcaffe00``, if 2 commits have passed since
last *vtag*.
"""
from __future__ import print_function

import sys
import re

import subprocess as sbp


#: The default pattern globbing for *vtags* with ``git describe --match <pattern>``.
vtag_fnmatch_frmt = '%s-v*'

#: The default regex pattern breaking *vtags* into 3 capturing groups.
#: See :pep:`0426` for project-name characters and format.
vtag_regex = re.compile(r"""(?xi)
    ^(?P<project>[A-Z0-9]|[A-Z0-9][A-Z0-9._-]*?[A-Z0-9])
    -
    v(?P<version>\d[^-]*)
    (?:-(?P<descid>\d+-g[a-f\d]+))?$
""")


def clean_cmd_result(res):  # type: (bytes) -> str
    """
    :return:
        only if there is something in `res`, as utf-8 decoded string
    """
    res = res and res.strip()
    if res:
        return res.decode('utf-8', errors='surrogateescape')


def rfc2822_tstamp(nowdt=None):
    """Py2.7 code from https://stackoverflow.com/a/3453277/548792"""
    from datetime import datetime
    import time
    from email import utils

    if nowdt is None:
        nowdt = datetime.now()
    nowtuple = nowdt.timetuple()
    nowtimestamp = time.mktime(nowtuple)
    now = utils.formatdate(nowtimestamp)

    return now


def _my_run(cmd):
    "For commands with small output/stderr."
    proc = sbp.Popen(cmd.split(), stdout=sbp.PIPE, stderr=sbp.PIPE, bufsize=-1)
    res, err = proc.communicate()

    if proc.returncode != 0:
        print(err, file=sys.stderr)
        raise sbp.CalledProcessError(proc.returncode, cmd)
    else:
        return clean_cmd_result(res)


def split_vtag(vtag, vtag_regex):
    try:
        m = vtag_regex.match(vtag)
        if not m:
            raise ValueError(
                "Unparseable *vtag* from `vtag_regex`!")
        mg = m.groupdict()
        return mg['project'], mg['version'], mg['descid']
    except Exception as ex:
        print("Matching vtag '%s' failed due to: %s" %
              (vtag, ex), file=sys.stderr)
        raise


def polyversion(project, default=None,
                vtag_fnmatch_frmt=vtag_fnmatch_frmt,
                vtag_regex=vtag_regex):
    """
    Report *vtag* derived sub-project-version; use it from within it's sources.

    :param str project:
        Used as the prefix of vtags when searching them.
    :param str default:
        What *version* to return if git cmd fails.
    :param str vtag_fnmatch_frmt:
        The pattern globbing for *vtags* with ``git describe --match <pattern>``.
        See :data:`vtag_fnmatch_frmt`
    :param regex vtag_regex:
        The regex pattern breaking apart *vtags*, with 3 named capturing groups:
        - ``project``,
        - ``version`` (without the 'v'),
        - ``descid`` (optional) anything following the dash('-') after
          the version in ``git-describe`` result.
        See :data:`vtag_regex`
    :return:
        the version-id or `default` if command failed/returned nothing

    .. NOTE::
       This is a python==2.7 & python<3.6 safe function; there is also the similar
       function with elaborate error-handling :func:`polyvers.vtags.descrive_project()`
       used by the tool internally.
    """
    version = None
    tag_pattern = vtag_fnmatch_frmt % project
    try:
        cmd = 'git describe --tags --match %s' % tag_pattern
        vtag = _my_run(cmd)
        matched_project, version, descid = split_vtag(vtag, vtag_regex)
        if matched_project != project:
            print("Matched  vtag project '%s' different from expected '%s'!" %
                  (matched_project, project), file=sys.stderr)
        if descid:
            local_part = descid.replace('-', '.')
            version = '%s+%s' % (version, local_part)
    except:  # noqa;  E722"
        if default is None:
            raise

    if not version:
        version = default

    return version


def polytime(no_raise=False):
    """
    The date of the last commit of the project.

    :param str no_raise:
        If true, never fail and return current-time
    :return:
        the commit-date if in git repo, or now; :rfc:`2822` formatted
    """
    cdate = None
    cmd = "git log -n1 --format=format:%cD"
    try:
            cdate = _my_run(cmd)
    except:  # noqa;  E722
        if not no_raise:
            raise

    if not cdate:
        cdate = rfc2822_tstamp()

    return cdate


def main(*args):
    """
    Describe a single or multiple projects.

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

    if len(args) == 1:
        res = polyversion(args[0])
    else:
        res = '\n'.join('%s: %s' % (p, polyversion(p, default=''))
                        for p in args)

    if res:
        print(res)


if __name__ == '__main__':
    main(*sys.argv[1:])
