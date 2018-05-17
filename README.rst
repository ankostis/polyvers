==================================================================
Polyvers: Bump independently sub-project versions in Git monorepos
==================================================================

.. _opening-start:
.. image:: https://img.shields.io/pypi/v/polyvers.svg
    :alt: Deployed in PyPi?
    :target: https://pypi.org/pypi/polyvers

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

.. image:: https://pyup.io/repos/github/JRCSTU/polyvers/shield.svg
    :target: https://pyup.io/repos/github/JRCSTU/polyvers/
    :alt: Dependencies needing updates?

.. image:: https://api.codacy.com/project/badge/Grade/11b2545fd0264f1cab4c862998833503
    :target: https://www.codacy.com/app/ankostis/polyvers_jrc
    :alt: Code quality metric

:version:       0.0.2a2
:updated:       2018-05-17T20:51:02.051128
:Documentation: https://polyvers.readthedocs.io
:repository:    https://github.com/JRCSTU/polyvers
:pypi-repo:     https://pypi.org/project/polyvers/
:keywords:      version-management, configuration-management, versioning,
                git, monorepo, tool, library
:copyright:     2018 JRC.C4(STU), European Commission (`JRC <https://ec.europa.eu/jrc/>`_)
:license:       `EUPL 1.2 <https://joinup.ec.europa.eu/software/page/eupl>`_

A python 3.6+ command-line tool to manage `PEP-440 version-ids
<https://www.python.org/dev/peps/pep-0440/>`_ of dependent sub-projects
hosted in a *Git* `monorepos`_, independently.

When bumping the version of sub-project(s), *polyvers* does the following:

- help you decide the next version of sub-projects, selectively and independently;
- add x2 tagged commits for each project bumped:

  - one in-trunk *"Version" commit tags (pvtags)* like ``foo-proj-v0.1.0``,
    and another `out-of-trunk (leaf) "Release" commit`_ like ``foo-proj-r0.1.0``;

- engrave the new versions in the source code of bumped-project(s) and
  all *dependent* sub-projects, but this happening only in the "leaf"
  version-commit;
- build packages out of the later (optionally);
- enforce (customizable) validation rules and run (extensible) hooks.

Additional capabilities and utilities:

- **polyversion** library code to extract sub-project's version from past tags;
  provided as a separate subproject here, for not depending on the full
  development tool.

- It is still possible to use plain **version tags (vtags)** like ``v0.1.0``,
  assuming you have a single project (called hereinafter a *mono-project*)

.. _opening-end:

.. contents:: Table of Contents
   :backlinks: top
   :depth: 4


.. _usage:

Quickstart
==========
1. Install the tool
-------------------
And you get the ``polyvers`` command:

.. code-block:: console

    $ pip install polyvers
    ...
    $ polyvers --version
    0.0.0
    $ polyvers --help
    ...

    $ polyvers status
    polyvers: Neither `setup.py` nor `.polyvers(.json|.py|.salt)` config-files found!

.. Note::

  Actually two projects are installed:

  - **polyvers** cmd-line tool, for developing python monorepos,
  - **polyversion**: the base python library used by projects developed
    with *polyvers* tool, so that their sources can discover their subproject-version
    on runtime from Git.


2. Initialize project
---------------------
Assuming our *monorepo* project ``/monorepo.git/`` contains two sub-projects::

    /monorepo.git/
        +--setup.py:  setup(name='mainprog', ...)
        +--mainprog/__init__.py
        +--...
        +--core-lib/
            +--setup.py: setup(name='core', ...)
            +--core/__init__.py
            +--...

...we let the tool auto-discover the mapping of *project folders ↔ project-names*
and create a `traitlets configuration YAML-file <https://traitlets.readthedocs.io>`_
named as  ``/monorepo.git/.polyvers.py``:

.. code-block:: console

    $ cd monorepo.git

    $ polyvers init --monorepo
    Created new config-file '.polyvers.yaml'.

    $ cat .polyvers.yaml
    ...
    PolyversCmd:
      projects:
      - pname: mainprog     # name extracted from `setup.py`.
        basepath: .         # path discovered by the location of `setup.py`
      - pname: core
        basepath: core-lib
    ...

    $ git add .polyvers.yaml
    $ git commit -m 'add polyvers config-gile'

And now we can use the ``polyvers`` command to inspect the versions of all
sub-projects:

.. code-block:: console

    $ polyvers status
    - mainprog
    - core

Indeed there are no tags in in git-history for the tool to derive and display
project-versions, so only project-names are shown.  With ``--all`` option
more gets displayed:

.. code-block:: console

    $ polyvers status -a
    - pname: mainprog
      basepath: .
      gitver:
      history: []
    - pname: core
      basepath: core-lib
      gitver:
      history: []

..where ``gitver`` would be the result of ``git-describe``.


3. Bump versions
----------------
We can now use tool to set the same version to all sub-projects:

