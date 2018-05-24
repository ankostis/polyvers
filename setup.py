#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup script *polyvers-cmd*."""

from os import path as osp
import re
import sys

from setuptools import setup, find_packages


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
    try:
        print("Hack: pre-installing `polyversion` from standalone `pvlib.run` wheel",
              file=sys.stderr)
        sys.path.append(osp.join(mydir, 'bin', 'pvlib.run'))
        from polyversion import polyversion
    except Exception as ex:
        print("Hack failed :-(", file=sys.stderr)
        polyversion = lambda *_, **__: '0.0.0'


MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit("Sorry, Python >= %s is required, found: %s" %
             ('.'.join(str(i) for i in MIN_PYTHON), str(sys.version_info)))


def yield_rst_only_markup(lines):
    """
    :param file_inp:     a `filename` or ``sys.stdin``?
    :param file_out:     a `filename` or ``sys.stdout`?`

    """
    substs = [
        # Selected Sphinx-only Roles.
        #
        (r':abbr:`([^`]+)`', r'\1'),
        (r':ref:`([^`]+)`', r'ref: *\1*'),
        (r':term:`([^`]+)`', r'**\1**'),
        (r':dfn:`([^`]+)`', r'**\1**'),
        (r':(samp|guilabel|menuselection|doc|file):`([^`]+)`', r'``\2``'),

        # Sphinx-only roles:
        #        :foo:`bar`   --> foo(``bar``)
        #        :a:foo:`bar` XXX afoo(``bar``)
        #
        #(r'(:(\w+))?:(\w+):`([^`]*)`', r'\2\3(``\4``)'),
        (r':(\w+):`([^`]*)`', r'\1(`\2`)'),
        # emphasis
        # literal
        # code
        # math
        # pep-reference
        # rfc-reference
        # strong
        # subscript, sub
        # superscript, sup
        # title-reference


        # Sphinx-only Directives.
        #
        (r'\.\. doctest', r'code-block'),
        (r'\.\. module', r'code-block'),
        (r'\.\. currentmodule::', r'currentmodule:'),
        (r'\.\. plot::', r'.. plot:'),
        (r'\.\. seealso', r'info'),
        (r'\.\. glossary', r'rubric'),
        (r'\.\. figure::', r'.. '),
        (r'\.\. image::', r'.. '),

        (r'\.\. dispatcher', r'code-block'),

        # Other
        #
        (r'\|version\|', r'x.x.x'),
        (r'\|today\|', r'x.x.x'),
        (r'\.\. include:: AUTHORS', r'see: AUTHORS'),
    ]

    regex_subs = [(re.compile(regex, re.IGNORECASE), sub)
                  for (regex, sub) in substs]

    def clean_line(line):
        try:
            for (regex, sub) in regex_subs:
                line = regex.sub(sub, line)
        except Exception as ex:
            print("ERROR: %s, (line(%s)" % (regex, sub))
            raise ex

        return line

    yield from (clean_line(line) for line in lines)


with open(osp.join(mydir, 'README.rst')) as readme_file:
    readme = readme_file.readlines()

with open(osp.join(mydir, 'CHANGES.rst')) as history_file:
    ## Remove 1st header-mark line or else,
    #  README.rst gets invalid header levels.
    history = history_file.readlines()[1:]


long_desc = ''.join(yield_rst_only_markup((readme + ['\n\n'] + history)))

requirements = [
    'polyversion',
    'boltons',                  # for IndexSet
    'toolz',
    'rainbow_logging_handler',
    'ruamel.yaml',              # for logconf
    'ipython_genutils',         # by vendorized `traitlets`
    'spectate',                 # by vendorized `traitlets`
    'ruamel.yaml>=0.15.37',     # fix PY3.7 ruamel/yaml#187
    "contextvars; python_version<'3.7'",  # for yaml-exporting cmdlets
    'packaging==17.1',
]

test_requirements = [
    'pytest >= 3.5.0',  # caplog.clear() fixed (pytest-dev/pytest#3297)
    'pytest-runner',
    'pytest-cov',
    'flake8',
    'flake8-builtins',
    'flake8-mutable',
    #'mypy',
]
PROJECT = 'polyvers'

setup(
    name=PROJECT,
    version=polyversion(PROJECT, '0.0.0'),
    description="Bump sub-project versions in Git monorepos independently.",
    long_description=long_desc,
    author="Kostis Anagnostopoulos",
    author_email='ankostis@gmail.com',
    url='https://github.com/jrcstu/polyvers',
    download_url='https://pypi.org/project/polyvers/',
    project_urls={
        'Documentation': 'https://polyvers.readthedocs.io/',
        'Source': 'https://github.com/jrcstu/polyvers',
        'Tracker': 'https://github.com/jrcstu/polyvers/issues',
        'Polyversion': 'https://pypi.org/project/polyversion/',
    },
    package_dir={'': 'pvcmd'},
    packages=find_packages('pvcmd', exclude=['tests', 'tests.*']),
    include_package_data=True,
    # setup_requires=[   # pytest suggestion: https://docs.pytest.org/en/latest/goodpractices.html
    #     #'polyversion',  @@ no, actually it is engraved-out from packages
    #     'pytest-runner'
    # ],
    install_requires=requirements,
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
    python_requires='>=3.6',
    tests_require=test_requirements,
    extras_require={
        'test': test_requirements,
        'test:python_version>="3"': ['mypy']
    },
    entry_points={
        'console_scripts': [
            '%(p)s = %(p)s.__main__:main' % {'p': PROJECT}]},
)
