#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import vermath
from polyvers.vermath import VersionError, RelativeVersions

from packaging.version import Version
import pytest


def _check_addition(exp, v1, *v2):
    if isinstance(exp, Exception):
        with pytest.raises(type(exp), match=str(exp)):
            vermath.add_versions(v1, *v2)
    else:
        got = vermath.add_versions(v1, *v2)
        assert got == Version(exp)


@pytest.mark.parametrize('v1, v2, exp', [
    ('1.1.1', 'foo', VersionError('Invalid relative')),
    ('bar', 'foo', VersionError('Invalid version')),
    ('0', '=dev1', VersionError('Invalid relative')),
    ('0', '=rc0', VersionError('Invalid relative')),
    ('0', '=a', VersionError('Invalid relative')),
    ('0', '=.beta', VersionError('Invalid relative')),
    ('0', '=.post', VersionError('Invalid relative')),
    ('0', '=-12', VersionError('Invalid relative')),
])
def test_errors(v1, v2, exp):
    _check_addition(exp, v1, v2)


@pytest.mark.parametrize('v1, v2, exp', [
    ('1.1.1', '+0.1.2', '1.2.3'),
    ('0.0', '+1.1.1', '1.1.1'),
    ('1.1.1', ' +0.0 ', '1.1.1'),

    ('0.dev', '+0dev', '0.dev0'),
    ('0.dev', '+0dev1', '0.dev1'),
    ('0.dev1', '+0dev', VersionError('ackward bump')),
    ('0.dev1', '+0dev2', '0.dev2'),
    ('0.dev1', '+=0dev', '0.dev1'),

    ('0.0.post0', '+0.0-2', '0.0.post2'),
    ('0.0.post0', '+=0.0.post2', '0.0.post2'),
    ('1.1.post2', '+0.0.0.post2', '1.1.0.post2'),
    ('1.1.post2', '+=0.0.0.post2', '1.1.0.post4'),
    ('1.1.post3', '+2.2.2.post1', '3.3.2.post1'),
    ('1.1.post3', '+=2.2.2.post', '3.3.2.post3'),
    ('1.1.post3', '+=2.2.2.post1', '3.3.2.post4'),

    ('1.1a1', '+0.2.0a0', '1.3.0a0'),
    ('1.1a1', '+=0.2.0a0', '1.3.0a1'),
    ('1.1a1', '+0.2.0a1', '1.3.0a1'),
    ('1.1a1', '+=0.2.0a1', '1.3.0a2'),

    ('1.2.3a3', '+3beta1.dev2', '4.2.3b1.dev2'),
    ('1.2.3a3', '+=0.1.3a2', '1.3.6a5'),
    ('1.2.3a3', '+=0.1.3b2', '1.3.6b2'),
    ('1.2.3b3', '+0.1.3a2', '1.3.6a2'),

    ('1.1.post3', '+0.2', '1.3'),
    ('0.dev', '+0', '0'),
    ('0.post', '+0', VersionError('ackward bump')),
    ('0b.post.dev', '+0', '0'),
    ('0b.post.dev', '+0', '0'),

    ## No release-numbers
    #
    ('0', '+a1', VersionError('ackward bump')),
    ('0.0', '+dev', VersionError('ackward bump')),
    ('0.0', '+post', '0.0post0'),
    ('0a', '+b', '0b0'),
    ('0beta', '+a', VersionError('ackward bump')),

    ('0a1.post2.dev3', '+a.post.dev', VersionError('ackward bump')),  # '0a1.post2.dev3'),
    ('0a1.post2.dev3', '+a1.post.dev', VersionError('ackward bump')),  # '0a1.post2.dev0'),
    ('0a1.post0.dev0', '+=a.post.dev', '0a1.post0.dev0'),

    ('0a0.post0.dev0', '+a1', '0a1'),
    ('0a.post.dev', '+=a1', '0a1.post0.dev0'),

    ('0a.post2.dev1', '+post', VersionError('ackward bump')),  # '0a0.post2'),
    ('0a.post2.dev1', '+=post1', '0a0.post3.dev1'),
    ('0a.post2.dev1', '+post.dev', VersionError('ackward bump')),  # '0a0.post3.dev0'),

    ('0a.post.dev', '+dev', VersionError('ackward bump')),  # '0a-.post0.dev0'),
    ('0a.post.dev2', '+=dev', '0a0.post0.dev2'),

    ## TODO: epoch vermath, and update README
    #('0a.post.dev2', '+=1!dev', '0a0.post0.dev2'),
    #('0a.post.dev2', '+=1!post2.dev1', '0a0.post2.dev3'),
    #('0b.post.dev2', '+1!a.dev1', '0a0.dev1'),
])
def test_plus_versions(v1, v2, exp):
    _check_addition(exp, v1, v2)