.. code-block:: console

    $ polyvers bump 0.0.0 -f noengraves   # all projects implied, if no project-name given
    00:52:06       |WARNI|polyvers.bumpcmd.BumpCmd|Ignored 1 errors while checking if at least one version-engraving happened:
      ignored (--force=noengraves): CmdException: No version-engravings happened, bump aborted.
    00:52:07       |NOTIC|polyvers.bumpcmd.BumpCmd|Bumped projects: mainprog-0.0.0 --> 0.0.0, core-0.0.0 --> 0.0.0

The ``--force=noengraves`` disables a safety check that requires at least one
file modification for engraving the current version in the leaf "Release" commit
(see next step).

.. code-block:: console

    $ polyvers status
    - mainprog-v0.0.0
    - core-v0.0.0

    $ git lg    # Ok, augmented `lg` output a bit here...HEAD --> UPPER branch.
    COMMITS BRANCH TAGS                 REMARKS
    ======= ====== ==================== ========================================
         O  latest mainprog-r0.0.0      - x2 tags on "Release" leaf-commit
        /          core-r0.0.0            outside-of-trunk (not in HEAD).
       O    MASTER mainprog-v0.0.0      - x2 tags on "Version" commit
       |           core-v0.0.0            for bumping both projects to v0.0.0
       O                                - Previous commit, before version bump.

   .. Hint::
    Note the difference between ``ABC-v0.0.0`` vs ``ABC-r0.0.0`` tags.

   In the source code, it's only the "release" commit that has *engraved* version-ids:

   .. code-block:: console

    $ cat mainprog/mainprog/__init__.py    # Untouched!
    import polyvers

    __title__     = "mainprog"
    __version__ = polyvers.version('mainprog')
    ...

    $ git checkout  latest
    $ cat mainprog/mainprog/__init__.py
    import polyvers

    __title__     = "mainprog"
    __version__ = '0.0.0'
    ...

    $ git checkout  -  # to return to master.


4. Engrave version in the sources
---------------------------------
Usually programs report their version somehow when run, e.g. with ```cmd --version``.
With *polyvers* we can derive the latest from the tags created in the previous step,
using a code like this, usually in the file ``/mainprog/mainprog/__init__.py:``:

.. code-block:: python

    import polyvers

    __title__ = "mainprog"
    __version__ = polyvers.version('mainprog')
    ...

...and respectively ``/core-lib/core/__init__.py:``:

.. code-block:: python

    __version__ = polyvers.version('core')



5. Bump sub-projects selectively
--------------------------------
Now let's add another dummy commit and then bump ONLY ONE sub-project:

.. code-block:: console

    $ git commit  --allow-empty  -m "some head work"
    $ polyvers bump ^1 mainprog
    00:53:07       |NOTIC|polyvers.bumpcmd.BumpCmd|Bumped projects: mainprog-0.0.0 --> 0.0.1

    $ git lg
    COMMITS BRANCH TAGS                 REMARKS
    ======= ====== ==================== ========================================
         O  latest mainprog-r0.0.1.dev0 - The latest "Release" leaf-commit.
        /                                 branch `latest` was reset non-ff.
       O    MASTER mainprog-v0.0.1.dev0 - The latest "Version" commit.
       O                                - some head work
       | O         mainprog-r0.0.0      - Now it's obvious why "Release" commits
       |/          core-r0.0.0            are called "leafs".
       O           mainprog-v0.0.0
       |           core-v0.0.0
       O

    $ git checkout latest
    $ cat mainprog/mainprog/__init__.py
    import polyvers

    __title__     = "mainprog"
    __version__ = '0.0.1.dev0'
    ...

    $ cat core/core/__init__.py
    import polyvers

    __title__ = "core"
    __version__ = '0.0.0+mainprog.0.0.1.dev0'
    ...
    $ git checkout -

Notice how the the `"local" part of PEP-440
<https://www.python.org/dev/peps/pep-0440/#local-version-identifiers>`_ (statring with ``+...``)
is used by the engraved version of the **un-bumped** ``core`` project to signify
the correlated version of the **bumped** ``mainprog``.  This trick is uneccesary
for tags because they apply repo-wide, to all sub-projects.


.. _features:

Features
========
PEP 440 version ids
-------------------
While most versioning tools use `Semantic versioning
<http://semver.org/>`_, python's ``distutils`` native library
supports the quasi-superset, but more versatile, `PEP-440 version ids
<https://www.python.org/dev/peps/pep-0440/>`_, like that:

- Pre-releases: when working on new features::

    X.YbN               # Beta release
    X.YrcN  or  X.YcN   # Release Candidate
    X.Y                 # Final release

- Post-release::

    X.YaN.postM         # Post-release of an alpha release
    X.YrcN.postM        # Post-release of a release candidate

- Dev-release::

    X.YaN.devM          # Developmental release of an alpha release
    X.Y.postN.devM      # Developmental release of a post-release


Monorepos
---------
When your single project succeeds, problems like these are known only too well:

  Changes in **web-server** part depend on **core** features that cannot
  go public because the "official" **wire-protocol** is freezed.

  While downstream projects using **core** as a library complain about
  its bloated transitive dependencies (asking why *flask* library is needed??).

