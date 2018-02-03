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
:keywords:      version-management, configuration-management, versioning,
                git, monorepo, tool, library
:copyright:     2018 European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `EUPL 1.2 <https://joinup.ec.europa.eu/software/page/eupl>`_

A ``bumpversion``-like command-line tool to bump `PEP-440 version-ids
<https://www.python.org/dev/peps/pep-0440/>`_ independently on multiple related
sub-projects hosted in a single *Git* repo (the `monorepo`_ ).

"Bumping a version" translates into:

- deciding the next version of sub-projects, selectively and independently;
- adding x2 commits & tags: one *"Version" commit* in-trunk, and another
  `"Leaf" release-commit`_;
- engraving the new version-ids in the source code of all *dependent* sub-projects
  (in the "leaf" commit only),
- optionally building packages out of the later;
- enforcing customizable validation rules and extensible hooks on the process.


.. contents:: Table of Contents
  :backlinks: top
  :depth: 4

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

    $ polyvers status
    polyvers: Neither `setup.py` nor `.polyvers(.json|.py|.salt)` config-files found!


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
   file <https://traitlets.readthedocs.io>`_ named as
   ``/monorepo.git/.polyvers.py``:

   .. code-block:: python

        c.Polyvers.projects = [
            {'path': 'base_project'},  # If no 'name' given, extracted from `setup.py`.
            {'name': 'core'}           # If no `path`, same as `project_name` implied.
        ]


3. We then set each sub-project to derive its version *on runtime* from latest tag(s),
   using this code in e.g. ``/monorepo.git/base_project/baseproj/__init__.py:``:

   .. code-block:: python

        import polyvers

        __title__ = "baseproj"
        __version__ = polyvers.version('baseproj')
        ...

4. We can now use the ``polyvers`` command to inspect & set the same version to all
   sub-projects:

   .. code-block:: console

    $ cd /monorepo.git
    $ polyvers status           # No sub-project versions yet.
    base_project: null
    core: null

    $ polyvers setver 0.0.0
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
    $ polyvers bump 0.0.1.dev  baseproj
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
PEP 440 version ids
-------------------
While most versioning tools use `Semantic versioning
<http://semver.org/>`_, python's ``distutils`` native library
supports the quasi-superset, but more versatile, `PEP-440 version ids
<https://www.python.org/dev/peps/pep-0440/>`_.

Monorepos
---------
When your project succeeds, problems like these are known only too well:

  Changes in **web-server** depend on **core** features that cannot go public
  because the "official" **wire-protocol** is freezed.

  While downstream projects using **core** as a library complain about its bloated
  transitive dependencies (why *flask* library is needed??).

So the time to "split the project has come.  But from `lerna <https://lernajs.io/>`_:

  Splitting up large codebases into separate independently versioned packages
  is extremely useful for code sharing. However, making changes across
  many repositories is messy and difficult to track, and testing across repositories
  gets complicated really fast.

So a `monorepo <http://www.drmaciver.com/2016/10/why-you-should-use-a-single-repository-for-all-your-companys-projects/>`_
is needed.
But as `Yarn <https://yarnpkg.com/blog/2017/08/02/introducing-workspaces/>`_ put it:

  OTOH, splitting projects into their own folders is sometimes not enough.
  Testing, managing dependencies, and publishing multiple packages quickly
  gets complicated and many such projects adopt tools such as ...

This is such a tool.

"Leaf" Release-commit
---------------------
Even in single-project repos, sharing code across branches may cause merge-conflicts
due to the version-ids "engraved" in the sources.
In monorepos, more engraved version-ids translate to more opportunities for conflicts.

Contrary to `similar tools`_, static version-ids are engraved only in out-of-trunk
(leaf) commits, and only when the sub-projects are released.
In-trunk code report its version-id on runtime based on Git tags (``git-describe``)
so it's always up-to-date.

Marking dependent versions across sub-projects
----------------------------------------------
When bumping the version of a sub-project the `"local" part of PEP-440
<https://www.python.org/dev/peps/pep-0440/#local-version-identifiers>`_
on all other the *dependent* sub-projects in the monorepo  signify their relationship
at the time of the bump.

Lock release trains as "developmental"
--------------------------------------
Specific branches can be selected always to be published into *PyPi* only as
`PEP-440's "Developmental" releases
<https://www.python.org/dev/peps/pep-0440/#developmental-releases>`_, meanining that
users need ``pip install --pre`` to install from such release-trains.
This is a safeguard to avoid accidentally landing half-baked code to users.

Other Features
--------------
- Highly configurable using `traitlets <https://traitlets.readthedocs.io>`_, with
  sensible defaults; it's possible to run without any config file in single-project repos.
- Extensible with bump-version *hooks* (e.g. for validating doctests) TODO: implemented
  as `setuptools plugins
  <http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_.
- Always accurate version reported on runtime when run from git repos
  (never again wonder with which version your experimental-data were produced).

Drawbacks & Workarounds
-----------------------
- To `install sub-projects from git repos
  <https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support>`_ use::

      pip install -e git+https://repo_url/#egg=pkg&subdirectory=pkg_dir

- Set branch ``latest`` as default in GitHub to show engraved sub-project version-ids.


Similar Tools
=============
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
- `Lerna <https://lernajs.io/>`_: A tool for managing JavaScript projects
  with multiple packages.
- `Pants <https://www.pantsbuild.org/>`_:  a build system designed for codebases that:
  - Are large and/or growing rapidly.
  - Consist of many subprojects that share a significant amount of code.
  - Have complex dependencies on third-party libraries.
  - Use a variety of languages, code generators and frameworks.



Credits
=======
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

