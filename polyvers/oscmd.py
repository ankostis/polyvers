#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#

"""Utility to call OS commands through :func:`subprocess.run()` with logging.

The *polyvers* version-configuration tool is generating tags like::

    proj-foo-v0.1.0

On purpose python code here kept with as few dependencies as possible."""

import logging
from typing import Dict

import subprocess as sbp


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


class _Cli:
    def __init__(self, popen_kw: Dict, cmd: str):
        self.popen_kw = popen_kw
        self.cmdlist = [cmd]

    def __extend_cmdlist(self, args, kw):
        def kv2arg(k, v):
            nk = len(k)
            if isinstance(v, bool):
                if v:
                    return '-' + k if len(k) == 1 else '--' + k
                else:
                    if nk == 1:
                        raise ValueError('Cannot negate -%s!' % k)
                    return '--no-' + k
            else:
                return '%s=%s' % (k, v)

        arglist = self.cmdlist
        arglist.extend(args)
        arglist.extend(kv2arg(*kv) for kv in kw.items())

    def __call__(self, *args, **kw):
        self.__extend_cmdlist(args, kw)
        res = exec_cmd(self.cmdlist, **self.popen_kw)
        self.rc = res.returncode
        self.stderr = res.stderr
        return res.stdout

    def _(self, *args, **kw):
        self.__extend_cmdlist(args, kw)
        return self


class PopenCmd:
    def __init__(self, **popen_kw):
        self._popen_kw = popen_kw

    def __getattr__(self, attr):
        return _Cli(self._popen_kw, attr)


oscmd = PopenCmd(check_stdout=True, check_stderr=True)
