#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Search and replace version-ids in files."""

from collections import OrderedDict as odict, defaultdict
from pathlib import Path
from typing import List, Tuple, Sequence, Dict, Match, Union, Optional
import logging
import re

from . import cmdlets, fileutils as fu, pvtags
from ._vendor.traitlets.traitlets import (
    Union as UnionTrait, Instance, List as ListTrait, Unicode, Int, Bytes)
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


PatternClass = type(re.compile('.*'))  # For traitlets
MatchClass = type(re.match('.*', ''))  # For traitlets


def _slices_to_ids(slices, thelist):
    from boltons.setutils import IndexedSet as iset

    all_ids = list(range(len(thelist)))
    mask_ids = iset()
    for aslice in slices:
        mask_ids.update(all_ids[aslice])

    return list(mask_ids)


class Graft(cmdlets.Replaceable, cmdlets.Printable, cmdlets.Spec):
    regex = Unicode(
        read_only=True,
        config=True,
        help="The regular-expressions to search within the byte-contents of files."
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

            gs = Graft()
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
    nsubs = Int(allow_none=True)

    def collect_graft_hits(self, fbytes: bytes) -> 'Graft':
        """
        :return:
            a clone with updated `hits`
        """
        hits: List[Match] = list(self.regex.finditer(fbytes))
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

    def substitute_graft_hits(self, fpath: Path, fbytes: bytes) -> Tuple[str, 'Graft']:
        """
        :return:
            A 2-TUPLE ``(<substituted-fbytes>, <updated-graft>)``, where
            ``<updated-graft>`` is a *possibly* clone with updated
            `hits_indices` (if one used), or the same if no idices used,
            or None if no hits remained. after hits-slices filtering
        """
        if not self.hits:
            return (fbytes, self)

        orig_fbytes = fbytes

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
                fbytes = fbytes[:m.start()] + m.expand(clone.subst) + fbytes[m.end():]
                nsubs += 1
        clone.nsubs = nsubs

        if not nsubs:
            assert fbytes == orig_fbytes, (fbytes, orig_fbytes)

        return (fbytes, clone)


class Engrave(cmdlets.Replaceable, cmdlets.Spec):
    """File-patterns to search and replace with version-id patterns."""

    globs = ListTrait(
        Unicode(),
        read_only=True,
        config=True,
        help="A list of POSIX file patterns (.gitgnore-like) to search and replace"
    )

    grafts = ListTrait(
        AutoInstance(Graft),
        read_only=True,
        config=True,
        help="""
        A list of `Graft` for engraving (search & replace) version-ids or other infos.

        Use `{appname} config desc Graft` to see its syntax.
        """
    )

    def collect_glob_files(self,
                           mybase: FLike = '.',
                           other_bases: Union[FLikeList, None] = None
                           ) -> FPaths:
        return glob_files(self.globs, mybase, other_bases)

    def collect_file_hits(self, fbytes: bytes) -> List[Graft]:
        """
        :return:
            the updated cloned `grafts` that match the given text
        """
        new_grafts: List[Graft] = []
        for vg in self.grafts:
            nvgraft = vg.collect_graft_hits(fbytes)
            new_grafts.append(nvgraft)

        return new_grafts


class FileContents(cmdlets.Printable, cmdlets.Spec):
    fbytes: bytes = Bytes()

    def collect_all_hits(self, pathengs: 'PathEngraves') -> 'PathEngraves':
        hits: 'PathEngraves' = odict()
        for fpath, eng in pathengs.items():
            ## TODO: try-catch regex matching.
            neng = eng.collect_file_hits()
            hits[fpath] = neng

        return hits

    def substitute_file_hits(self) -> Optional['Engrave']:
        """
        :return:
            a clone with substituted `grafts` updated, or none if nothing substituted
        """
        new_grafts: List[Graft] = []
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
        ##TODO: replace with FileProcessor
        files: FPaths = self.collect_glob_files(mybase=mybase,
                                                other_bases=other_bases)
        log.info("%s globbed %i files in '%s': %s",
                 self, len(files), Path(mybase).resolve(), ', '.join(str(f) for f in files))

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


class FileProcessor(cmdlets.Spec):
    def read_files(self, fpaths: Sequence[Path]) -> Dict[Path, bytes]:
        path_bytes = {}

        with self.errlog(IOError,
                         token='fread',
                         doing="reading files to engrave") as errlog:
            for fpath in fpaths:
                with errlog(action=fpath):
                    path_bytes[fpath] = fpath.read_bytes()

        return path_bytes

    def glob_files_from_projects(self, projects: "Sequence[pvtags.Project]"
                                 ) -> List[Path]:
        other_bases = [prj.basepath for prj in projects]

        with self.errlog(IOError,
                         token='glob',
                         doing="globbing projects") as errlog:
            for prj in projects:
                with errlog(action=prj.pname):
                    mybase = prj.basepath
                    fpaths = prj.collect_glob_files(
                        mybase=mybase, other_bases=other_bases)

#     def path_grafts_from_projects(self,
#                                   projects: Sequence[pvtags.Project]
#                                 ) -> Dict[Path, List[Graft]]:
#         """
#         Assign globbed files to all scanned grafts from engraves.
#
#         :param engrave_tuples:
#             a 3 tuple (engrave, mybase, otherbases)
#         """
#         def get_or_set_list(adict, key):
#             if key in adict:
#                 return adict[key]
#             adict[key] = v = []
#             return v
#
#         with self.errlog(IOError, token='fread') as errlog:
#             for eng, mybase, other_bases in engrave_tuples:
#                 with errlog(action=fpath):
#                     fpaths: FPaths = eng.collect_glob_files(mybase=mybase,
#                                                             other_bases=other_bases)
#                     log.debug("%s globbed %i files in '%s': %s",
#                               eng, len(fpaths), Path(mybase).resolve(),
#                               ', '.join(str(f) for f in fpaths))
#
#
#         hits: Dict[Path, List[Graft]] = odict(list)
#         for eng, mybase, other_bases in engrave_tuples:
#             for fp in fpaths:
#                 ## File-texts might have been loaded already.
#                 #
#                 get_or_set_list
#                 scanned_engraves = hits.get(fp)
#                 #if scanned_engraves:


    #     hits = [(engpaths, enghits)
    #             for eng in engraves
    #             for engpaths, enghits in eng.scan_hits().items()]


    #     ## Consolidate grafts-per-file in a single map.
    #     #
    #     hits_map: PathEngraves = odict()
    #     for fpath, fspec in hits:
    #         prev_fspec = hits_map.get(fpath)
    #         if prev_fspec:
    #             prev_fspec.grafts.extend(fspec.grafts)
    #         else:
    #             hits_map[fpath] = fspec
    #
    #     return hits_map

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