@pytest.mark.parametrize('v1, v2, exp', [
    ('0', '^0', '0'),
    ('0.0', '^0', '0.0'),
    ('1.1', '^0.0', '1.1.0'),

    ('1a3', '^0', '1'),
    ('1a3', '^=0', '1a3'),
    ('1.alpha3.post1-dev3', '^0', '1'),
    ('1.alpha3.post1-dev3', '^=0', '1a3.post1.dev3'),

    ('0.0.0', '^2', '0.0.2'),
    ('0.0.0', '^=2', '0.0.2'),
    ('0.2', '^2', '0.4'),
    ('0.2', '^=2', '0.4'),
    ('0', '^1.2', '1.2'),

    ('0.1.0b0', '^2', '0.1.2'),
    ('0.1.0b0', '^=2', '0.1.2b0'),
    ('1.2a0', '^1.2', '1.3.2'),
    ('1.2a0', '^=1.2', '1.3.2a0'),

    ('1.2.3.dev1+a.b.cd', '^1', '1.2.4+a.b.cd'),
    ('1.2.3.dev1+a_b-cd', '^=1', '1.2.4.dev1+a.b.cd'),
])
def test_caret_versions(v1, v2, exp):
    _check_addition(exp, v1, v2)


@pytest.mark.parametrize('relvers, group, exp', [
    (('^0', '+0'), 'op', '+'),
    (('+0', '^0'), 'op', '^'),

    (('^0', '+dev1'), 'op', '+'),
    (('^post0', '+dev1'), 'op', '+'),
    (('^dev', '+post2'), 'op', '+'),

    (('+rc1', '^0'), 'op', '^'),
    (('+rc1', '^post1'), 'op', '^'),

    (('^0.2', '+rc2', '+=dev'), 'release', '0.2'),
    (('^0.2', '+rc2', '+=dev'), 'pre_n', '2'),
    (('^0.2', '+rc2', '+=dev'), 'dev_l', 'dev'),
    (('^0.2', '+rc2', '+=dev'), 'dev_n', None),

    ## TODO: add more merge TCs
])
def test_RelativeVersions(relvers, group, exp):
    rv = RelativeVersions(relvers)
    assert rv.group(group) == exp


@pytest.mark.parametrize('exp, v1, relvers', [
#     ('0', '0', ('^0', '^0')),
#     ('0', '0', ('^0', '+0')),
#
#     ('0.0', '0', ('^0.0', '+0.0')),
#     ('0.0.0', '0', ('^0.0', '+0.0')),

    ## relatives added with themselves
    ## XXXXX: FAIL, and STARTED REWORK IN RelativeVersions (label(), num())
    ('2', '0', ('+1', '+1')),
    ('2', '0', ('^1', '^1')),
    ('2', '0', ('^1', '+1')),
    ('2', '0', ('+1', '^1')),
    ('0b3', '0b1', ('+b1', '+b1')),
    ('0b3', '0b1', ('+=b1', '+=b1')),

    ## fix irrelevant if previous parts unchanged
    ('0.dev5', '0.dev2', ('+dev1', '+=dev1', '^dev1')),
    ## and zero-parts do nothing
    ('0rc5', '0rc2', ('+rc1', '+=rc1', '^rc1', '^rc', '+rc')),
    ## fix not leaking to next part
    ('0a2.dev1', '0a1.dev1', ('+a1', '+dev1')),
    ('0a2.dev1', '0a1.dev1', ('+a=1', '+dev1')),

    ('0.1.2rc2.dev1', '0.1.dev2', ('^0.2', '^rc2', '^dev1')),
    ('0.1.2rc2.dev3', '0.1.dev2', ('^0.2', '+rc2', '+=dev1')),

    ## all combinations from multi-rels
    ('0.1.2b4.post3.dev3', '0.1b2.post1.dev2', ('^0.2', '+b2', '+=post2', '+=dev1')),
    ('0.1.2b4.post3.dev1', '0.1b2.post1.dev2', ('^0.2', '+b2', '^=post2', '+dev1')),
    ('0.1.2b4.post3.dev3', '0.1b2.post1.dev2', ('^0.2', '+=b2', '=post2', '+=dev1')),
    ('0.1.2b4.post3.dev1', '0.1b2.post1.dev2', ('^0.2', '+=b2', '^=post2', '+dev1')),
    ('0.1.2b4.post2.dev3', '0.1b2.post1.dev2', ('^0.2', '+=b2', '^post2', '+=dev1')),
    ('0.1.2b4.post2.dev1', '0.1b2.post1.dev2', ('^0.2', '+=b2', '+post2', '+dev1')),
])
def test_multiple_versions(exp, v1, relvers):
    _check_addition(exp, v1, *relvers)
