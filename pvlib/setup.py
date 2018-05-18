#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup script *polyversion-lib*."""
from __future__ import print_function

from setuptools import setup
import os.path as osp

mydir = osp.dirname(osp.realpath(__file__))

## This sub-project eats it's own dog-food, and
#  uses `polyversion` to derive its own version on runtime from Git tags.
#
#  For this reason the following hack is needed to start developing it
#  from git-sources: it bootstraps  ``pip install -e pvlib[test]``
#  when not any version of the `polyversion` lib is already installed on the system.
#
try:
    from polyversion import polyversion
except ImportError:
    import sys
    try:
        print("Hack: pre-installing `polyversion` from standalaone `bin/pvlib.whl`...",
              file=sys.stderr)
        sys.path.append(osp.join(mydir, 'bin', 'pvlib.whl'))
        from polyversion import polyversion
    except Exception as ex:
        print("Hack failed :-(", file=sys.stderr)
        polyversion = lambda *_, **__: '0.0.0'


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
    ## The ``package_dir={'': <sub-dir>}`` arg is needed for `py_modules` to work
    #  when packaging sub-projects. But ``<sub-dir>`` must be relative to launch cwd,
    #  or else, ``pip install -e <subdir>`` and/or ``python setup.py develop``
    #  break.
    #  Also tried chdir(mydir) at the top, but didn't work.
    package_dir={'': osp.relpath(mydir)},
    # packages=find_packages(osp.realpath(osp.join(mydir, 'polyversion')),
    #                        exclude=['tests', 'tests.*']),
    packages=['polyversion'],
    license='MIT',
    zip_safe=True,
    platforms=['any'],
    keywords="version-management configuration-management versioning "
             "git monorepo tool library".split(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
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
