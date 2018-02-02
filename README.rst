.. image:: https://img.shields.io/pypi/v/multivers.svg
        :target: https://pypi.python.org/pypi/multivers

.. image:: https://img.shields.io/travis/ankostis/multivers.svg
        :target: https://travis-ci.org/ankostis/multivers

.. image:: https://readthedocs.org/projects/multivers/badge/?version=latest
        :target: https://multivers.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/ankostis/multivers/shield.svg
     :target: https://pyup.io/repos/github/ankostis/multivers/
     :alt: Updates

=========================================================================
Multivers: Bump independently PEP-440 versions on multi-project Git repos
=========================================================================

:version:        |version|
:rel_date:      `2017-12-07 01:31:19`
:Documentation: https://multivers.readthedocs.io
:repository:    https://github.com/JRCSTU/multivers
:pypi-repo:     https://pypi.org/project/multivers/
:keywords:      software, configuration, versioning, library
:copyright:     2018 European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `EUPL 1.2 <https://joinup.ec.europa.eu/software/page/eupl>`_

A ``bumpversion``-like command-line tool to maintain independent PEP-440 versions
of multiple related projects hosted in a single Git repo (*monorepo*).


Quickstart
==========

.. code-block:: console

    $ multivers                            # list all sub-project versions
    $ multivers  proj1  --add 0.0.1.dev    # e.g. proj-1-0.1.0 --> 0.1.1.dev0

    Which will add a new tag: proj1-r0.1.1.dev0 on top of proj1-v0.1.1.dev0 commit.

Features
========
* TODO


Similar Projects
================
Contrary to this project's *PEP-440*, all other important projects are
using `Semantic versioning <http://semver.org/>`_:

- The original **bumpversion** project, development stopped after 2015:
   https://github.com/peritus/bumpversion
- The active **bumpversion** project:
  https://github.com/c4urself/bump2version
- **releash**: another *monorepos* managing tool, also publishing to PyPi:
  https://github.com/maartenbreddels/releash
- A newer & simpler *bumpversion*:
  https://github.com/wdecoster/bumpversion/graphs/contributors
-**Git Bump** using git-hooks:
  https://github.com/arrdem/git-bump
- Search also `34 similar projects in GitHub
  <https://github.com/search?l=Python&o=desc&q=bump+version&s=updated&type=Repositories>`_


Credits
=======
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

