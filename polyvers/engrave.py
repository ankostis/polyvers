#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Search and replace version-ids in files."""

from . import cmdlets as cmd
from ._vendor.traitlets import List, Tuple, Unicode, CRegExp  # @UnresolvedImport


def as_glob_pattern(fpath):
    "Add '**' in relative names, and eliminate comments"
    fpath = fpath.strip()

    ## Remove comments/empty-lines.
    if not fpath or fpath.startswith('#'):
        return

    if fpath.startswith('!'):
        # raise NotImplementedError('Negative match pattern %r not supported!' %
        #                           fpath)
        return '!' + as_glob_pattern(fpath[1:])

    ## TODO: Handle '!' and escaping with '\' like .gitignore
    if fpath.startswith('/'):
        fpath = fpath.lstrip('/')
    else:
        fpath = '**/' + fpath

    return fpath.replace('\\', '')


def glob_files(patterns):
        from glob import iglob
        import itertools as itt
        from boltons.setutils import IndexedSet as iset

        patterns = [as_glob_pattern(fpat) for fpat in patterns]
        files = itt.chain.from_iterable(iglob(fpat, recursive=True)
                                        for fpat in patterns)
        files = iset(files)

        return files


def _enact_all_tmp_files(tmpfiles):
    import shutil

    for fpath, npath in tmpfiles.items():
        shutil.copystat(fpath, npath)
        shutil.move(npath, fpath)


def prepare_glob_list(files):
    files = [as_glob_pattern(fpath) for fpath in files]
    files = [fpath for fpath in files if fpath]

    return files


class Engrave(cmd.Spec):
    """File-patterns to search and replace with version-id patterns."""

    files = List(
        #Unicode(),
        help="A list of POSIX file patterns (.gitgnore-like) to search and replace"
    ).tag(config=True)

    vgreps = List(
        Tuple(CRegExp(), Unicode()),
        help="""
        A list of 2-tuples (search, replace) patterns.

        - The `search` part is a regular expression.
        - The `replace` may use any capture groups (see Python's regex documentation)
          or interpolation variables.
        """
    ).tag(config=True)

    encoding = Unicode(
        'utf-8',
        help="Open files with this encoding."
    ).tag(config=True)

    encoding_errors = Unicode(
        'surrogateescape',
        help="""
        Open files with this encoding-error handling.

        See https://docs.python.org/3/library/codecs.html#codecs.register_error
        """
    ).tag(config=True)

    def _fopen(self, fpath, mode):
        import io

        return io.open(fpath, mode=mode,
                       encoding=self.encoding, errors=self.encoding_errors)

    def proc_file(self, fpath, tmpfiles):
        # https://stackoverflow.com/a/31499114/548792
        import os

        npath = fpath + '$'
        changed = False
        with self._fopen(fpath, 'r') as finp, self._fopen(npath, 'w') as fout:
            for line in finp:
                nline = line

                for regex, replace in self.vgreps:
                    nline = regex.sub(replace, nline)

                fout.write(nline)
                changed |= (nline != line)

        if changed:
            tmpfiles[fpath] = npath
        else:
            os.remove(npath)

    def engrave_all(self):
        self._tmpfiles = {}
        visited = set()
        tmpfiles = {}
        for fpath in glob_files(self.files):
            if fpath in visited:
                continue
            visited.add(fpath)

            self.proc_file(fpath, tmpfiles)

        _enact_all_tmp_files(tmpfiles)