So the time to "split the project has come.  But from `lerna <https://lernajs.io/>`_:

  Splitting up large codebases into separate independently versioned packages
  is extremely useful for code sharing. However, making changes across
  many repositories is messy and difficult to track, and testing across repositories
  gets complicated really fast.

So a *monorepo* [#]_ [#]_ is the solution.
But as `Yarn <https://yarnpkg.com/blog/2017/08/02/introducing-workspaces/>`_ put it:

  OTOH, splitting projects into their own folders is sometimes not enough.
  Testing, managing dependencies, and publishing multiple packages quickly
  gets complicated and many such projects adopt tools such as ...

*Polyvers* is such a tool.

.. [#] <https://medium.com/@maoberlehner/monorepos-in-the-wild-33c6eb246cb9
.. [#] http://www.drmaciver.com/2016/10/why-you-should-use-a-single-repository-for-all-your-companys-projects/

Out-of-trunk (leaf) "Release" commit
------------------------------------
Even in single-project repos, sharing code across branches may cause merge-conflicts
due to the version-ids "engraved" in the sources.
In monorepos, the versions proliferate, and so does the conflicts.

Contrary to `similar tools`_, static version-ids are engraved only in out-of-trunk
(leaf) commits, and only when the sub-projects are released.
In-trunk code is never touched, and version-ids are reported, on runtime, based
on Git tags (like ``git-describe``), so they are always up-to-date.

Marking dependent versions across sub-projects
----------------------------------------------
TODO: When bumping the version of a sub-project the `"local" part of PEP-440
<https://www.python.org/dev/peps/pep-0440/#local-version-identifiers>`_
on all other the *dependent* sub-projects in the monorepo  signify their relationship
at the time of the bump.

Lock release trains as "developmental"
--------------------------------------
TODO: Specific branches can be selected always to be published into *PyPi* only as
`PEP-440's "Developmental" releases
<https://www.python.org/dev/peps/pep-0440/#developmental-releases>`_, meanining that
users need ``pip install --pre`` to install from such release-trains.
This is a safeguard to avoid accidentally landing half-baked code to users.

Other Features
--------------
- Highly configurable using `traitlets <https://traitlets.readthedocs.io>`_, with
  sensible defaults; it's possible to run without any config file in single-project repos.
- Always accurate version reported on runtime when run from git repos
  (never again wonder with which version your experimental-data were produced).

Features TODO
-------------
pre/post release hooks
^^^^^^^^^^^^^^^^^^^^^^
Possible to implement hooks as
`setuptools plugins <http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins>`_.
to run, for example, housekeeping commands on all subprojects like
``pip install -e <project>`` and immediately start working in "develop mode".

 This functionality would also allow to *validate tests* before/after
 every bump::

     ## Pre-release hook
     #
     pytest tests


     ## Post-release hook
     #
     rm -r dist/* build/*;
     python setup.py sdist bdist_wheel
     twine upload dist/*whl -s

Lock release trains as "developmental"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Specific branches can be selected always to be published into *PyPi* only as
`PEP-440's "Developmental" releases
<https://www.python.org/dev/peps/pep-0440/#developmental-releases>`_, meanining that
users need ``pip install --pre`` to install from such release-trains.
This is a safeguard to avoid accidentally landing half-baked code to users.


Drawbacks & Workarounds
-----------------------
- WARNING: when you build your package for distribution (*wheel*, correct?)
  remember to switch to the `out-of-trunk (leaf) "Release" commit`.
  This is particularly important if your ``setup.py`` file  use ``polyversion()``
  to derive its version.. Because if it fails for whatever reason
  (``git`` command is missing, project not located in a git-repo, miss-configuration,
  etc).

  Check also that if you provide a ``default`` argument to facilitate development,
  then you may actually build a package(*wheel*, ok?) with that "default" version.
  So, always check you package's version before uploading it to *pypi*.

- (not related to this tool) In ``setup.py`` script, the kw-argument
  ``package_dir={'': <sub-dir>}`` arg is needed for `py_modules` to work
  when packaging sub-projects (also useful with ``find_packages()``,
  check this project's sources).
  But ``<sub-dir>`` must be relative to launch cwd, or else,
  ``pip install -e <subdir>`` and/or ``python setup.py develop``
  break.

- (not related to this tool) When building projects with ``python setup.py bdist_wheel``,
  you have to clean up your build directory, or else, the distribution package
  will contain the sources from all previous subprojects.  That applies also
  when rebuilding a project between versions.

- (not related to this tool) If you don't place a ``setup.py`` file at the root
  of your git-repo, then it becomes more cumbersome to ``pip`` `install directly
  from remote URLs <https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support>`_,
  like this:
  ::

      pip install -e git+https://repo_url/#egg=pkg&subdirectory=pkg_dir

  You may use ``package_dir`` argument to ``setup()`` function
  (see `setuptools-docs <http://setuptools.readthedocs.io/en/latest/setuptools.html#id10>`_).

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
