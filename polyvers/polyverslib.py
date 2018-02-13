#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Python code to discover sub-project version in a Git monorepo."""

from collections import defaultdict
import logging
import re
import sys


def format_syscmd(cmd):
    if isinstance(cmd, (list, tuple)):
        cmd = ' '.join('"%s"' % s if ' ' in s else s
                       for s in cmd)
    else:
        assert isinstance(cmd, str), cmd

    return cmd


def exec_cmd(cmd,
             dry_run=False,
             check_stdout=None,
             check_stderr=None,
             check_returncode=True,
             encoding='utf-8', encoding_errors='surrogateescape'):
    """
    param check_stdout:
        None: Popen(stdout=None), printed
        False: Popen(stdout=sbp.DEVNULL), ignored
        True: Popen(stdout=sbp.PIPE), collected & returned
    """
    import subprocess as sbp

    log = logging.getLogger(__name__)
    call_types = {
        None: {'label': 'EXEC', 'stream': None},
        False: {'label': 'EXEC(no-stdout)', 'stream': sbp.DEVNULL},
        True: {'label': 'CALL', 'stream': sbp.PIPE},
    }
    stdout_ctype = call_types[check_stdout]
    cmd_label = stdout_ctype['label']
    cmd_str = format_syscmd(cmd)

    log.debug('%s%s %r', 'DRY_' if dry_run else '', cmd_label, cmd_str)

    if dry_run:
        return

    ##WARN: python 3.6 `encoding` & `errors` kwds in `Popen`.
    res = sbp.run(
        cmd,
        stdout=stdout_ctype['stream'],
        stderr=call_types[check_stderr]['stream'],
        encoding=encoding,
        errors=encoding_errors
    )
    if res.returncode:
        log.error('%s %r failed with %s!\n  stdout: %s\n  stderr: %s',
                  cmd_label, cmd_str, res.returncode, res.stdout, res.stderr)
    elif check_stdout or check_stderr:
        log.debug('%s %r ok: \n  stdout: %s\n  stderr: %s',
                  cmd_label, cmd_str, res.stdout, res.stderr)

    if check_returncode:
        res.check_returncode()

    return res


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
    vtag_fnmatch_frmt = '%s-v*'
    vtag_regex = re.compile(r'^([-.\w]+)-v(\d.+)$', re.IGNORECASE)

    patterns = [vtag_fnmatch_frmt % p
                for p in projects or ('*', )]
    cmd = ['git', 'tag', '-l'] + patterns
    res = exec_cmd(cmd, check_stdout=True, check_stderr=True)
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


if __name__ == '__main__':
    logging.basicConfig(level=0)
    print(get_subproject_versions(*sys.argv[1:]))
