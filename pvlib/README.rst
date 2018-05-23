==================================================================
Polyversion: derive subproject versions from tags on git monorepos
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
:Documentation: file:///D:/Work/polyvers.git/build/sphinx/html/usage.html#usage-of-polyversion-library
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
  - through the standalone executable wheel: ``pvlib/bin/pvlib.whl``
    (no installation, but sources required; behaves identically
    to ``polyversion`` command).

.. Note::
    Only this library is (permissive) MIT-licensed, so it can be freely used
    by any program - the respective `polyvers` command-line tool is
    "copylefted" under EUPLv1.2.

API usage
---------
.. currentmodule:: polyversion

An API sample of using :func:`polyversion.polyversion()` in
a ``myproject.git/setup.py`` file:

.. code-block:: python

    ...
    setup(
        name='myproject',
        version=polyversion('myproject')
        ...
    )

An API sample of using also :func:`polytime()` in
a ``myproject.git/myproject/__init__.py`` file:

.. code-block:: python

    ...
    __version__ = polyversion()  # project assumed equal to module-name 'myproject'
    __updated__ = polytime()
    ...

.. Tip::
   Depending on your repo's *versioning scheme* (eg you have a *mono-project* repo,
   with version-tags simply like ``vX.Y.Z``), you must add in both invocations
   of :func:`polyversion.polyversion()` above the kw-arg ``mono_project=True``.


Console usage
-------------
A sample of command-line usage is given below:

.. code-block:: console


    user@host:~/ $ polyversion --help
    Describe the version of a *polyvers* projects from git tags.

    USAGE:
        polyversion [PROJ-1] ...

    user@host:~/ $ polyversion polyversion
    polyversion: 0.0.2a7+37.g0707a09
    polyvers: 0.0.2a9.post0+7.g0707a09

    user@host:~/polyvers.git (dev) $ polyversion --help
    Describe the version of a *polyvers* projects from git tags.

    USAGE:
        polyversion [PROJ-1] ...

A sample of the standalone wheel:

.. code-block:: console

    user@host:~/ $ cd ~/polyvers.git
    user@host:~/polyvers.git (master) $ polyversion polyversion
    polyversion: 0.0.2a7+37.g0707a09


.. Note:
   You cannot define what is your *versioning-scheme* from console tools - it is
   your repo's ``.polyvers.yaml` configuration file that defines whether
   you have a *mono-project* or a *monorepo* (version-tags like ``proj-vX.Y.Z``).


For the rest, consult the *polyvers* project: https://polyvers.readthedocs.io
