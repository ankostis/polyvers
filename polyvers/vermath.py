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

from packaging.version import Version

from . import cmdlets
from ._vendor.traitlets import traitlets as trt


VerLike = Union[str, Version]


## TODO: move version-math to separate module?
class VersionError(cmdlets.CmdException):
    pass


class Pep440Version(trt.Instance):
    """A trait parsing text like python "slice" expression (ie ``-10::2``)."""
    klass = Version
    _cast_types = str  # type: ignore

    def cast(self, value):
        return Version(value)


def _is_version_id_relative(version_str: VerLike):
    return str(version_str).startswith(('+', '^'))


def _add_versions(v1: VerLike, v2: VerLike):
    from packaging.version import _cmpkey
    from copy import copy
    import itertools as itt

    def add_pairs(part, p1, p2):
        try:
            ## TODO: smarted cycle 1st rel-pair part than 2nd win-over.
            name1, num1 = p1
            name2, num2 = p2
            assert isinstance(name1, str) and isinstance(name2, str), (p1, p2)

            if name1 == name2:
                return (name1, num1 + num2)
            elif name1 < name2:
                return (name2, num2)
            else:
                raise VersionError("Cannot backtrack version \"%s\" part: "
                                   "%s%s-->%s%s" % (part) + p1 + p2)

        except TypeError:
            ## One or both are `None`.
            return p2 if p1 is None else p1

    def add_locals(l1, l2):
        try:
            vv1.local + vv2.local
        except TypeError:
            ## One or both are `None`.
            return l2 if l1 is None else l1

    v1, v2 = [v if isinstance(v, Version) else Version(v)
              for v in (v1, v2)]
    vv1, vv2 = v1._version, v2._version
    new_version = copy(v1)

    release = tuple(a + b
                    for a, b in itt.zip_longest(vv1.release,
                                                vv2.release,
                                                fillvalue=0))
    new_vv = vv1._replace(
        epoch=vv1.epoch + vv2.epoch,
        release=release,
        dev=add_pairs('dev', vv1.dev, vv2.dev),
        pre=add_pairs('pre', vv1.pre, vv2.pre),
        post=add_pairs('post', vv1.post, vv2.post),
        local=add_locals(vv1.local, vv2.local)
    )
    new_version._version = new_vv

    ## When transplanting `_version`, this point to the old one;
    #  special hash/eq functions rely on this.
    #
    new_version._key = _cmpkey(
        new_vv.epoch,
        new_vv.release,
        new_vv.pre,
        new_vv.post,
        new_vv.dev,
        new_vv.local,
    )

    return new_version


def _find_caret_anchor_version(v: VerLike):
    raise NotImplementedError()


def calc_versions_op(op: str, v1: VerLike, v2: VerLike):
    """return the "sum" of the the given two versions."""
    ## Version parsing sample::
    #
    #      >>> Version('1.2a3.post4.dev5+ab_cd.ef-16')._version
    #      _Version(epoch=0, release=(1, 2), dev=('dev', 5), pre=('a', 3),
    #               post=('post', 4), local=('ab', 'cd', 'ef', 16))

    if op == '+':
        new_version = _add_versions(v1, v2)
    elif op == '^':
        v1 = _find_caret_anchor_version(v1)
        new_version = _add_versions(v1, v2)

    else:
        raise AssertionError("Version-op '%s' unknown or not implemented!" % op)

    return new_version
