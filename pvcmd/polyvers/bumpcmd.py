# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""The command that actually bumps versions."""
from typing import Sequence, Optional
from typing import Tuple, Set, List  # noqa: F401 @UnusedImport, flake8 blind in funcs

from boltons.setutils import IndexedSet as iset

import polyversion as pvlib

from . import NOTICE, pvtags, pvproject, cli
from ._vendor.traitlets.traitlets import Bool, Unicode
from .cmdlet import cmdlets
from .utils import fileutil as fu
from .utils.oscmd import cmd


class BumpCmd(cli._SubCmd):
    """
    Increase or set the version of project(s) to the (relative/absolute) version.

    SYNTAX:
        {cmd_chain} [OPTIONS] [<version> | --amend] [<project>]...

    - If no project(s) specified, increase the versions on all projects.
    - Denied if version for some projects is backward-in-time (or has jumped parts?);
      use --force if you might.

    VERSION:
    - A version specifier, either ABSOLUTE, or RELATIVE to the
    current version og each project:

      - *ABSOLUTE* PEP-440 version samples:
        - Pre-releases: when working on new features:
            X.YbN               # Beta release
            X.YrcN  or  X.YcN   # Release Candidate
            X.Y                 # Final release
        - Post-release:
            X.YaN.postM         # Post-release of an alpha release
            X.YrcN.postM        # Post-release of a release candidate
        - Dev-release:
            X.YaN.devM          # Developmental release of an alpha release
            X.Y.postN.devM      # Developmental release of a post-release

      - *RELATIVE* samples:
        - +0.1          #       1.2.3     --> 1.3.0
        - +0.0.3a2      #       1.2.3a3   --> 1.2.6a5
        - +3b1.dev2     #       1.2.3a3   --> 4.2.3b1.dev2
        - +b1.dev2      #       <VersioError:  relver missing release-tuple prefix>

        - ^2            ## Increases by +2 the last part of current version,
                        #  in that order: release-tuple, pre, post, dev
                        #  Example::
                        #       0.2       --> 0.4
                        #       0.0.0     --> 0.0.2
                        #       1.2.3     --> 1.2.5
                        #       0.1.0b0   --> 0.1.0b2
        - ^0            #       0.2b2     --> 0.2
        - ^1.2          #       0.5.0     --> 0.5.1.2
                        #       1.2a0     --> 1.2a1.post2
        - ^1.2.3        #       1.2a0     --> 1.2a1.post2.dev3
        - ^1.2          #       1.2.post1 --> 1.2.post2.dev2
        - ^1.2.3        #       1.2.post1 --> <VersionError: parts exhausted>

        - ^+a_b-cd      ## Increased by a "local" identifier::
                        #       1.2.3     --> 1.2.3+a.b.cd

      - If no <version> specified, each project specifies its default
        (by default '^1').
      - Don't add a 'v' prefix in the version!

    GRAMMAR (TODO):
        ver       := ( oepoch '!' )? release? opre? opost? odev? ( '+' local')?
        oepoch    := op? epoch
        epoch     := DIGIT+
        release   := onum ( '.' onum )*
        onum      := op? DIGIT+
        opre      := op? pre
        opost     := op? post
        odev      := op? dev
        op        := ( '+' | '^' | '=' ) '?'?            # '=' if missing

       - spaces are not allowed
       - see PEP440 for the grammar of <pre>, <post>, <dev>, <local>
    """

    classes = [pvproject.Project, pvproject.Engrave, pvproject.Graft]  # type: ignore

    amend = Bool(
        config=True,
        help="""
        Amend the last version tag of the project, don't bump
        (one older version assumed)"""
    )

    engrave_only = Bool(
        config=True,
        help="Don't commit/tag after engraving; good for debugging engravings"
    )

    engrave_bumped_only = Bool(
        config=True,
        help="""
        "Don't engrave projects not involved in the bump.

        When true, it leaves those projects in the release-commits with the code
        to auto-derive their version, instead of engraving them with version
        having possibly a local-part.
        """
    )

    out_of_trunk_releases = Bool(
        True,
        config=True,
        help="""
            Version-ids statically engraved in-trunk when true, otherwise in "leaf" commits.

            - Limit branches considered as "in-trunk" using `in_trunk_branches` param.
            - Select the name of the Leaf branch with `leaf_branch` param.

            Leaf release-commits avoid frequent merge-conflicts in files containing
            the version-ids.
    """)

    release_branch = Unicode(
        'latest',
        config=True,
        help="""
        Branch-name where the release-tags must be created under.

        - The branch will be hard-reset to the *out-of-trunk* commit
          on each bump-version.
        - If not given, no special branch used for *rtags*.
        """
    )

    commit = Bool(
        config=True,
        help="""
            Commit after engraving with a commit-message describing version bump.

            - If false, no commit created, just search'n replace version-ids.
              Related params: out_of_trunk, message.
            - False make sense only if `use_leaf_releases=False`
        """)

    message_summary = Unicode(
        "chore(ver): bump {sub_summary}",
        config=True,
        help="""
            The commit & tag message's summary-line.

            - Additional interpolation: `sub_summary`
            - Others interpolations (apart from env-vars prefixed with '$'):
              {ikeys}
        """)

    message_body = Unicode(
        "{sub_body}",
        config=True,
        help="""
            The commit & tag message's body.

            - Additional interpolation: `sub_body`
            - Others interpolations (apart from env-vars prefixed with '$'):
              {ikeys}
        """)

    sign_tags = Bool(
        allow_none=True,
        config=True,
        help="Enable PGP-signing of tags (see also `sign_user`)."
    )

    sign_commmits = Bool(
        allow_none=True,
        config=True,
        help="Enable PGP-signing of *rtag* commits (see also `sign_user`)."
    )

    sign_user = Unicode(
        allow_none=True,
        config=True,
        help="The signing PGP user identity (email, key-id)."
    )

    def _stop_if_git_dirty(self):
        """
        Note: ``git diff-index --quiet HEAD --``
        from https://stackoverflow.com/a/2659808/548792
        give false positives!
        """
        ## TODO: move all git-cmds to pvtags?
        out = cmd.git.describe(dirty=True, all=True)
        if out.endswith('dirty'):
            raise pvtags.GitError("Dirty working directory, bump aborted.")

    def _filter_projects_by_pnames(self, projects, version, *pnames):
        """Separate `version` from `pnames`, scream if unknown pnames."""
        if pnames:
            all_pnames = [prj.pname for prj in projects]
            pnames = iset(pnames)
            unknown_projects = (pnames - iset(all_pnames))
            if unknown_projects:
                raise cmdlets.CmdException(
                    "Unknown project(s): %s\n  Choose from existing one(s): %s" %
                    (', '.join(unknown_projects), ', '.join(all_pnames)))

            projects = [p for p in projects
                        if p.pname in pnames]

        return version, projects

    def _make_commit_message(self, *projects: pvproject.Project,
                             is_release=False):
        from ipython_genutils.text import indent, wrap_paragraphs

        sub_summary = ', '.join(prj.interp(prj.summary_interped(is_release))  # type: ignore # none
                                for prj in projects)
        summary = self.interp(self.message_summary, sub_summary=sub_summary)

        text_lines: List[str] = []
        for prj in projects:
            if prj.message_body:
                text_lines.append('- %s' % prj.pname)
                text_lines.append(indent(wrap_paragraphs(prj.message_body), 2))

        sub_body = '\n'.join(text_lines).strip()
        body = self.interp(self.message_body, sub_body=sub_body)

        return '%s\n\n%s' % (summary, body)

    def _commit_new_release(self, msg,
                            projects: Sequence[pvproject.Project]):
        ## TODO: move all git-cmds to pvtags?
        out = cmd.git.commit(message=msg,  # --message=fo bar FAILS!
                             all=True,
                             sign=self.sign_commmits or None,
                             dry_run=self.dry_run or None,
                             allow_empty=True  # empty when no engraves!
                             )
        if self.dry_run:
            self.log.warning('PRETEND commit: %s' % out)

    def _prepare_project_for_bump(self, prj: pvproject.Project,
                                  version_bump: Optional[str],
                                  is_to_bump: bool):
        if is_to_bump:
            prj.load_current_version_from_history()
            if self.amend:
                assert not version_bump, (
                    "cmd.run() checks that no ver given: %s" % version_bump)
                version_bump = prj.current_version
                prj.load_current_version_from_history(1)

            ## Scream if version-bump fails pep440 validation.
            prj.set_new_version(version_bump)
        else:
            ## TODO: parse Project.git_describe() instead of calling polyversion(non_bumped)!
            latest_version = pvlib.polyversion(
                pname=prj.pname,
                tag_format=prj.pvtag_format,
                tag_regex=prj.pvtag_regex,
                vprefixes=prj.tag_vprefixes,
                basepath=prj.basepath
            )
            prj.version = latest_version

    def _log_action_completed(self, projects, fproc):
        if self.log.isEnabledFor(NOTICE):
            git_root = self.git_root.resolve(strict=True)
            enfiles = fproc.grafted_files()
            enfiles_desc = '\n    - '.join(
                str(f.relative_to(git_root)) for
                f in enfiles)
            projver_desc = '\n    - '.join(
                '%s-%s --> %s' % (prj.pname, prj.current_version, prj.version)
                for prj in projects)
            action = "Engraved" if self.engrave_only else "Bumped"
            self.log.notice(
                "%s%s projects: \n    - %s\n  with %s grafts in %s files"
                " (out of %s files globbed): "
                "\n    - %s",
                'PRETEND ' if self.dry_run else '',
                action,
                projver_desc,
                fproc.nmatches(),
                len(enfiles),
                len(fproc.grafted_files(all_searched=True)),
                enfiles_desc)

    def run(self, *version_and_pnames):
        from . import engrave

        projects = self.bootstrapp_projects()
        if version_and_pnames:
            if self.amend:
                ## When --amend, no version accepted.
                version_and_pnames = (None, ) + version_and_pnames
            version_bump, bump_projects = self._filter_projects_by_pnames(
                projects, *version_and_pnames)
        else:
            version_bump = None
            bump_projects = projects

        engrave_projects = (bump_projects
                            if self.engrave_bumped_only else
                            projects)

        pvtags.populate_pvtags_history(*bump_projects)
        for prj in engrave_projects:
            self._prepare_project_for_bump(prj,
                                           version_bump,
                                           prj in bump_projects)

        fproc = engrave.FileProcessor(parent=self)
        if not self.engrave_only:
            ## Cancel --dry-run when doing a "real" bump,
            #  because Git will rollback the changes.
            fproc.dry_run = False

        git_root = self.git_root.resolve(strict=True)
        with fu.chdir(git_root):
            fproc.scan_projects(engrave_projects, projects)

        if fproc.nmatches() == 0:
            ## FIXME: check each project specifically for engraves.
            with self.errlogged(
                    doing="checking if at least one version-engraving happened",
                    token='noengraves'):
                raise cmdlets.CmdException(
                    "No version-engravings happened, bump aborted.")

        if self.engrave_only:
            with fu.chdir(git_root):
                fproc.engrave_matches()
            self._log_action_completed(engrave_projects, fproc)
            return

        ## Finally stop before serious damage happens,
        #  (but only after havin run some validation to run, above).
        self._stop_if_git_dirty()

        with pvtags.git_restore_point(restore_head=self.dry_run):
            with fu.chdir(git_root):
                fproc.engrave_matches()

            ## TODO: move all git-cmds to pvtags?
            if self.out_of_trunk_releases:
                for proj in bump_projects:
                    msg = self._make_commit_message(*bump_projects, is_release=False)
                    proj.tag_version_commit(
                        msg, is_release=False, amend=self.amend,
                        sign_tag=self.sign_tags,
                        sign_user=self.sign_user)

                with pvtags.git_restore_point(restore_head=True,
                                              heads=False, tags=False):
                    if self.release_branch:
                        cmd.git.checkout._(B=True)(self.release_branch)
                    else:
                        cmd.git.checkout('HEAD')

                    msg = self._make_commit_message(*bump_projects, is_release=True)
                    self._commit_new_release(msg, bump_projects)

                    for proj in bump_projects:
                        msg = self._make_commit_message(*bump_projects, is_release=True)
                        proj.tag_version_commit(
                            msg, is_release=True, amend=self.amend,
                            sign_tag=self.sign_tags,
                            sign_user=self.sign_user)

            else:  # In-trunk plain *vtags* for mono-project repos.
                msg = self._make_commit_message(*bump_projects, is_release=False)
                self._commit_new_release(msg, bump_projects)

                for proj in bump_projects:
                    proj.tag_version_commit(
                        self,
                        msg, is_release=False,
                        amend=self.amend,
                        sign_tag=self.sign_tags,
                        sign_user=self.sign_user)

        self._log_action_completed(bump_projects, fproc)

    # def start(self):
    #     with self.errlogged(doing="running cmd '%s'" % self.name,
    #                         info_log=self.log.info):
    #         return super().start()


BumpCmd.flags = {  # type: ignore
    ('c', 'commit'): (
        {'BumpCmd': {'commit': True}},
        BumpCmd.commit.help
    ),
    ('s', 'sign-tags'): (
        {'BumpCmd': {'sign_tags': True}},
        BumpCmd.sign_tags.help
    ),
    ('a', 'amend'): (
        {'BumpCmd': {'amend': True}},
        BumpCmd.amend.help
    ),
    ('e', 'engrave-only'): (
        {'BumpCmd': {'engrave_only': True}},
        BumpCmd.engrave_only.help
    ),
    ('t', 'tag'): (
        {'Project': {'tag': True}},
        pvproject.Project.tag.help
    ),
}
BumpCmd.aliases = {  # type: ignore
    ('m', 'message'): 'BumpCmd.message_body',
    ('i', 'sign-user'): 'BumpCmd.sign_user',
}
