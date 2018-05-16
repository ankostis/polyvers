#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers import vermath
from polyvers.vermath import VersionError

from packaging.version import Version
import pytest


def _check_addition(v1, v2, exp):
    if isinstance(exp, Exception):
        with pytest.raises(type(exp), match=str(exp)):
            vermath.add_versions(v1, v2)
    else:
        got = vermath.add_versions(v1, v2)
        assert got == Version(exp)


@pytest.mark.parametrize('v1, v2, exp', [
    ('1.1.1', 'foo', VersionError('Invalid relative')),
    ('bar', '+1', VersionError('Invalid version')),
    ('bar', 'foo', VersionError('Invalid version')),
    ('0', '=dev1', VersionError('Invalid relative')),
    ('0', '=rc0', VersionError('Invalid relative')),
    ('0', '=a', VersionError('Invalid relative')),
    ('0', '=.beta', VersionError('Invalid relative')),
    ('0', '=.post', VersionError('Invalid relative')),
    ('0', '=-12', VersionError('Invalid relative')),
])
def test_errors(v1, v2, exp):
    _check_addition(v1, v2, exp)


@pytest.mark.parametrize('v1, v2, exp', [
    ('1.1.1', '+0.1.2', '1.2.3'),
    ('0.0', '+1.1.1', '1.1.1'),
    ('1.1.1', ' +0.0 ', '1.1.1'),

    ('0.dev', '+0dev', '0.dev0'),
    ('0.dev', '+0dev1', '0.dev1'),
    ('0.dev1', '+0dev', VersionError('ackward bump')),
    ('0.dev1', '+0dev2', '0.dev2'),
    ('0.dev1', '+=0dev', '0.dev1'),

    ('0.0.post0', '+0.0.post2', '0.0.post2'),
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

    ('1.2.3a3', '+3b1.dev2', '4.2.3b1.dev2'),
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

    ## TODO: epoch
    #('0a.post.dev2', '+=1!dev', '0a0.post0.dev2'),
    #('0a.post.dev2', '+=1!post2.dev1', '0a0.post2.dev3'),
    #('0b.post.dev2', '+1!a.dev1', '0a0.dev1'),
])
def test_plus_versions(v1, v2, exp):
    _check_addition(v1, v2, exp)


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
    _check_addition(v1, v2, exp)
