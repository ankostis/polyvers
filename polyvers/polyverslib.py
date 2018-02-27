#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Python code to discover sub-project versions in Git *polyvers* monorepos.

The *polyvers* version-configuration tool is generating tags like::

    proj-foo-v0.1.0

On purpose python code here kept with as few dependencies as possible."""

import logging
import re
import sys

import subprocess as sbp


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
             encoding='utf-8', encoding_errors='surrogateescape',
             **popen_kws):
    """
    param check_stdout:
        None: Popen(stdout=None), printed
        False: Popen(stdout=sbp.DEVNULL), ignored
        True: Popen(stdout=sbp.PIPE), collected & returned
    """
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
        errors=encoding_errors,
        **popen_kws
    )
    if res.returncode:
        log.warning('%s %r failed with %s!\n  stdout: %s\n  stderr: %s',
                    cmd_label, cmd_str, res.returncode, res.stdout, res.stderr)
    elif check_stdout or check_stderr:
        log.debug('%s %r ok: \n  stdout: %s\n  stderr: %s',
                  cmd_label, cmd_str, res.stdout, res.stderr)

    if check_returncode:
        res.check_returncode()

    return res


def describe_project(project, default=None, tag_date=False, debug=False):
    """
    A ``git describe`` replacement based on sub-project's vtags, if any.

    :param str project:
        Used as the prefix of vtags when searching them.
    :param str default:
        What to return if git cmd fails.  If `tag_date` asked, remember
        to return a tuple.
    :param bool debug:
        Version id(s) contain error?
    :param bool tag_date:
        return 2-tuple(version-id, last commit's date)
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
    vid = cdate = None
    tag_pattern = vtag_fnmatch_frmt % project
    cmd = 'git describe --tags --match'.split() + [tag_pattern]
    try:
        res = exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        vid = out and out.strip()

        if tag_date:
            log_cmd = "git log -n1 --format=format:%cD".split()
            res = exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
            out = res.stdout
            cdate = out and out.strip()
    except sbp.CalledProcessError as ex:
        if default:
            return default
        else:
            err = ex.stderr
            if 'No annotated tags' in err or 'No names found' in err:
                vid = None
            else:
                if debug:
                    vid = '<git-error: %s>' % err.strip().replace('\n', ' # ')
                else:
                    vid = '<git-error>'

    return (vid, cdate) if tag_date else vid


def describe_project_py27(project, default=None):
    "Python == 2.7 & < 3.6 function."
    import subprocess as subp

    try:
        version = subp.check_output('git describe --match %s-v*' % project)
        version = version and version.strip()
        if version:
            return version.decode('utf-8', errors='surrogateescape')
    except:  # noqa;  E722
        pass

    if not version:
        return default


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

    verbose = False
    for o in ('-v', '--verbose'):
        if o in args:
            verbose = True
            args.remove(o)

    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    if len(args) == 1:
        res = describe_project(args[0], debug=verbose)
    else:
        res = '\n'.join('%s: %s' % (p, describe_project(p, debug=verbose))
                        for p in args)

    if res:
        print(res)


if __name__ == '__main__':
    main(*sys.argv[1:])
