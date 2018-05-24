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

:version:       |version|
:updated:       |today|
:Documentation: https://polyvers.readthedocs.io/en/latest/usage.html#usage-of-polyversion-library
:repository:    https://github.com/JRCSTU/polyvers
:pypi-repo:     https://pypi.org/project/polyversion/
:copyright:     2018 JRC.C4(STU), European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `MIT License <https://choosealicense.com/licenses/mit/>`_

The python 2.7+ library needed by (sub-)projects managed by `polyvers cmd
<https://github.com/JRCSTU/polyvers>`_ to derive their version-ids on runtime from Git.

.. _coord-end:

Quickstart
==========
.. _usage:

There are 3 ways to use this library:
  - through its Python-API (to dynamically version your project);
  - through its barebone cmdline tool: ``polyversion``
    (installation required);
  - through the standalone executable wheel: ``bin/pvlib.run``
    (no installation, but sources required; behaves identically
    to ``polyversion`` command).

.. Note::
    Only this library is (permissive) MIT-licensed, so it can be freely used
    by any program - the respective `polyvers` command-line tool is
    "copylefted" under EUPLv1.2.

API usage
---------
.. currentmodule:: polyversion

An API usage sample of using :func:`polyversion.polyversion()` from within your
``myproject.git/setup.py`` file:

.. code-block:: python

    from setuptools import setup

    ## OPTIONAL HACK if you want to facilitate people to install from sources.
    #  You have to attach `pvlib.run` into your repository for this.
    #
    try:
        from polyversion import polyversion
    except Exception as ex:
        import sys
        sys.path.append(<YOUR PATH TO pvlib.run>)
        from polyversion import polyversion

    ...

    setup(
        name='myproject',
        version=polyversion('myproject', '0.0.0')
        install_requires=[
            'polyversion'
            ...
        ],
        ...
    )

.. Tip::
   For cases where a shallow git clone did not reach any *vtags* back in history,
   or simply because the project is new, and there are no *vtags*, we set ``default=0.0.0``,
   to facilitate pip-install these projects from sources.
   If you want a hard fail, set ``default=None``.

An API usage sample of using also :func:`polytime()` from within your
``myproject.git/myproject/__init__.py`` file:

.. code-block:: python

    from polyversion import polyversion, polytime  # no hack, dependency already installed

    __version__ = polyversion()  # project assumed equal to this module-name: 'myproject'
    __updated__ = polytime()
    ...

.. Tip::
   Depending on your repo's *versioning scheme* (eg you have a *mono-project* repo,
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

And various ways to use the standalone wheel from *bash*
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
