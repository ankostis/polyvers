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

:version:       |version|
:updated:       |today|
:Documentation: https://polyvers.readthedocs.io
:repository:    https://github.com/JRCSTU/polyvers
:pypi-repo:     https://pypi.org/project/polyversion/
:copyright:     2018 JRC.C4(STU), European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `MIT License <https://choosealicense.com/licenses/mit/>`_

The python 2.7+ library needed by (sub-)projects managed by `polyvers cmd
<https://github.com/JRCSTU/polyvers>`_ to derive their version-ids on runtime from Git.

This library can be used:
- through its API (to version your project)
- through its barebone cmdline ``polyversion``:

  .. code-block:: console


      user@host ~/polyvers.git (dev) $ polyversion --help
      Describe the version of a *polyvers* projects from git tags.

      USAGE:
          polyversion [PROJ-1] ...

      user@host ~/polyvers.git (dev) $ polyversion polyversion
      polyversion: 0.0.2a7+37.g0707a09
      polyvers: 0.0.2a9.post0+7.g0707a09

For the rest, consult the *polyvers* project: https://polyvers.readthedocs.io

.. Note::
    Only this library is (permissive) MIT-licensed so it can be freely used
    by any program - the respective `polyvers` command-line tool is
    "copylefted" under EUPLv1.2.
