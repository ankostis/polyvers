==================================================================
Polyversion: derive subproject versions from tags on Git monorepos
==================================================================

.. image:: https://img.shields.io/pypi/v/polyversion.svg
    :alt: Deployed in PyPi?
    :target: https://pypi.org/pypi/polyversion

.. image:: https://img.shields.io/travis/JRCSTU/polyvers.svg
    :alt: TravisCI (linux) build ok?
    :target: https://travis-ci.org/JRCSTU/polyvers

.. image:: https://ci.appveyor.com/api/projects/status/lyyjtmit5ti7tg1n?svg=true
    :alt: Apveyor (Windows) build?
    :scale: 100%
    :target: https://ci.appveyor.com/project/ankostis/polyvers

.. image:: https://img.shields.io/coveralls/github/JRCSTU/polyvers.svg
    :alt: Test-case coverage report
    :scale: 100%
    :target: https://coveralls.io/github/JRCSTU/polyvers?branch=master&service=github

.. image:: https://readthedocs.org/projects/polyvers/badge/?version=latest
    :target: https://polyvers.readthedocs.io/en/latest/?badge=latest
    :alt: Auto-generated documentation status

.. image:: https://api.codacy.com/project/badge/Grade/11b2545fd0264f1cab4c862998833503
    :target: https://www.codacy.com/app/ankostis/polyvers_jrc
    :alt: Code quality metric

.. _coord-start:

:version:       0.2.2a0
:updated:       2018-07-08T00:14:57.704899
:Documentation: http://polyvers.readthedocs.io/en/latest/usage-pvlib.html
:repository:    https://github.com/JRCSTU/polyvers
:pypi-repo:     https://pypi.org/project/polyversion/
:copyright:     2018 JRC.C4(STU), European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `MIT License <https://choosealicense.com/licenses/mit/>`_

The python 2.7+ library needed by (sub-)projects managed by `polyvers cmd
<https://github.com/JRCSTU/polyvers>`_ to derive their version-ids on runtime from Git.

Specifically, the configuration file ``.polyvers.yaml`` is NOT read -
you have to repeat any non-default configurations as function/method keywords
when calling this API.

Here only a very rudimentary documentation is provided - consult `polyvers`
documents provided in the link above.

.. Note::
    Only this library is (permissive) MIT-licensed, so it can be freely vendorized
    by any program - the respective `polyvers` command-line tool is
    "copylefted" under EUPLv1.2.

.. _coord-end:

Quickstart
==========
.. _usage:

There are 4 ways to use this library:
  - As a :term:`setuptools plugin`;
  - through its Python-API (to dynamically version your project);
  - through its barebone cmdline tool: ``polyversion``
    (installation required);
  - through the standalone executable wheel: ``bin/pvlib.run``
    (no installation, but sources required; behaves identically
    to ``polyversion`` command).


*setuptools* usage
------------------
.. currentmodule:: polyversion

The `polyversion` library function as a *setuptools* "plugin", and
adds two new ``setup()`` keywords for deriving subproject versions
from PKG-INFO or git tags  (see :func:`polyversion.init_plugin_kw`):

1. keyword: ``polyversion --> (bool | dict)``
    When a dict, its keys roughly mimic those in :func:`polyversion()`,
    and can be used like this:

    .. code-block:: python

        from setuptools import setup

        setup(
            project='myname',
            version=''              # omit (or None) to abort if cannot auto-version
            polyversion={           # dict or bool
                'mono_project': True, # false by default
                ...  # See `polyversion.init_plugin_kw()` for more keys.
            },
            setup_requires=[..., 'polyversion'],
            ...
        )

2. keyword: ``polyversion_check_bdist_enabled --> bool``
    When it is true, the :term:`bdist-check` is enabled, and any `bdist_*` setup-commands
    (e.g. ``bdist_wheel``) will abort if not run from :term:`engrave`\d sources
    (ie from an :term:`release tag`).

    To enable this check without editing the sources, add the following into
    your ``$CWD/setup.cfg`` file::

        [global]
        polyversion_check_bdist_enabled = true
        ...


API usage
---------
An API sample of using also :func:`polytime()` from within your
``myproject.git/myproject/__init__.py`` file:

.. code-block:: python

    from polyversion import polyversion, polytime  # no hack, dependency already installed

    __version__ = polyversion()  # project assumed equal to this module-name: 'myproject'
    __updated__ = polytime()
    ...

.. Tip::
   Depending on your repo's *versioning scheme* (eg you have a :term:`mono-project` repo,
   with version-tags simply like ``vX.Y.Z``), you must add in both invocations
   of :func:`polyversion.polyversion()` above the kw-arg ``mono_project=True``.


Console usage
-------------
The typical command-line usage of this library (assuming you don't want to install
the full blown `polyvers` command tool) is given below:

.. code-block:: console


    user@host:~/ $ polyversion --help
    Describe the version of a *polyvers* projects from git tags.

    USAGE:
        polyversion [PROJ-1] ...
        polyversion [-v | -V ]     # print my version information

    user@host:~/ $ polyversion polyversion    # fails, not in a git repo
    b'fatal: not a git repository (or any of the parent directories): .git\n'
      cmd: ['git', 'describe', '--match=cf-v*']
    Traceback (most recent call last):
      File "/pyenv/site-packages/pvlib/polyversion/__main__.py", line 18, in main
        polyversion.run(*sys.argv[1:])
      File "/pyenv/site-packages/pvlib/polyversion/__init__.py", line 340, in run
        res = polyversion(args[0], repo_path=os.curdir)
      File "/pyenv/site-packages/pvlib/polyversion/__init__.py", line 262, in polyversion
        pvtag = _my_run(cmd, cwd=repo_path)
      File "/pyenv/site-packages/pvlib/polyversion/__init__.py", line 106, in _my_run
        raise sbp.CalledProcessError(proc.returncode, cmd)
    subprocess.CalledProcessError: Command '['git', 'describe', '--match=cf-v*']' returned non-zero exit status 128.

    user@host:~/ $ cd polyvers.git
    user@host:~/polyvers.git (dev) $ polyversion polyvers polyversion
    polyvers: 0.0.2a10
    polyversion: 0.0.2a9

Standalone wheel
----------------
Various ways to use the standalone wheel from *bash*
(these will still work without having installed anything):

.. code-block:: console

    user@host:~/polyvers.git (master) $
    user@host:~/polyvers.git (master) $ ./bin/pvlib.run polyversion
    polyversion: 0.0.2a9
    user@host:~/polyvers.git (master) $ python ./bin/pvlib.run --help
    ...
    user@host:~/polyvers.git (master) $ python ./bin/pvlib.run -m polyversion  -v
    version: 0.0.2a9
    user@host:~/polyvers.git (master) $ PYTHONPATH=./bin/pvlib.run  python -m polyversion  -V
    version: 0.0.2a9
    updated: Thu, 24 May 2018 02:47:37 +0300


.. Note:
   You cannot define what is your *versioning-scheme* from console tools - it is
   your repo's ``.polyvers.yaml` configuration file that defines whether
   you have a *mono-project* or a *monorepo* (version-tags like ``proj-vX.Y.Z``).


For the rest, consult the *polyvers* project: https://polyvers.readthedocs.io
