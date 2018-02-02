#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    # TODO: put package requirements here
]

setup_requirements = [
    'pytest-runner',
    # TODO(ankostis): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]
proj_name = 'multivers'
setup(
    name=proj_name,
    version='0.0.0',
    description="Bump versions of multiple projects hosted in a single Git repo"
                ", independently.",
    long_description=readme + '\n\n' + history,
    author="Kostis Anagnostopoulos",
    author_email='ankostis@gmail.com',
    url='https://github.com/ankostis/multivers',
    packages=find_packages(include=['multivers']),
    include_package_data=True,
    install_requires=requirements,
    license='EUPL 1.2',
    zip_safe=False,
    keywords='multivers',
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
