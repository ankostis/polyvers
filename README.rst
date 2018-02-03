.. image:: https://img.shields.io/pypi/v/polyvers.svg
        :target: https://pypi.python.org/pypi/polyvers

.. image:: https://img.shields.io/travis/jrcstu/polyvers.svg
        :target: https://travis-ci.org/jrcstu/polyvers

.. image:: https://readthedocs.org/projects/polyvers/badge/?version=latest
        :target: https://polyvers.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/jrcstu/polyvers/shield.svg
     :target: https://pyup.io/repos/github/jrcstu/polyvers/
     :alt: Updates

==========================================================================
Polyvers: Bump sub-project PEP-440 versions in Git monorepos independently
==========================================================================

:version:       |version|
:rel_date:      2018-02-03 00:00:00
:Documentation: https://polyvers.readthedocs.io
:repository:    https://github.com/JRCSTU/polyvers
:pypi-repo:     https://pypi.org/project/polyvers/
:keywords:      versioning, configuration, git, monorepo, software, tool, library
:copyright:     2018 European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `EUPL 1.2 <https://joinup.ec.europa.eu/software/page/eupl>`_

A ``bumpversion``-like command-line tool to bump `PEP-440 version-ids
<https://www.python.org/dev/peps/pep-0440/>`_ independently
on multiple related sub-projects hosted in a single Git repo (*monorepo*).


Quickstart
==========
1. Installing the tool, and you get the ``polyvers`` command:

   .. code-block:: console

    $ pip install polyvers
    ...
    $ polyvers --version
    0.0.0
    $ polyvers --help
    ...

    $ polyvers
    polyvers: Neither `setup.py` nor `.polyvers.py` configuration file found!


2. Assuming our *monorepo* project ``/monorepo.git/`` contains two sub-projects::

    /monorepo.git/
        +--base_project/
        |   +--setup.py:  setup(name='baseproj', ...)
        |   +--baseproj/__init__.py
        |   +--...
        +--core/
            +--setup.py: setup(name='core', ...)
            +--core/__init__.py
            +--...

   ...we have to map the *project folders ↔ project-names* using a `traitlets configuration
   file <https://traitlets.readthedocs.io/en/stable/>`_ named as
   ``/monorepo.git/.polyvers.py``:

   .. code-block:: python

        c.Polyvers.projects = [
            {'path': 'base_project'},  # If no 'name' given, extracted from `setup.py`.
            {'name': 'core'}           # If no `path`, same as `project_name` implied.
        ]

        ## Prefer not to engrave Version-ids "statically" in master branch (trunk),
        #  to avoid conflicts when merging version files.
        c.Polyvers.leaf_releases = True


3. We then set each sub-project to derive its version *on runtime* from latest tag(s),
   using this code in e.g. ``/monorepo.git/base_project/baseproj/__init__.py:``:

   .. code-block:: python

        import polyvers

        __title__ = "baseproj"
        __version__ = polyvers.version('baseproj')
        ...

4. We can now run use the ``polyvers`` command to inspect & set versions for all
   sub-projects:

   .. code-block:: console

    $ cd /monorepo.git
    $ polyvers             # No sub-project versions yet.
    base_project: null
    core: null

    $ polyvers  --set 0.0.0
    ...
    base_project: 0.0.0
    core: 0.0.0

    $ git lg    # Ok, augmented `lg` output a bit here...HEAD --> UPPER branch.
    COMMITS BRANCH TAGS                 REMARKS
    ======= ====== ==================== ========================================
         O  latest baseproj-r0.0.0      - x2 tags on "Release" leaf-commit
        /          core-r0.0.0            outside-of-trunk (not in HEAD).
       O    MASTER baseproj-v0.0.0      - x2 tags on "Version" commit
       |           core-v0.0.0            for bumping both projects to v0.0.0
       O                                - Previous commit, before version bump.

   .. Hint::
    Note the difference between ``ABC-v0.0.0`` vs ``ABC-r0.0.0`` tags.

   In the source code, it's only the "release" commit that has *engraved* version-ids:

   .. code-block:: console

    $ cat base_project/baseproj/__init__.py    # Untouched!
    import polyvers

    __title__     = "baseproj"
    __version__ = polyvers.version('baseproj')
    ...

    $ git checkout  latest
    $ cat base_project/baseproj/__init__.py
    import polyvers

    __title__     = "baseproj"
    __version__ = '0.0.0'
    ...

    $ git checkout  -  # to return to master.


5. Now let's add another commit and then bump ONLY ONE sub-project:

   .. code-block:: console

    $ git commit  --allow-empty  -m "some head work"
    $ polyvers  baseproj  --add 0.0.1.dev
    ...
    base_project: 0.0.1.dev0
    core: 0.0.0+base_project.0.0.1.dev0

    $ git lg
    COMMITS BRANCH TAGS                 REMARKS
    ======= ====== ==================== ========================================
         O  latest baseproj-r0.0.1.dev0 - The latest "Release" leaf-commit.
        /                                 branch `latest` was reset non-ff.
       O    MASTER baseproj-v0.0.1.dev0 - The latest "Version" commit.
       O                                - some head work
       | O         baseproj-r0.0.0      - It's obvious now why "Release" commits
       |/          core-r0.0.0            are called "leafs".
       O           baseproj-v0.0.0
       |           core-v0.0.0
       O

    $ git checkout latest
    $ cat base_project/baseproj/__init__.py
    import polyvers

    __title__     = "baseproj"
    __version__ = '0.0.1.dev0'
    ...

    $ cat core/core/__init__.py
    import polyvers

    __title__ = "core"
    __version__ = '0.0.0+baseproj.0.0.1.dev0'
    ...
    $ git checkout -

   Notice how the the `"local" part of PEP-440
   <https://www.python.org/dev/peps/pep-0440/#local-version-identifiers>`_ (statring with ``+...``)
   is used by the engraved version of the **un-bumped** ``core`` project to signify
   the correlated version of the **bumped** ``baseproj``.  This trick is uneccesary
   for tags because they apply repo-wide, to all sub-projects.


Features
========
- `PEP-440 version ids
  <https://www.python.org/dev/peps/pep-0440/>`_; use *local version identifiers* part
  to signify versions of any the *dependent* project(s).
- Optionally engrave sub-project version-ids in "leaf" commits, outside-of-trunk
  to avoid thus merge conflicts.
- Maintain "developmental" release trains that can be safely published in *PyPi*
  (need ``pip install --pre``).
- Extensible with bump-version *hooks* (e.g. for validating doctests) implemented
  as `setuptools plugins
  <http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_.
- Always accurate version reported on runtime when run from git repos
  (never again forget to update IDs when running experiments)

Drawbacks
=========
- Needs extra setup to view the project-version in GitHub landing page.


Similar Projects
================
Contrary to this project's *PEP-440*, all other important projects are
using `Semantic versioning <http://semver.org/>`_:

- The original **bumpversion** project; development stopped after 2015:
  https://github.com/peritus/bumpversion
- **bump2version:** active clone of the original:
  https://github.com/c4urself/bump2version
- **releash**: another *monorepos* managing tool, that publishes also to PyPi:
  https://github.com/maartenbreddels/releash
- **Git Bump** using git-hooks:
  https://github.com/arrdem/git-bump
- Search other `34 similar projects in GitHub
  <https://github.com/search?l=Python&o=desc&q=bump+version&s=updated&type=Repositories>`_.
- https://github.com/korfuri/awesome-monorepo


Credits
=======
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

