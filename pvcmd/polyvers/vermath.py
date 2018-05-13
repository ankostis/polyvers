#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Validate and do algebra operations on Version-ids."""
from typing import Union
import re

from packaging.version import Version, _parse_letter_version

import itertools as itt

from ._vendor.traitlets import traitlets as trt
from .cmdlet import cmdlets


VerLike = Union[str, Version]


class VersionError(cmdlets.CmdException):
    pass


class Pep440Version(trt.Instance):
    """A trait parsing text like python "slice" expression (ie ``-10::2``)."""
    klass = Version
    _cast_types = str  # type: ignore

    def cast(self, value):
        return Version(str(value))


#: Possible to skip release-numbers, no local-part.
#: Adapted from :data:`packaging.VERSION_PATTERN`.
_relative_ver_regex = re.compile(r"""(?ix)
    (?:
        (?P<op>[+^])                                      # relative operator
        (?P<freeze>=?)                                    # freeze marker
        (?P<release>[0-9]+(?:\.[0-9]+)*)?                 # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    """)


def is_version_id_relative(version_str: VerLike):
    return _relative_ver_regex.match(str(version_str)) is not None


def _add_pre(base_tuple, rel_label, rel_num):
    assert base_tuple is not None or rel_label is not None, (
        base_tuple, rel_label, rel_num)
    if not rel_label:
        return base_tuple

    blabel, bnum = base_tuple or (None, 0)
    rlabel, rnum = _parse_letter_version(rel_label, rel_num)

    if blabel == rlabel:
        return blabel, bnum + rnum
    else:
        return rlabel, rnum


def _add_versions(base_ver: VerLike, relative_ver):
    bver = base_ver if isinstance(base_ver, Version) else Version(base_ver)
    m = _relative_ver_regex.match(str(relative_ver))
    if not m:
        raise VersionError("Invalid relative version: {}".format(relative_ver))

    op = m.group('op')
    freeze = m.group('freeze')

    ver_nums = list(bver.release)
    rel_release = m.group('release')
    if rel_release:
        #
        ## Caret(^) makes a difference only for release-digits.

        rel_nums = [int(d) for d in rel_release.split('.')]
        if op == '^':
            ##  Extend caret version from base-version's last digit.
            #
            ver_nums[-1] += rel_nums[0]
            ver_nums.extend(rel_nums[1:])
        elif op == '+':
            ver_nums = [a + b
                        for a, b in itt.zip_longest(ver_nums, rel_nums, fillvalue=0)]
        else:
            raise AssertionError(op)

    parts = ['.'.join(str(i) for i in ver_nums)]

    ## Clear base pre/post/dev parts if release-tuple bumped
    ## and relative-version is not "freezed" (like '+=1').
    keep_bparts = freeze or not rel_release

    if m.group('pre') or keep_bparts and bver.pre:
        parts.append('%s%s' % _add_pre(bver.pre,
                                       m.group('pre_l'),
                                       m.group('pre_n')))

    if m.group('post') or keep_bparts and bver.post:
        rel_post = m.group('post_n1') or m.group('post_n2') or 0
        new_post = (bver.post or 0) + int(rel_post)
        parts.append(".post%s" % new_post)

    if m.group('dev') or keep_bparts and bver.dev:
        new_dev = (bver.dev or 0) + int(m.group('dev_n') or 0)
        parts.append(".dev%s" % new_dev)

    if bver.local:
        parts.append('+' + bver.local)

    new_version = ''.join(parts)

    return Version(new_version)


def add_versions(v1: VerLike, v2: VerLike) -> Version:
    """return the "sum" of the the given two versions."""
    new_version = _add_versions(v1, v2)

    v1 = Version(v1)
    if new_version < v1:
        raise VersionError("Backward bump is forbidden: %s -/-> %s" %
                           (v1, new_version))
    return new_version
