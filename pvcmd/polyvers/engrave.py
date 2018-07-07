#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Search and replace version-ids in files."""

from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, Sequence, Set, Match, Dict
import logging

from . import pvproject
from ._vendor.traitlets.traitlets import (
    Dict as DictTrait, Bool as BoolTrait, Tuple as TupleTrait)
from ._vendor.traitlets.traitlets import Bytes, Instance
from .cmdlet import cmdlets
from .utils import fileutil as fu


log = logging.getLogger(__name__)


def _as_glob_pattern_pair(fpath):
    """24
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
        ## Keep bases only inside mybase, but
        # Exclude bases coinciding with mybase.
        #
        other_ppaths = [Path(ob) for ob in other_bases]
        other_ppaths = [ob for ob in other_ppaths
                        if not fu._is_same_file(mybase, ob) and
                        fu._is_base_or_same(mybase, ob)]
        files = _glob_filter_out_other_bases(files, other_ppaths)

    assert all(isinstance(f, Path) for f in files)
    return files


Range = Tuple[int, int]


def overlapped_matches(matches: Sequence[Match],
                       no_touch=False,
                       ) -> Set[Match]:
    """
    :param no_touch:
        if true, all three (0,1), (1,2) (2,3) overlap on 1 and 2.
    """
    import itertools as itt
    import operator

    op = operator.le if no_touch else operator.lt

    def overlap(a, b) -> Set[Match]:
        # from https://stackoverflow.com/a/3269471/548792
        return op(a[0], b[1]) and op(b[0], a[1])

    all_pairs = itt.combinations(matches, 2)
    overlapped: Set[Match] = set()
    for m1, m2 in all_pairs:
        if m1 not in overlapped and overlap(m1.span(), m2.span()):
            overlapped.add(m2)

    return overlapped


GlobTruples = List[Tuple[pvproject.Project, pvproject.Engrave, Path]]
GraftsMap = Dict[Path, List[Tuple[pvproject.Project,
                                  pvproject.Engrave,
                                  pvproject.Graft]]]
MatchQruple = Tuple[pvproject.Project,
                    pvproject.Engrave,
                    pvproject.Graft,
                    Match]
MatchMap = Dict[Path, List[MatchQruple]]


class FileProcessor(cmdlets.Spec):

    _fpath_bytes: Dict[Path, Tuple[bytes, bool]] = DictTrait(  # type: ignore
        key_trait=Instance(Path),
        value_trait=TupleTrait(Bytes(),
                               BoolTrait()))

    def _set_file_bytes(self, fpath: Path, fbytes: bytes) -> bytes:
        key = fpath.resolve(strict=True)
        if key in self._fpath_bytes:
            orig_fbytes, _changed = self._fpath_bytes[key]
            changed = fbytes != orig_fbytes
        else:
            ## Just read file.
            changed = False
        self._fpath_bytes[key] = (fbytes, changed)

        return fbytes

    def _read_file(self, fpath: Path) -> bytes:
        key = fpath.resolve(strict=True)
        fbytes, _changed = self._fpath_bytes.get(key, (None, None))
        if fbytes is None:
            with self.errlogged(OSError,
                                token='fread',
                                doing="reading file '%s'" % fpath):
                fbytes = self._set_file_bytes(fpath, fpath.read_bytes())
                self.log.debug("Read %i-bytes from file-to-engrave '%s'.",
                               len(fbytes), fpath)

        return fbytes

    def _write_all_files(self):
        for fpath, (fbytes, changed) in self._fpath_bytes.items():
            if not changed:
                self.log.debug("Skipped untouched file '%s'.", fpath)
                continue

            if not self.dry_run:
                with self.errlogged(OSError,
                                    token='fwrite',
                                    doing="writing file '%s'" % fpath):
                    fpath.write_bytes(fbytes)

            self.log.info("Written %i-bytes in engraved file '%s'.",
                          len(fbytes), fpath)

    match_map: MatchMap = DictTrait(key_trait=Instance(Path))  # type: ignore
#                                     TupleTrait((Instance(pvproject.Project),
#                                                 Instance(Engrave),
#                                                 Instance(Graft),
#                                                 ListTrait(Instance(Match))))))

    def nmatches(self):
        return sum(len(qruple) for qruple in self.match_map.values())

    def grafted_files(self, all_searched=False) -> List[Path]:
        return sorted(fpath
                      for fpath, (_fbytes, changed)
                      in self._fpath_bytes.items()
                      if all_searched or changed)

    def _glob_project(self,
                      project: pvproject.Project,
                      other_bases: pvproject.FLikeList = ()
                      ) -> GlobTruples:
        mybase = project.basepath
        glob_truples: GlobTruples = []
        for eng in project.active_engraves():
            with self.errlogged(
                token='glob',
                doing="globbing %.28s%s" % (eng, eng.globs)
            ):
                globs = [project.interp(gs, _escaped_for='glob')
                         for gs in eng.globs
                         if gs is not None]
                hit_fpaths = glob_files(  # type: ignore # (interp may be null)
                    globs, mybase=mybase or '.', other_bases=other_bases)
                glob_truples.extend((project, eng, fp)
                                    for fp in hit_fpaths)

        return glob_truples

    def _reindex_glob_results_on_fpaths(self, gtruples: GlobTruples
                                        ) -> GraftsMap:
        igtruples: GraftsMap = defaultdict(list)
        for prj, eng, fpath in gtruples:
            igtruples[fpath].extend((prj, eng, graft)
                                    for graft in eng.grafts)
        return igtruples or {}

    def _glob_all_projects(self,
                           projects: Sequence[pvproject.Project],
                           all_projects: Sequence[pvproject.Project]
                           ) -> GraftsMap:
        other_bases = [prj.basepath for prj in all_projects if prj.basepath]
        glob_truples = []
        for prj in projects:
            with self.errlogged(token='glob',
                                doing="globbing %.28s" % prj):
                glob_truples.extend(self._glob_project(prj, other_bases))

        return self._reindex_glob_results_on_fpaths(glob_truples)

    def _scan_all_grafts(self, grafts_map: GraftsMap) -> MatchMap:
        match_map: MatchMap = defaultdict(list)
        for fpath, graft_truple in grafts_map.items():
            fbytes = self._read_file(fpath)
            for prj, eng, graft in graft_truple:
                with self.errlogged(token='scan',
                                    doing="scanning '%s' for %.28s.%.28s" %
                                    (fpath, prj, eng)):
                    matches = graft.collect_matches(fbytes, prj)
                    self.log.debug(
                        "Scanned %i matches in %i-bytes text of file '%s': "
                        "\n  matches: %s\n  %s\n  %s \n  %s",
                        len(matches), len(fbytes), fpath,
                        '\n    '.join(str(m) for m in [''] + matches),  # type: ignore
                        graft, eng, prj)

                    sliced_matches = graft.sliced_matches(matches)
                    if len(sliced_matches) != len(matches):
                        self.log.debug(
                            "Sliced %i out of %i matches in file '%s' for %s.",
                            len(sliced_matches), len(matches), fpath, graft)

                match_map[fpath].extend((prj, eng, graft, m)
                                        for m in matches)

        return match_map or {}

    def _drop_overlapping_matches(self, match_map: MatchMap) -> MatchMap:
        """Sorts also matches on the starting-points."""
        good_match_map = {}
        for fpath, mqruples in match_map.items():
            mqruples = sorted(mqruples, key=lambda mq: mq[-1].start())
            all_file_matches = [mq[-1] for mq in mqruples]

            bad_matches = overlapped_matches(all_file_matches, no_touch=True)
            if bad_matches:
                self.log.debug(
                    "Found %i out of %i overlapping matches for file '%s'."
                    "\n  Overlaps: %s",
                    len(bad_matches), len(all_file_matches), fpath,
                    ', '.join(str(s) for s in bad_matches))

            good_match_map[fpath] = [mq
                                     for mq in mqruples
                                     if mq[-1] not in bad_matches]

        return good_match_map

    def scan_projects(self,
                      projects: Sequence[pvproject.Project],
                      all_projects: Sequence[pvproject.Project] = None
                      ) -> MatchMap:
        assert projects
        grafts_map = self._glob_all_projects(projects, all_projects or projects)
        match_map = self._scan_all_grafts(grafts_map)
        match_map = self._drop_overlapping_matches(match_map)

        self.match_map = match_map

        return match_map

    def _graft_match(self,
                     graft: pvproject.Graft,
                     fbytes: bytes,
                     match: Match,
                     offset: int,
                     project: 'pvproject.Project',
                     ) -> Tuple[bytes, int]:
        """
        :param graft:
            a graft with a non-null :attr:`pvproject.Graft.subst`
        :return:
            the substituted fbytes
        """
        subst = graft.subst_resolved(project)
        if subst is not None:
            mstart, mend = match.span()
            new_text = match.expand(subst)
            head = fbytes[:mstart + offset]
            tail = fbytes[mend + offset:]
            fbytes = head + new_text + tail
            offset += len(new_text) - (mend - mstart)

        return fbytes, offset

    def engrave_matches(self):
        match_map = self.match_map
        for fpath, mqruples in match_map.items():
            if not mqruples:
                continue

            fbytes = self._read_file(fpath)
            offset = 0  # File growth/shrink as substituted?
            for prj, eng, graft, match in (mq
                                           for mq in mqruples
                                           if mq[2].subst):
                with self.errlogged(token='subst',
                                    doing="subst '%s' with %.28s.%.28s.%.28s.%.28s" %
                                    (fpath, prj, eng, graft, match)):

                    fbytes, offset = self._graft_match(
                        graft, fbytes, match, offset, prj)
                    self.log.debug(
                        "Substituted match in %i(%+i)-bytes file '%s': "
                        "\n  %s\n  %s\n  %s \n  %s",
                        len(fbytes), offset, fpath,
                        match, graft, eng, prj)

            self._set_file_bytes(fpath, fbytes)

        self._write_all_files()
