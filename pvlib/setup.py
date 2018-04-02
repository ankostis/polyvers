#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup script *polyversion-lib*."""

#import sys

from polyversion import polyversion

from setuptools import setup, find_packages

import os.path as osp


mydir = osp.dirname(__file__)


with open(osp.join(mydir, 'README.rst')) as readme_file:
    readme = readme_file.read()


test_requirements = [
    'pytest',
    'pytest-runner',
    'pytest-cov',
    'flake8',
    'flake8-builtins',
    'flake8-mutable',
    #'mypy',
]
PROJECT = 'polyversion'
setup(
    name=PROJECT,
    version=polyversion(PROJECT, '0.0.0'),
    description="Lib code deriving subproject versions from tags on git monorepos.",
    long_description=readme,
    author="Kostis Anagnostopoulos",
    author_email='ankostis@gmail.com',
    url='https://github.com/jrcstu/polyvers',
    download_url='https://pypi.org/project/polyversion/',
    project_urls={
        'Documentation': 'http://polyvers.readthedocs.io/',
        'Source': 'https://github.com/jrcstu/polyvers',
        'Tracker': 'https://github.com/jrcstu/polyvers/issues',
    },
    packages=find_packages(exclude=['tests']),
    license='EUPL 1.2',
    zip_safe=True,
    platforms=['any'],
    keywords="version-management configuration-management versioning "
             "git monorepo tool library".split(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    #python_requires='>=3.6',
    tests_require=test_requirements,
    extras_require={
        'test': test_requirements,
    },
    entry_points={
        'console_scripts': [
            '%(p)s = %(p)s:main' % {'p': PROJECT}]},
)
