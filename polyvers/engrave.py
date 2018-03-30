#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Search and replace version-ids in files."""

from collections import OrderedDict as odict
from pathlib import Path
from typing import List, Tuple, Sequence
import logging

from . import fileutils as fu, pvproject


log = logging.getLogger(__name__)


def _as_glob_pattern_pair(fpath):
    """
    Add '**' in relative names, eliminate comments and split in positive/negatives

    :return:
        a 2-tuple(positive, negative), one always None
    """
    fpath = fpath.strip()

    ## Remove comments/empty-lines.
    if not fpath or fpath.startswith('#') or fpath.startswith('..'):
        return (None, None)

    if fpath.startswith('!'):
        # raise NotImplementedError('Negative match pattern %r not supported!' %
        #                           fpath)
        (positive, negative) = _as_glob_pattern_pair(fpath[1:])
        return (negative, positive)

    ## TODO: Handle '!' and escaping with '\' like .gitignore
    if fpath.startswith(('./', '/')):
        fpath = fpath.lstrip('./')
        fpath = fpath.lstrip('/')
    else:
        fpath = '**/' + fpath

    return (fpath.replace('\\', ''), None)


def _prepare_glob_pairs(patterns):
    pat_pairs = [_as_glob_pattern_pair(fpat) for fpat in patterns]
    pat_pairs = [pair for pair in pat_pairs if any(pair)]

    return pat_pairs


def _glob_find_files(pattern_pairs: Tuple[str, str], mybase: Path):
    from boltons.setutils import IndexedSet as iset

    files = iset()
    notfiles = set()  # type: ignore
    for positive, negative in pattern_pairs:
        if positive:
            new_files = iset(mybase.glob(positive))
            cleared_files = [f for f in new_files
                             if not any(nf in f.parents for nf in notfiles)]
            files.update(cleared_files)
        elif negative:
            new_notfiles = mybase.glob(negative)
            notfiles.update(new_notfiles)
        else:
            raise AssertionError("Both in (positive, negative) pair are None!")

    return files


def _glob_filter_in_mybase(files: pvproject.FPaths,
                           mybase: Path):
    assert all(isinstance(f, Path) for f in files)
    nfiles = []
    for f in files:
        try:
            rpath = f.relative_to(mybase)
            if '..' not in str(rpath):
                nfiles.append(f)
        except ValueError as _:
            "Skip it, outside mybase"

    return nfiles


def _glob_filter_out_other_bases(files: pvproject.FPaths,
                                 other_bases: pvproject.FPaths):
    if not other_bases:
        return files

    assert all(isinstance(f, Path) for f in files)
    assert all(isinstance(f, Path) for f in other_bases)

    nfiles = [f for f in files
              if not any(fu._is_base_or_same(obase, f) in (None, True)
                         for obase in other_bases)]

    return nfiles


def glob_files(patterns: List[str],
               mybase: pvproject.FLike = '.',
               other_bases: pvproject.FLikeList = None) -> pvproject.FPaths:
    """
    Glob files in `mybase` but not in `other_bases` (unless bases coincide).

    - Supports exclude patterns: ``!foo``.
    - If `mybase` is in `other_bases`, it doesn't change the results.
    """
    pattern_pairs = _prepare_glob_pairs(patterns)

    mybase = Path(mybase)
    files = _glob_find_files(pattern_pairs, mybase)

    files = _glob_filter_in_mybase(files, mybase)
    if other_bases:
        ## Exclude bases coinciding with mybase.
        other_ppaths = [Path(ob) for ob in other_bases]
        other_ppaths = [ob for ob in other_ppaths
                        if not fu._is_same_file(mybase, ob)]
        files = _glob_filter_out_other_bases(files, other_ppaths)

    assert all(isinstance(f, Path) for f in files)
    return files


def scan_engraves(engraves: Sequence[pvproject.Engrave]) -> pvproject.PathEngraves:
    hits = [(engpaths, enghits)
            for eng in engraves
            for engpaths, enghits in eng.scan_hits().items()]

    ## Consolidate grafts-per-file in a single map.
    #
    hits_map: pvproject.PathEngraves = odict()
    for fpath, fspec in hits:
        prev_fspec = hits_map.get(fpath)
        if prev_fspec:
            prev_fspec.grafts.extend(fspec.grafts)
        else:
            hits_map[fpath] = fspec

    return hits_map
