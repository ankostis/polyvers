=======
Changes
=======

.. *towncrier* instructions for the developers:

    - Install cmd-line tool in your workstation::

            pip install towncrier

    - Add change-items in `changes.d/<issue>.<type>` files like that::

          echo 'Fixed a thing!' > ./changes.d/1234.fix

      Available change types:
        - break
        - feat
        - drop
        - fix
        - change
        - doc
        - chore

    - Generate new changes for the comming release::

          towncrier --draft       # to preview
          towncrier

    - *towncrier*'s config file is `pyproject.toml`.

. contents:: Releases
    :local:

.. _to-dos:

TODOs
=====
- Parse ``git describe`` like `setuptools_scm plugin
  <https://pypi.org/project/setuptools_scm/#default-versioning-scheme>`_ does.

- Drop `pvcmd/pvtags.py`, and replace it with `polyversion`?

- Engravings:  Not easy to extend!

  - Configurable hooks - refactor :term:`engravings` as one of them.
    to run, for example, housekeeping commands on all subprojects like
    ``pip install -e <project>`` and immediately start working in "develop mode".

    This would allow housekeeping commands and *validate tests*
    before/after every bump::

        ## Pre-release hook
        #
        pytest tests


        ## Post-release hook
        #
        rm -r dist/* build/*;
        python setup.py sdist bdist_wheel
        twine upload dist/*whl -s

  - Add top-level engrave glob-excludes.

  - Use `astor <https://pypi.org/project/astor/>`_ grafter.

- Refactor :term:`version-bump algebra` to support a single modifier per segment
  (see ``multivermath`` branch).

- Lock release-trains as "alpha/beta".., specific branches can be selected
  Based on :term:`version-bump algebra`), this will force users to always
  use ``pip install --pre`` to fetch such release-trains.
  This is a safeguard to avoid accidentally landing half-baked code to users.

- Retrofit `polyversion` library as a plugin of `polyvers` command.

- Function as plugin for other 3rd-party projects, bake a cookiecutter

- Check what happens with `no-commit`, e.g. to temporarily package a wheel.

- FIX: `git < 2.15.0` was buggy with multiple match-patterns in command::

      git describe --match=...  --match=...

  https://github.com/git/git/blob/master/Documentation/RelNotes/2.15.0.txt

.. towncrier release notes start


2018-07-05: polyversion-v0.2.1a0
================================
- Feature: The :envvar:`POLYVERSION_LOG_LEVEL` control *polyversion* verbosity.
  Run ``polyversion -h`` fo help.
- Change: minor reordering when searching version from package-metadata.
- fix: add standalone ``bin/pvlib.run`` from last release.
- fix: :func:~polyversion()`/:func:~polytime()` are guessing ``basepath`` keyword
  from the path of caller's top-package (not just from caller's fpath).


2018-07-04: polyversion-v0.2.0a2
================================
- Version `v0.2.0a0` not in pypi, consumed for standalone ``bin/pvlib.run``.
- Version `v0.2.0a1` were not finding sbling-dir versions if ``pip install git+...``,
  and had not replaced all skip-bdist flags.


Features
--------

- Teach non-engraved projects how to retrieve polyversion when pip-installed:

  - The functions :func:`.polyversion.polyversion()` & :func:`polyversion..polytime()`
    now attempt to fetch version from package/site-package infos.
  - And the function doing this  :func:`polyversion.pkg_metadata_version()`
    retrofitted to:

    - search  for `<pname-<version>.egg-info/PKG-INFO` in `baspath` sibling folder
      (before searching PKG-INFO, METADATA in `basepath`),
    - so now `basepath` always needed in  `polyversion()/polytime()` functions
      to locate sibling dir.


Breaking Changes
----------------

- Rename :term:`setuptools` flag from ``skip_polyversion_check -->
  polyversion_check_bdist_enabled`` to flip its default logic (not checking by
  default), since non-engraved wheels install just fine now.
- Rename the keyword of ``polyversion()``/``polytime()`` functions from
  ``repo_path --> basepath`` to denote its importance for retrieving the version
  of installed projects from sibling dirs inside  ``PYTHONPATH/site-packages/``.


2018-06-29: polyversion-v0.1.1a3
================================
(change actually done in `v0.1.1a1`, just a fixes & doc-msg in `a2`)

- FIX: teach :term:`setuptools plugin` about :term:`default version env-var`.
  Now can ``pip install git+https://some.git.repo/but-from/non-engraved-branch``.


2018-06-27: polyversion-v0.1.1a0
================================
- FEAT: Introduce configurable :term:`default version env-var` to fall-back
  to :envvar:`<pname>_VERSION` if it exists, in case of errors (e.g. no git).
  The presence of such a variable also sets ``polytime(no_raise=True)``,
  which now also support the ``pname`` and ``default_version_env_var`` kwds.


2018-06-06: polyvers-v0.1.0a1, polyversion-v0.1.0a7
===================================================
Mostly docs, combined release.

+ FEAT: reinstated :term:`engravings` on ``_version.py``
  (see previous release for rational).


2018-06-05: polyvers-v0.1.0a0, polyversion-v0.1.0a6: co2mpas-ready
==================================================================
+ FEAT: reinstated :term:`engravings` on ``setup.py`` (dropped only for a while
  in `2018-06-03: polyversion-v0.1.0a3: setuptools`_ ), since, assuming clients have adopted
  the new :term:`setuptools plugin` keyword, it is the `default_version` that
  will be engraved, which is fine.

+ fix: report any version matched both from :term:`v-tag`\s and :term:`r-tag`'s.

+ fix: ``bump`` command does not engrave *egg*-related files.

+ ``polyversion`` command got a bit more civilized (with logging to explain
  problems with related stacktraces.

+ dev: don't test building wheel on travis...too much fuzzz.


2018-06-05: polyversion-v0.1.0a5
================================
- Disable standalone-wheel hack from ``pvlib/setup.py`` and rely on
  *setuptools* plugin even for *polyversion* ONCE MORE.
  (but no need to update standalone, which is a wheel, unaffected by that)


2018-06-05: polyversion-v0.1.0a4
================================
Bugfixing `polyversion` (and generate a non-buggy standalone wheel):

- FIX `polyversion` where it ignored ``setup(default_version`` keyword.
  (:git:`6519a1ba`)
- fix: `polyversion` stop eating half of its own dog food: cannot reliably use
  :term:`setuptools plugin` for its installation. (:git:`56a894cde`)
- Monkeypatching *distutils* for :term:`bdist-check` was failing in *PY2*
  due to being an "old class". (:git:`1f72baec`)

- doc: fixed recommendation about how to bypass :term:`bdist-check` to this:

    ...
    You may bypass this check and create a package with non-engraved sources
    (although it might not work correctly) by adding `skip_polyversion_check` option
    in your ``$CWD/setup.cfg`` file, like this::

        [global]
        skip_polyversion_check = true
        ...


2018-06-03: polyversion-v0.1.0a3: *setuptools*
==============================================
- `v0.1.0a2`Canceled (like the previous 2), cannot release from r-tags because ``setup()``
  reports version from v-tag.

    - Q: Is a new setup-keyword needed ``--is-polyversion-release``?
    - A: no, just search both.
- `v0.1.0a0` had been canceled for the same reason, but somewhere down the road,
  the fix was reverted (:term:`bdist-check` works for r-tag only).
- `v0.1.0a1` just marked that our ``setup.py`` files ate our dog food.

Breaking changes
-----------------
- Dropped all positional-arguments from :func:`polyversion.polyversion()`;
  was error-prone.  They have all been converted to keyword-arguments.

- Renamed data in :mod:`polyversion`
  (also applied for :class:`polyvers.pvproject.Project()`)::

        pvtag_frmt  --> pvtag_format
        vtag_frmt   --> vtag_format

- Changed arguments in :func:`polyversion.polyversion()`
  (affect also :class:`polyvers.pvproject.Project()`)::

      default     --> default_version
      tag_frmt    --> tag_format
                  --> vprefixes   (new)
                  --> is_release  (new)

- REVERTED again the `0.0.2a9` default logic to raise when it version/time
  cannot be derived.  Now by default it raises, unless default-version or
  ``no_raise`` for :func:`polyversion.polytime()`.

- Stopped engraving ``setup.py`` files ; clients should use *setuptools* plugin
  to derive version for those files (see new features, below)).
  For reference, this is the removed element from default :class:`~Project`'s
  configuration (in YAML)::

        globs: [setup.py]
        grafts:
            - regex: -|
                (?xm)
                    \bversion
                    (\ *=\ *)
                    .+?(,
                    \ *[\n\r])+

- *polyversion* library searches both *v-tags* and *r-tags* (unless limited).
  Previously, even checked-out on an *r-tag*, both ``polyversion`` command
  and ``polyvers bump`` would ignore it, and report +1 from the *v-tag*!

Features
--------
- The `polyversion` library function as a *setuptools* "plugin", and
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

  2. keyword: ``skip_polyversion_check --> bool``
     When true, disable :term:`bdist-check`, when false (default),
     any `bdist_*` (e.g. ``bdist_wheel``), commands will abort if not run
     from a :term:`release tag`.
     You may bypass this check and create a package with non-engraved sources
     (although it might not work correctly) by invoking the setup-script
     from command-line like this::

         $ python setup.py bdist_wheel --skip-polyversion-check

- `bump` cmd: engrave also non-bumped projects with their ``git describe``-derived
   version (controlled by ``--BumpCmd.engrave_bumped_only`` flag).

- Assign names to engraves & grafts for readable printouts, and for refering to
  them from the new `Project.enabled_engarves` list. (namengraves)

- ``polyversion -t`` command-line tool prints the full tag (not the version)
  to make it easy to know if it is a v-tag or r-tag.

Documentation changes
---------------------

- Adopt `towncrier` for compiling CHANGES. So now each code change can describe
  its change in the same commit, without conflicts. (towncrier)
- usage: explain how to set your projects :pep:`0518` ``pyproject.toml``
  file & ``setup_requires`` keyword in ``setup.py`` in your script.
- add `pbr`, `incremental` and `Zest.release` in :ref:`similar-tools` section
  as  *setuptools* plugins.
- re-wrote and shrinked opening section using glossary terms.

- Chore development:
    - deps: don't pin `packaging==17.1`, any bigger +17 is fine for parsing
      version correctly.


2018-05-24: 0.0.2a10: polyvers
==============================
- fix: slight change of default engraving for ``setup.py:version=...``.
- Remove default versions from the sources of our-own-dog-food
  (affects installations for developing this tool).
- refact: merged ```pvlib.whl`` and ``pvlib.run`` into a single executable and
  importable standalone wheel in ``bin/pvlib.run``, generated from
  ``polyversion-0.0.2a9``, release below.
- doc: expand section for installing and contributing into this project.
- chore: tighten various test harnesses.

2018-05-24: 0.0.2a9: polyversion
--------------------------------
2nd interim release to embed new ``bin/pvlib.run``.

- INVERT by default ``polyversion()/polytime()`` functions not to raise
  if vtags missing.
- fix: `pvlib.run` shebang to use ``#!/usr/bin/env python`` to work on linux.

2018-05-23: 0.0.2a8: polyversion
--------------------------------
Interim release to embed new ``bin/pvlib.run``.

- FIX ``polyversion`` barebone command (a utility for when not installing
  the full `polyvers` tool).
- feat: make project-name optional in :func:`polyversion.polyversion()`;
  if not given,  defaults to caller's last segment of the  module.
- doc: rudimentary explanation of how to use the lib on its own README.


2018-05-23: 0.0.2a9.post0: polyvers
===================================
- feat: add ``-C`` option to change project dir before running command.
- ``init`` command:
    - fix: were creating invalid ``.polyvers.yaml`` configuration-file
      unless ``--monorepo/--mono-project`` flags were given.
    - feat: include config-help in generated file only if
      the new ``--doc`` flag given.
    - feat: inform user of the projects auto-discovered and what type of config-file
      was generated.
- various fixes.


2018-05-19: 0.0.2a8: polyvers
=============================
- FIX(bump): was engraving all projects and not limiting to those
  specified in the command-line - command's syntax slightly changed.
- chore: Stop increasing `polyversion` version from now on.
- doc: fix all sphinx errors and API reference.

2018-05-18: 0.0.2a7
-------------------
Interim release to embed re-LICENSED ``pvlib/bin/pvlib.whl``,
from EUPLv1.2-->MIT


2018-05-18: 0.0.2a6: ``bump``!
==============================
- ``bump`` command:
    - feat: ``--amend`` now works
    - feat: ``--engrave-only``.
    - feat: log ``PRETEND`` while doing actions.
    - feat: Log which files where engraved in the final message.
- fix(engrave): don't waste cycles/log-messages on empty-matches (minor).


2018-05-18: 0.0.2a5
===================
Actually most changes happened in "interim" release `v0.0.2a2`, below.

- feat: make a standalone polyversion-lib wheel to facilitate bootstrap
  when installing & building from sources (and the lib is not yet installed).
- Add ``bin/package.sh`` that create the `pvlib` wheel as executable ``dist/pvlib.run``.
- doc: fix rtd & pypi sites.

2018-05-18: 0.0.2a4
-------------------
doc: bad PyPi landing page.

2018-05-17: 0.0.2a3
-------------------
The `pvcmd` was actually broken so far; was missing `polyversion` lib
dependency!

2018-05-17: 0.0.2a2
-------------------
Interim release to produce executable wheel needed by next release.


2018-05-17: 0.0.2a1: *monorepo*!
================================
- 2nd release, own "mono-project" splitted into 2-project "monorepo":
  - **polyvers:** cmdline tool
  - **polyversion:** library code for program-sources to derive version from git-tags
- `init`, `status`, `bump` and `config` commands work.
- Read/write YAML config file ``.polyvers.yaml`` at the git-root,
  and can automatically discover used configuration (from existing git *tags*
  or projects files).
- Support both ``--monorepo`` and ``--mono-project`` configurations.
- By default ``__init__.py``, ``setup.py`` and ``README.rst`` files are engraved
  with bumped version.

2018-05-16: 0.0.2a0
-------------------
broken


2018-01-29: 0.0.1a0: *mono-project*
===================================
- First release on PyPI as *mono-project*
