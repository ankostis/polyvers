#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'rainbow_logging_handler',
    'ruamel.yaml',
    'ipython_genutils',         # by vendorized `traitlets`
    'gitpython >= 2.1.0',       # Win+Cygwin support
]

setup_requirements = [
    'pytest-runner',
    # TODO(ankostis): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]
proj_name = 'polyvers'
setup(
    name=proj_name,
    version='0.0.0',
    description="Bump independently PEP-440 versions on multi-project Git repos.",
    long_description=readme + '\n\n' + history,
    author="Kostis Anagnostopoulos",
    author_email='ankostis@gmail.com',
    url='https://github.com/jrcstu/polyvers',
    packages=find_packages(include=['polyvers']),
    include_package_data=True,
    install_requires=requirements,
    license='EUPL 1.2',
    zip_safe=False,
    keywords='polyvers',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: European Union Public Licence 1.1 (EUPL 1.1)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
    entry_points={
        'console_scripts': [
            '%(p)s = %(p)s.__main__:main' % {'p': proj_name}]},
)
