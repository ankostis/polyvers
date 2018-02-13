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


def exec_cmd(cmd, check_out=None, dry_run=False,
             encoding='utf-8', encoding_errors='surrogateescape'):
    """
    param check_out:
        False: Popen(stdout=sbp.DEVNULL), ignored
        True: Popen(stdout=sbp.PIPE), collected & returned
        None: Popen(stdout=None), printed
    """
    import subprocess as sbp

    log = logging.getLogger(__name__)
    call_types = {
        None: {'label': 'EXEC', 'stdout': None},
        False: {'label': 'EXEC(no-stdout)', 'stdout': sbp.DEVNULL},
        True: {'label': 'CALL', 'stdout': sbp.PIPE},
    }
    ctype = call_types[check_out]
    cmd_label = ctype['label']
    cmd_str = format_syscmd(cmd)

    log.debug('%s%s %r', 'DRY_' if dry_run else '', cmd_label, cmd_str)

    if dry_run:
        return

    ##WARN: python 3.6 `encoding` & `errors` kwds in `Popen`.
    res = sbp.run(
        cmd,
        stdout=ctype['stdout'],
        stderr=sbp.STDOUT,
        encoding=encoding,
        errors=encoding_errors
    )
    if res.returncode:
        log.error('%s %r failed with %s!\n  stdout: %s',
                  cmd_label, cmd_str, res.returncode, res.stdout)
    elif check_out:
        log.debug('%s %r ok: \n  stdout: %s',
                  cmd_label, cmd_str, res.stdout)
    res.check_returncode()

    return res.stdout and res.stdout.strip()


def find_all_subproject_vtags(*projects):
    """
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
    out = exec_cmd(cmd, check_out=True)
    tags = out.split('\n')

    project_versions = defaultdict(list)
    for t in tags:
        m = vtag_regex.match(t)
        if m:
            pname, ver = m.groups()
            project_versions[pname].append(ver)

    return project_versions


def get_subproject_versions(*projects):
    import subprocess as sbp

    try:
        vtags = find_all_subproject_vtags(*projects)
    except sbp.CalledProcessError as _:
        pass
    else:
        return {proj: (versions and versions[-1])
                for proj, versions in vtags.items()}


if __name__ == '__main__':
    logging.basicConfig(level=0)
    print(get_subproject_versions(*sys.argv[1:]))
