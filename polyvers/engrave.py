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
from typing import List, Tuple, Sequence
import logging

from . import cmdlets, fileutils as fu, pvproject
from ._vendor.traitlets.traitlets import Bytes, Instance
from ._vendor.traitlets.traitlets import Dict as DictTrait


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



class FileProcessor(cmdlets.Spec):

    fpath_bytes_map: pvproject.FileBytes = DictTrait(key_trait=Instance(Path),
                                           value_trait=Bytes())
    match_map: pvproject.MatchMap = None
#                           DictTrait((Instance(Path),
#                                      TupleTrait((Instance(pvproject.Project),
#                                                  Instance(Engrave),
#                                                  Instance(Graft),
#                                                  Instance(Match)))))

    def _read_file(self, fpath: Path) -> pvproject.FileBytes:
        file_bytes = self.fpath_bytes_map.get(fpath.resolve(strict=True), None)
        if file_bytes is None:
            with self.errlogged(IOError,
                                token='fread',
                                doing="reading file '%s'" % fpath):
                path_bytes = self.fpath_bytes_map[fpath] = fpath.read_bytes()

        return path_bytes

    def _collect_project_globs(self,
                               project: pvproject.Project,
                               other_bases: pvproject.FLikeList = ()
                               ) -> pvproject.GlobTruples:
        mybase = project.basepath
        glob_truples: pvproject.GlobTruples = []
        for i, eng in enumerate(project.engraves):
            with self.errlogged(
                Exception, token='glob',
                doing="globbing %s engrave %i" % (project, i)
            ):
                globs = [project.interp(gs, _escaped_for='glob')
                         for gs in eng.globs]
                hit_fpaths = glob_files(
                    globs, mybase=mybase or '.', other_bases=other_bases)
                glob_truples.extend((project, eng, fp)
                                    for fp in hit_fpaths)

        return glob_truples

    def _delineate_glob_truples(self, gtruples: pvproject.GlobTruples
                                ) -> pvproject.GraftsMap:
        igtruples = defaultdict(list)
        for prj, eng, fpath in gtruples:
            igtruples[fpath].extend((prj, eng, graft)
                                    for graft in eng.grafts)
        return igtruples or {}

    def scan_projects(
            self, projects: Sequence[pvproject.Project]
    ) -> pvproject.MatchMap:
        other_bases = [prj.basepath for prj in projects
                       if prj.basepath]

        glob_truples: GlobTruples = []
        for i, prj in enumerate(projects):
            with self.errlogged(
                Exception, token='glob',
                doing="scanning %ith %s" % (i, prj)
            ):
                glob_truples.extend(
                    self._collect_project_globs(prj, other_bases))

        grafts_map = self._delineate_glob_truples(glob_truples)

        match_map = self.match_map = defaultdict(list)
        for i, (fpath, graft_spec) in enumerate(grafts_map.items()):
            fbytes = self._read_file(fpath)
            for prj, eng, graft in graft_spec:
                with self.errlogged(
                    Exception, token='scan',
                    doing="scanning %s graft %i" % (prj, i)
                ):
                    hits = graft.collect_graft_hits(fbytes)
                    valid_hits = graft.valid_hits(hits)
                    log.debug(
                        "Matched %i out of %i matches in file '%s' of pattern '%s'.",
                        len(valid_hits), len(hits), fpath, graft.regex)

                match_map[fpath].extend((prj, eng, graft, match)
                                        for match in hits)

        return match_map or {}

    def projects_with_grafts_matched(self,
                                     projects: Sequence[pvproject.Project]
                                     ) -> List[pvproject.Project]:
        """
        Replace grafts of project-engraves with populated matches.

        SIDE-EFFECT: project, engraves must be cloned
        """
#     def glob_files_from_engraves(self, engraves: "Sequence[Engrave]"
#                                  other_bases:FPaths = [prj.basepath for prj in projects]
#                                  ) -> List[Path]:
#
#         with self.errlogged(IOError,
#                          token='glob',
#                          doing="globbing projects") as errlog:
#             for prj in projects:
#                 with errlog(action=prj.pname):
#                     mybase = prj.basepath
#                     fpaths = prj.collect_glob_files(
#                         mybase=mybase, other_bases=other_bases)

#     def path_grafts_from_projects(self,
#                                   projects: Sequence[pvproject.Project]
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
#         with self.errlogged(IOError, token='fread') as errlog:
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

