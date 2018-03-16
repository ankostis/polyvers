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
from typing import List, Tuple, Sequence, Dict, Match, Union, Optional
import logging
import re

from . import cmdlets, fileutils as fu
from ._vendor.traitlets.traitlets import (
    Union as UnionTrait, Instance, List as ListTrait, Unicode, Int, CRegExp)
from .autoinstance_traitlet import AutoInstance
from .slice_traitlet import Slice as SliceTrait


log = logging.getLogger(__name__)


FPaths = List[Path]
FLike = Union[str, Path]
FLikeList = List[FLike]


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


def _glob_filter_in_mybase(files: FPaths,
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


def _glob_filter_out_other_bases(files: FPaths,
                                 other_bases: FPaths):
    if not other_bases:
        return files

    assert all(isinstance(f, Path) for f in files)
    assert all(isinstance(f, Path) for f in other_bases)

    nfiles = [f for f in files
              if not any(fu._is_base_or_same(obase, f) in (None, True)
                         for obase in other_bases)]

    return nfiles


def glob_files(patterns: List[str],
               mybase: FLike = '.',
               other_bases: Union[FLikeList, None] = None) -> FPaths:
    """
    Glob files in `mybase` but not in `other_bases` (unless bases coincide).

    - support exclude patterns: ``!foo``.
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


PatternClass = type(re.compile('.*'))  # For traitlets
MatchClass = type(re.match('.*', ''))  # For traitlets


def _slices_to_ids(slices, thelist):
    from boltons.setutils import IndexedSet as iset

    all_ids = list(range(len(thelist)))
    mask_ids = iset()
    for aslice in slices:
        mask_ids.update(all_ids[aslice])

    return list(mask_ids)


class GraftSpec(cmdlets.Spec, cmdlets.Replaceable, cmdlets.Printable):
    regex = CRegExp(
        read_only=True,
        config=True,
        help="What to search"
    )

    subst = Unicode(
        allow_none=True, default_value='',
        help="""
        What to replace with; if `None`, no substitution happens.

        Inside them, supported extensions are:
        - captured groups with '\\1 or '\g<foo>' expressions
          (see Python's regex documentation)
        - interpolation variables; Keys available (apart from env-vars prefixed with '$'):
          {ikeys}
        """
    )

    slices = UnionTrait(
        (SliceTrait(), ListTrait(SliceTrait())),
        read_only=True,
        config=True,
        help="""
        Which of the `hits` to substitute, in "slice" notation(s); all if not given.

        Example::

            gs = GraftSpec()
            gs.slices = 0                ## Only the 1st match.
            gs.slices = '1:'             ## Everything except the 1st match
            gs.slices = ['1:3', '-1:']   ## Only 2nd, 3rd and the last match.
                "

        """
    )

    hits = ListTrait(Instance(MatchClass), read_only=True)
    hits_indices = ListTrait(Int(),
                             allow_none=True,
                             default_value=None, read_only=True)
    nsubs = Int(allow_none=True, read_only=True)

    def collect_graft_hits(self, ftext: str) -> 'GraftSpec':
        """
        :return:
            a clone with updated `hits`
        """
        hits: List[Match] = list(self.regex.finditer(ftext))
        return self.replace(hits=hits)

    def _get_hits_indices(self) -> Optional[List[int]]:
        """
        :return:
            A list with the list-indices of hits kept, or None if no `slices` given.
        """
        slices: Union[slice, List[slice]] = self.slices
        if slices:
            if not isinstance(slices, list):
                slices = [slices]

            hits_indices = _slices_to_ids(slices, self.hits)

            return hits_indices

    def valid_hits(self) -> List[Match]:
        hits = self.hits
        hits_indices = self.hits_indices
        if hits_indices is None:
            return hits
        else:
            return [hits[i] for i in hits_indices]

    def substitute_graft_hits(self, fpath: Path, ftext: str) -> Tuple[str, 'GraftSpec']:
        """
        :return:
            A 2-TUPLE ``(<substituted-ftext>, <updated-graft-spec>)``, where
            ``<updated-graft-spec>`` is a *possibly* clone with updated
            `hits_indices` (if one used), or the same if no idices used,
            or None if no hits remained. after hits-slices filtering
        """
        if not self.hits:
            return (ftext, self)

        orig_ftext = ftext

        hits_indices = self._get_hits_indices()
        if hits_indices:
            clone = self.replace(hits_indices=hits_indices)
            log.debug(
                "Replacing %i out of %i matches in file '%s' of pattern '%s': %s",
                len(hits_indices), len(self.hits), fpath, self.regex, hits_indices)
        elif self.hits:
            clone = self.replace()

        ## NOTE: Bad programming style to update state (hits_indices)
        #  and then rely on that inside the same method.

        nsubs = 0
        for m in clone.valid_hits():
            if clone.subst is not None:
                ftext = ftext[:m.start()] + m.expand(clone.subst) + ftext[m.end():]
                nsubs += 1
        clone.nsubs = nsubs

        if not nsubs:
            assert ftext == orig_ftext, (ftext, orig_ftext)

        return (ftext, clone)


class Engrave(cmdlets.Spec, cmdlets.Replaceable):
    """File-patterns to search and replace with version-id patterns."""

    globs = ListTrait(
        Unicode(),
        read_only=True,
        config=True,
        help="A list of POSIX file patterns (.gitgnore-like) to search and replace"
    )

    grafts = ListTrait(
        AutoInstance(GraftSpec),
        read_only=True,
        config=True,
        help="""
        A list of `GraftSpec` for engraving (search & replace) version-ids or other infos.

        Use `{appname} config desc GraftSpec` to see its syntax.
        """
    )

    encoding = Unicode(
        'utf-8',
        read_only=True,
        config=True,
        help="Open files with this encoding."
    )

    encoding_errors = Unicode(
        'surrogateescape',
        read_only=True,
        config=True,
        help="""
        Open files with this encoding-error handling.

        See https://docs.python.org/3/library/codecs.html#codecs.register_error
        """
    )

    fpath = Instance(Path, allow_none=True, read_only=True)
    ftext = Unicode(allow_none=True, read_only=True)

    def _fread(self, fpath: Path):
        return fpath.read_text(
            encoding=self.encoding, errors=self.encoding_errors)

    def _fwrite(self, fpath: Path, text: str):
        fpath.write_text(
            text, encoding=self.encoding, errors=self.encoding_errors)

    def read_files(self, files: FPaths) -> 'PathEngraves':
        pathengs: 'PathEngraves' = odict()

        for fpath in files:
            ## TODO: try-catch file-reading.
            ftext = self._fread(fpath)

            pathengs[fpath] = self.replace(fpath=fpath, ftext=ftext)

        return pathengs

    def collect_glob_files(self,
                           mybase: FLike = '.',
                           other_bases: Union[FLikeList, None] = None) -> FPaths:
        return glob_files(self.globs, mybase, other_bases)

    def collect_file_hits(self) -> 'Engrave':
        """
        :return:
            a clone with `grafts` updated
        """
        new_grafts: List[GraftSpec] = []
        ftext = self.ftext
        for vg in self.grafts:
            nvgraft = vg.collect_graft_hits(ftext)
            new_grafts.append(nvgraft)

        return self.replace(grafts=new_grafts)

    def substitute_file_hits(self) -> Optional['Engrave']:
        """
        :return:
            a clone with substituted `grafts` updated, or none if nothing substituted
        """
        new_grafts: List[GraftSpec] = []
        ftext = self.ftext
        fpath = self.fpath
        for vg in self.grafts:
            subst_res = vg.substitute_graft_hits(fpath, ftext)
            if subst_res:
                ftext, nvgraft = subst_res
                new_grafts.append(nvgraft)

        if new_grafts:
            return self.replace(ftext=ftext, grafts=new_grafts)
        else:
            assert self.ftext == ftext, (self.ftext, ftext)

    @property
    def nhits(self):
        return sum(len(vg.valid_hits()) for vg in self.grafts)

    @property
    def nsubs(self):
        return sum(vg.nsubs for vg in self.grafts)

    ####################
    ## PathEngs maps ##
    ####################

    def collect_all_hits(self, pathengs: 'PathEngraves') -> 'PathEngraves':
        hits: 'PathEngraves' = odict()
        for fpath, eng in pathengs.items():
            ## TODO: try-catch regex matching.
            neng = eng.collect_file_hits()
            hits[fpath] = neng

        return hits

    def substitute_hits(self, hits: 'PathEngraves') -> 'PathEngraves':
        substs: 'PathEngraves' = odict()
        for fpath, eng in hits.items():
            ## TODO: try-catch regex substitution.
            neng = eng.substitute_file_hits()
            if neng:
                substs[fpath] = neng

        return substs

    def write_engraves(self, substs: 'PathEngraves') -> None:
        if not self.dry_run:
            for fpath, eng in substs.items():
                ## TODO: try-catch regex matching.
                self._fwrite(fpath, eng.ftext)

    def _log_action(self, pathengs: 'PathEngraves', action: str):
        file_lines = '\n  '.join('%s: %i %s' % (fpath, eng.nhits, action)
                                 for fpath, eng in pathengs.items())
        ntotal = sum(eng.nhits for eng in pathengs.values())
        log.info("%sed %i files: %s", action.capitalize(), ntotal, file_lines)

    def scan_hits(self,
                  mybase: FLike = '.',
                  other_bases: Union[FLikeList, None] = None
                  ) -> 'PathEngraves':
        files: FPaths = self.collect_glob_files(mybase=mybase,
                                                other_bases=other_bases)
        log.info("Globbed %i files in '%s': %s",
                 len(files), Path(mybase).resolve(), ', '.join(str(f) for f in files))

        pathengs: 'PathEngraves' = self.read_files(files)

        file_hits: 'PathEngraves' = self.collect_all_hits(pathengs)
        self._log_action(file_hits, 'match')

        return file_hits

    def engrave_hits(self, hits: 'PathEngraves') -> 'PathEngraves':
        substs: 'PathEngraves' = self.substitute_hits(hits)
        self._log_action(substs, 'graft')

        self.write_engraves(substs)

        return substs

    def scan_and_engrave(self) -> 'PathEngraves':
        hits = self.scan_hits()
        return self.engrave_hits(hits)


PathEngraves = Dict[Path, Engrave]


def scan_engraves(engraves: Sequence[Engrave]) -> PathEngraves:
    hits = [(engpaths, enghits)
            for eng in engraves
            for engpaths, enghits in eng.scan_hits().items()]

    ## Consolidate grafts-per-file in a single map.
    #
    hits_map: PathEngraves = odict()
    for fpath, fspec in hits:
        prev_fspec = hits_map.get(fpath)
        if prev_fspec:
            prev_fspec.grafts.extend(fspec.grafts)
        else:
            hits_map[fpath] = fspec

    return hits_map
