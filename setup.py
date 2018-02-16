#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

import sys

from setuptools import setup, find_packages


MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit("Sorry, Python >= %s is required, found: %s" %
             ('.'.join(str(i) for i in MIN_PYTHON), str(sys.version_info)))


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'boltons',                  # for IndexSet
    'toolz',
    'rainbow_logging_handler',
    'ruamel.yaml',              # for logconf
    'ipython_genutils',         # by vendorized `traitlets`
    'spectate',                 # by vendorized `traitlets`
]

setup_requirements = [
    'pytest-runner',
    # TODO(ankostis): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    'pytest-capturelog',
]
PROJECT = 'polyvers'
setup(
    name=PROJECT,
    version='0.0.0',
    description="Bump sub-project PEP-440 versions in Git monorepos independently.",
    long_description=readme + '\n\n' + history,
    author="Kostis Anagnostopoulos",
    author_email='ankostis@gmail.com',
    url='https://github.com/jrcstu/polyvers',
    packages=find_packages(include=['polyvers']),
    include_package_data=True,
    install_requires=requirements,
    license='EUPL 1.2',
    zip_safe=False,
    keywords="version-management configuration-management versioning "
             "git monorepo tool library".split(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
    entry_points={
        'console_scripts': [
            '%(p)s = %(p)s.__main__:main' % {'p': PROJECT}]},
)
