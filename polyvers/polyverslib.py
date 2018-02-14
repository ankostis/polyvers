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


vtag_fnmatch_frmt = '%s-v*'
vtag_regex = re.compile(r'^([-.\w]+)-v(\d.+)$', re.IGNORECASE)


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


def describe_project(project, date=False, debug=False):
    """
    A ``git describe`` replacement based on project's vtags, if any.

    :param str project:
        Used as the prefix of vtags when searching them.
    :param bool debug:
        Version id(s) contain error?
    :return:
        when `date` is false:
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
    tag_pattern = vtag_fnmatch_frmt % project
    cmd = 'git describe --tags --match'.split() + [tag_pattern]
    log_cmd = "git log -n1 --format=format:%cD".split() if date else None
    try:
        res = exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        vid = out and out.strip()

        if log_cmd:
            res = exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
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

    return (vid, cdate) if date else vid


def main(*args):
    """
    Describe a single project, or list their (all) vtags if more (none) given.

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
    if len(args) == 1:
        res = describe_project(args[0], debug=verbose)
    else:
        vdict = get_subproject_versions(*args)
        res = '\n'.join('%s: %s' % pair
                        for pair in vdict.items())

    if res is not None:
        print(res)


if __name__ == '__main__':
    main(*sys.argv[1:])
