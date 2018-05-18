=======
Changes
=======


0.0.2a7 (2018-05-18)
--------------------
LICENSE `polyversion` lib under MIT


0.0.2a6 (2018-05-18)
--------------------
- ``bump`` command:
    - feat: ``--amend`` now works
    - feat: ``--engrave-only``.
    - feat: log ``PRETEND`` while doing actions.
    - feat: Log which files where engraved in the final message.
- fix(engrave): don't waste cycles/log-messages to substite empty-matches
  (minor).


0.0.2a5 (2018-05-18)
--------------------
Actually most changes happened in "interim" release `v0.0.2a2`, below.

- feat: make a standalone polyversion-lib wheel to facilitate bootstrap
  when installing & building from sources (and the lib is not yet installed).
- Add ``bin/package.sh`` that create the `pvlib` wheel as executable ``pvlib.run``.
- doc: fix rtd & pypi sites.

0.0.2a4 (2018-05-18)
^^^^^^^^^^^^^^^^^^^^
doc: bad PyPi landing page.

0.0.2a3 (2018-05-17)
^^^^^^^^^^^^^^^^^^^^
The `pvcmd` was actually broken so far; was missing `polyversion` lib
dependency!

0.0.2a2 (2018-05-17)
^^^^^^^^^^^^^^^^^^^^
Interim release to produce executable wheel needed by next release.


0.0.2a1 (2018-05-17)
--------------------
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

0.0.2a0 (2018-05-16)
^^^^^^^^^^^^^^^^^^^^
broken


0.0.1a0 (2018-01-29)
--------------------
- First release on PyPI as *mono-project*
