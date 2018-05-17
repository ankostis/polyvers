=======
CHANGES
=======

0.0.2a4 (2018-05-18)
--------------------
Actually most changes happened in "interim" release `v0.0.2a2`, below.

- feat: make a standalone polyversion-lib wheel to facilitate bootstrap
  when installing & building from sources (and the lib is not yet installed).
- Add ``bin/package.sh`` that create the `pvlib` wheel as executable ``pvlib.run``.
- doc: fix rtd & pypi sites.

0.0.2a3 (2018-05-17)
~~~~~~~~~~~~~~~~~~~~
Broken `pvcmd`, was missing `polyversion` lib dependency(!)

0.0.2a2 (2018-05-17)
~~~~~~~~~~~~~~~~~~~~
Interim release to produce executable wheel needed by next release.


0.0.2a1 (2018-05-17)
--------------------
- 2nd release as 2 projects:
  - **polyvers:** cmdline tool
  - **polyversion:** library code for program-sources to derive version from git-tags
- `init`, `status`, `bump` and `config` commands work.
- Read/write YAML config file ``.polyvers.yaml`` at the git-root,
  and can automatically discovere used configuration (from existing git *tags*
  or projects files).
- Support both ``--monorepo`` and ``--mono-project`` configurations.
- By default ``__init__.py``, ``setup.py`` and ``README.rst`` files are engraved
  with bumped version.

0.0.2a0 (2018-05-16)
~~~~~~~~~~~~~~~~~~~~
broken


0.0.1a0 (2018-01-29)
--------------------
- First release on PyPI as *mono-project*
