#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
The main structures of *polyvers*::

    Project 1-->* Engrave 1-->* Graft
"""
from collections import OrderedDict as odict
from pathlib import Path
from typing import List, Dict, Optional, Union, Match, Tuple
import logging
import re

from . import polyverslib as pvlib, cmdlets
from ._vendor.traitlets import traitlets as trt
from ._vendor.traitlets.traitlets import (
    Bool, Unicode, Int, Instance,
    List as ListTrait, Tuple as TupleTrait, Union as UnionTrait)  # @UnresolvedImport
from .autoinstance_traitlet import AutoInstance
from .oscmd import cmd
from .slice_traitlet import Slice as SliceTrait


log = logging.getLogger(__name__)


FPaths = List[Path]
FLike = Union[str, Path]
FLikeList = List[FLike]


## TODO: Make Project printable.
class Project(cmdlets.Replaceable, cmdlets.Printable, cmdlets.Spec):
    pname = Unicode()
    basepath = Instance(Path, default_value=None, allow_none=True, castable=str)

    tag_vprefixes = TupleTrait(
        Unicode(), Unicode(),
        default_value=pvlib.tag_vprefixes,
        config=True,
        help="""
        A 2-tuple containing the ``{vprefix}`` interpolation values,
        one for *version-tags* and one for *release-tags*, respectively.
    """)

    pvtag_frmt = Unicode(
        help="""
        The pattern to generate new *pvtags*.

        It is interpolated with this class's traits as :pep:`3101` parameters;
        among others ``{pname}`` and ``{version}``; use ``{ikeys}`` to receive
        all available keys.

        .. WARNING::
           If you change this, ensure the :func:`polyversion.polyversion()`
           gets invoked from project's sources with the same value
           in `pvtag_frmt` kw-arg.
    """).tag(config=True)

    @trt.default('pvtag_frmt')
    def _tag_frmt_from_template(self):
        template_project = getattr(self.active_subcmd(), 'template_project', None)
        if template_project and template_project is not self:
            return template_project.pvtag_frmt
        return ''

    def tag_fnmatch(self, is_release=False):
        """
        The glob-pattern finding *pvtags* with ``git describe --match <pattern>`` cmd.

        :param is_release:
            `False` for version-tags, `True` for release-tags

        By default, it is interpolated with two :pep:`3101` parameters::

            {pname}   <-- this Project.pname
            {version} <-- '*'
        """
        vprefix = self.tag_vprefixes[int(is_release)]
        return self.interp(self.pvtag_frmt,
                           vprefix=vprefix,
                           version='*',
                           _escaped_for='glob')

    pvtag_regex = Unicode(
        help="""
        The regex pattern breaking *pvtags* and/or ``git-describe`` output
        into 3 named capturing groups:
        - ``pname``,
        - ``version`` (without the 'v'),
        - ``descid`` (optional) anything following the dash('-') after
          the version in ``git-describe`` result.

        It is interpolated with this class's traits as :pep:`3101` parameters;
        among others ``{pname}``, and **maybe** ``{version}``; use ``{ikeys}``
        to receive all available keys.
        See :pep:`0426` for project-name characters and format.

        .. WARNING::
           If you change this, ensure the :func:`polyversion.polyversion()`
           gets invoked from project's sources with the same value
           in `pvtag_regex` kw-arg.
    """).tag(config=True)

    @trt.validate('pvtag_regex')
    def _is_valid_pvtag_regex(self, proposal):
        value = proposal.value
        try:
            for vprefix in self.tag_vprefixes:
                re.compile(value.format(pname='<pname>', vprefix=vprefix))
        except Exception as ex:
            proposal.trait.error(None, value, ex)
        return value

    tag = Bool(
        config=True,
        help="""
        Enable tagging, per-project.

        Adds a signed tag with name/msg from `tag_name`/`message` (commit implied).

        """)
    sign_tags = Bool(
        config=True,
        help="Enable PGP-signing of tags (see also `sign_user`)."
    )

    sign_user = Unicode(
        config=True,
        help="The signing PGP user (email, key-id)."
    )

    message = Unicode(
        "chore(ver): bump {current_version} → {version}",
        config=True,
        help="""
            The message for commits and per-project tags.

            Available interpolations (apart from env-vars prefixed with '$'):
            {ikeys}
        """)

    def tag_regex(self, is_release=False):
        """
        Interpolate and compile as regex.

        :param is_release:
            `False` for version-tags, `True` for release-tags
        """
        vprefix = self.tag_vprefixes[int(is_release)]
        regex = self.interp(self.pvtag_regex,
                            vprefix=vprefix,
                            _escaped_for='regex')
        return re.compile(regex)

    _pvtags_collected = ListTrait(
        Unicode(), allow_none=True, default_value=None,
        help="Populated internally by `populate_pvtags_history()`.")

    @property
    def pvtags_history(self) -> List[str]:
        """
        Return the full *pvtag* history for the project, if any.

        :raise AssertionError:
           If used before :func:`populate_pvtags_history()` applied on this project.
        """
        if self._pvtags_collected is None:
            raise AssertionError("Call first `populate_pvtags_history()` on %s!")
        return self._pvtags_collected

    def version_from_pvtag(self, pvtag: str) -> Optional[str]:
        """Extract the version from a *pvtag*."""
        m = self.tag_regex().match(pvtag)
        if m:
            mg = m.groupdict()
            if mg['descid']:
                log.warning(
                    "Ignoring pvtag '%s', it has `git-describe` suffix '%s'!",
                    pvtag, mg['descid'])

            return mg['version']

    def git_describe(self, *git_args: str,
                     include_lightweight=False,
                     is_release=False,
                     **git_flags: str):
        """
        Gets sub-project's version as derived from ``git describe`` on its *pvtag*.

        :param include_lightweight:
            Consider also non-annotated tags when derriving description;
            equivalent to ``git describe --tags`` flag.
        :param is_release:
            `False` for version-tags, `True` for release-tags
        :param git_args:
            CLI options passed to ``git describe`` command.
            See :class:`.oscmd.PopenCmd` on how to specify cli options
            using python functions, e.g. ``('*-v*', '*-r*')``
        :param git_flags:
            CLI flags passed to ``git describe`` command.
            - See :class:`.oscmd.PopenCmd` on how to specify cli flags
              using python functions, e.g. ``(all=True)``.
            - See https://git-scm.com/docs/git-describe
        :return:
            the *pvtag* of the current project, or raise
        :raise GitVoidError:
            if sub-project is not *pvtagged*.
        :raise NoGitRepoError:
            if CWD not within a git repo.
        :raise sbp.CalledProcessError:
            for any other error while executing *git*.

        .. NOTE::
           There is also the python==2.7 & python<3.6 safe :func:`polyvers.polyversion()``
           for extracting just the version part from a *pvtag*; use this one
           from within project sources.

        .. INFO::
           Same results can be retrieved by this `git` command::

               git describe --tags --match <PROJECT>-v*

           where ``--tags`` is needed to consider also non-annotated tags,
           as ``git tag`` does.
        """
        from . import pvtags

        pname = self.pname
        tag_pattern = self.tag_fnmatch(is_release)

        acli = cmd.git.describe
        if include_lightweight:
            acli._(tags=True)

        with pvtags.git_errors_handled(pname):
            out = acli._(*git_args, **git_flags)(match=tag_pattern)

        version = out

        ## `git describe --all` fetches 'tags/` prefix.
        if 'all' in git_flags:
            version = version.lstrip('tags/')

        if not self.version_from_pvtag(version):
            raise trt.TraitError(
                "Project-version '%s' fetched by '%s' unparsable by regex: %s"
                % (version, tag_pattern, self.tag_regex().pattern))

        return version

    def last_commit_tstamp(self):
        """
        Report the timestamp of the last commit of the git repo.

        :return:
            last commit's timestamp in :rfc:`2822` format

        :raise GitVoidError:
            if there arn't any commits yet or CWD not within a git repo.
        :raise sbp.CalledProcessError:
            for any other error while executing *git*.

        .. INFO::
           Same results can be retrieved by this `git` command::

               git describe --tags --match <PROJECT>-v*

           where ``--tags`` is needed to consider also unannotated tags,
           as ``git tag`` does.
        """
        from . import pvtags

        with pvtags.git_errors_handled(self.pname):
            out = cmd.git.log(n=1, format='format:%cD')  # TODO: traitize log-date format

        return out


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
        help="What to search"
    )

    @trt.validate('regex')
    def _is_valid_regex(self, proposal):
        value = proposal.value
        try:
            v = self.interpolations.interp(value,
                                           self,
                                           _stub_keys=lambda k: '<%s>' % k)
            re.compile(v)
        except Exception as ex:
            proposal.trait.error(None, value, ex)
        return value

    @property
    def regex_resolved(self):
            v = self.interpolations.interp(self.regex, self)
            return re.compile(v)

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

    def collect_graft_hits(self, ftext: str) -> 'Graft':
        """
        :return:
            a clone with updated `hits`
        """
        regex = self.regex_resolved
        hits: List[Match] = list(regex.finditer(ftext))
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

    def substitute_graft_hits(self, fpath: Path, ftext: str) -> Tuple[str, 'Graft']:
        """
        :return:
            A 2-TUPLE ``(<substituted-ftext>, <updated-graft>)``, where
            ``<updated-graft>`` is a *possibly* clone with updated
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
        from . import engrave
        return engrave.glob_files(self.globs, mybase, other_bases)

    def collect_file_hits(self) -> 'Engrave':
        """
        :return:
            a clone with `grafts` updated
        """
        new_grafts: List[Graft] = []
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
