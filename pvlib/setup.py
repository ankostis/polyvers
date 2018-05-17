#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup script *polyversion-lib*."""
## Need this to install from sources.
try:
    from polyversion import polyversion
except ImportError:
    def polyversion(*_, **__):
        return '0.0.0'

from setuptools import setup
import os.path as osp

mydir = osp.dirname(osp.realpath(__file__))

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
    py_modules=['polyversion'],  # need `package_dir`, or bad build from other dirs
    license='EUPL 1.2',
    zip_safe=True,
    platforms=['any'],
    keywords="version-management configuration-management versioning "
             "git monorepo tool library".split(),
    classifiers=[
        'Development Status :: 3 - Alpha',
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
