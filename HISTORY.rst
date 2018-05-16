=======
History
=======

0.0.2a0 (2018-05-16)
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


0.0.1a0 (2018-01-29)
--------------------
- First release on PyPI as *mono-project*
