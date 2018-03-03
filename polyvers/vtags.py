#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Python code to report sub-project "vtags" in Git *polyvers* monorepos."""

from collections import defaultdict
import logging
import os
from pathlib import Path

import subprocess as sbp

from . import polyverslib, cmdlets
from . import oscmd
from ._vendor.traitlets.traitlets import Bool, Unicode, CRegExp, Instance


log = logging.getLogger(__name__)


class GitVoidError(cmdlets.CmdException):
    "Sub-project has not yet been version with a *vtag*. "
    pass


class Project(cmdlets.Spec):
    pname = Unicode()
    basepath = Instance(Path, castable=str)

    vtag_fnmatch_frmt = Unicode(
        default_value=polyverslib.vtag_fnmatch_frmt,
        help="""
        The default pattern globbing for *vtags* with ``git describe --match <pattern>``.

        .. WARNING::
            If you change this, remember to invoke :func:`polyversion.polyversion()`
            with the changed value on `vtag_fnmatch_frmt` kwarg from project's sources.
    """).tag(config=True)

    vtag_regex = CRegExp(
        default_value=polyverslib.vtag_regex,
        help="""
        The default regex pattern breaking *vtags* and/or ``git-describe`` output
        into 3 named capturing groups:
        - ``project``,
        - ``version`` (without the 'v'),
        - ``descid`` (optional) anything following the dash('-') after
          the version in ``git-describe`` result.

        See :pep:`0426` for project-name characters and format.

        .. WARNING::
            If you change this, remember to invoke :func:`polyversion.polyversion()`
            with the changed value on `vtag_regex` kwarg from project's sources.
    """).tag(config=True)

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
        "chore(ver): bump {{current_version}} → {{new_version}}",
        config=True,
        help="""
            The message for commits and per-project tags.

            Available interpolations (apart from env-vars prefixed with '$'):
            {ikeys}
        """)

    def find_all_subproject_vtags(self, *projects):
        """
        Return the all ``proj-v0.0.0``-like tags, per project, if any.

        :param projects:
            project-names; fetch all vtags if none given.
        :return:
            a {proj: [vtags]}, possibly incomplete for projects without any vtag
        :raise subprocess.CalledProcessError:
            if `git` executable not in PATH
        """
        tag_patterns = [self.vtag_fnmatch_frmt % p
                        for p in projects or ('*', )]
        cmd = 'git tag --merged HEAD -l'.split() + tag_patterns
        res = oscmd.exec_cmd(cmd, check_stdout=True, check_stderr=True)
        out = res.stdout
        tags = out and out.strip().split('\n') or []

        project_versions = defaultdict(list)
        for t in tags:
            m = self.vtag_regex.match(t)
            if m:
                mg = m.groupdict()
                if mg['descid']:
                    log.warning(
                        "Ignoring vtag '%s', it has `git-describe` suffix '%s'!",
                        t, mg['descid'])
                else:
                    project_versions[mg['project']].append(mg['version'])

        return project_versions

    def get_subproject_versions(self, *projects):
        """
        Return the last vtag for any project, if any.

        :param projects:
            project-names; return any versions found if none given.
        :return:
            a {proj: version}, possibly incomplete for projects without any vtag
        :raise subprocess.CalledProcessError:
            if `git` executable not in PATH
        """
        vtags = self.find_all_subproject_vtags(*projects)
        return {proj: (versions and versions[-1])
                for proj, versions in vtags.items()}

    def git_describe(self):
        """
        Gets sub-project's version as derived from ``git describe`` on its *vtag*.

        :return:
            the *vtag* of the current project, or raise
        :raise GitVoidError:
            if sub-project is not *vtagged* or CWD not within a git repo.
        :raise sbp.CalledProcessError:
            for any other error while executing *git*.

        .. NOTE::
           There is also the python==2.7 & python<3.6 safe :func:`polyvers.polyversion()``
           for extracting just the version part from a *vtag*; use this one
           from within project sources.

        .. INFO::
           Same results can be retrieved by this `git` command::

               git describe --tags --match <PROJECT>-v*

           where ``--tags`` is needed to consider also unannotated tags,
           as ``git tag`` does.
        """
        project = self.pname
        vtag = None
        tag_pattern = self.vtag_fnmatch_frmt % project
        cmd = 'git describe --tags --match'.split() + [tag_pattern]
        try:
            res = oscmd.exec_cmd(cmd, check_stdout=True, check_stderr=True)
            out = res.stdout
            vtag = out and out.strip()

            return vtag
        except sbp.CalledProcessError as ex:
            err = ex.stderr
            if "does not have any commits yet" in err or "No names found" in err:
                raise GitVoidError(
                    "No *vtag* for sub-project '%s'!" % project) from ex
            elif "Not a git repository" in err:
                raise GitVoidError(err) from ex
            else:
                raise

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
        cdate = None
        try:
            log_cmd = "git log -n1 --format=format:%cD".split()
            res = oscmd.exec_cmd(log_cmd, check_stdout=True, check_stderr=True)
            out = res.stdout
            cdate = out and out.strip()

            return cdate
        except sbp.CalledProcessError as ex:
            err = ex.stderr
            if "does not have any commits yet" in err:
                raise GitVoidError("No commits yet!") from ex
            elif 'Not a git repository' in err:
                raise GitVoidError(
                    "Current-dir '%s' is not within a git repository!" %
                    os.curdir) from ex
            else:
                raise
