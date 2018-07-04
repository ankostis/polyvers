#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
A *setuptools* plugin with x2 ``setup()`` kwds and monkeypatch all ``bdist...`` cmds.

.. Tip::
  Set `envvar[DISTUTILS_DEBUG]` to debug it.
  From https://docs.python.org/3.7/distutils/setupscript.html#debugging-the-setup-script
"""
from polyversion import polyversion, pkg_metadata_version


__all__ = 'init_plugin_kw check_bdist_kw'.split()


def _parse_kw_content(attr, kw_value):
    good_keys = set('mono_project tag_format tag_regex '
                    'vprefixes basepath git_options '
                    'default_version_env_var'.split())

    try:
        pvargs = dict(kw_value)
        extra_keys = set(pvargs) - good_keys
        if extra_keys:
            raise ValueError('extra keys (%s)' %
                             ', '.join(str(k) for k in extra_keys))
    except Exception as ex:
        from distutils.errors import DistutilsSetupError

        raise DistutilsSetupError(
            "invalid content in `%s` keyword due to: %s"
            "\n  validkeys: %s"
            "\n  got: %r" %
            (attr, ex, ', '.join(good_keys), kw_value))

    return pvargs


def _establish_setup_py_version(dist, basepath=None, **pvargs):
    "Derive version from PKG-INFO or Git rtags, and trigger bdist-check in later case."
    pname = dist.metadata.name

    basepath = (basepath or
                (dist.package_dir and dist.package_dir.get('')) or
                '.')

    version = pkg_metadata_version(pname, basepath)
    if not version:
        ## Prepare pvargs for calling `polyversion()` below,
        #  and optionally in bdist-check.
        #
        #  If `pname` is None, `polyversion()` would call `_caller_module_name()`.
        #  which is nonsense from `setup()`.
        pvargs['pname'] = pname or '<UNKNOWN>'
        ## Avoid also `_caller_path()`.
        #  I confirm, `setuptools.find_packages()` assume '.'.
        pvargs['basepath'] = basepath
        default_version = dist.metadata.version

        ## Respect version env-var both if default-version empty/none.
        #
        defver_envvar = pvargs.get('default_version_env_var', '%s_VERSION' % pname)
        if not default_version:
            import os

            ## Ignore empty/none envvars
            #  to preserve empty (but not none) `default-version` kwd.
            #
            env_ver = os.environ.get(defver_envvar)
            if env_ver:
                default_version = env_ver

        pvargs['default_version'] = default_version

        ## Store `pvargs` so bdist-check can rerun `polyversion()` for r-tags.
        dist.polyversion_args = pvargs

        version = polyversion(**pvargs)

        ## Monkeypatch `Distribution.run_cmd()` only if not inside a package,
        #  and only once per dist-instance
        #  (in case of setup() has already been called on that instance).
        #
        #  NOTE: We monekypatch even if user has disabled check,
        #  bc we can't now the kw order.
        #
        ## NOTE: PY2 `type(dist)` is `<type 'instance'>` on PY2,
        #  which does not have the method to patch.
        DistClass = dist.__class__
        if not hasattr(DistClass, '_polyversion_orig_run_cmd'):
            try:
                from functools import partialmethod
            except ImportError:
                ## From https://gist.github.com/carymrobbins/8940382
                from functools import partial

                class partialmethod(partial):
                    def __get__(self, instance, owner):
                        if instance is None:
                            return self
                        return partial(self.func, instance,
                                       *(self.args or ()), **(self.keywords or {}))

            DistClass._polyversion_orig_run_cmd = DistClass.run_command
            DistClass.run_command = partialmethod(_monkeypathed_run_command,
                                                  defver_envvar=defver_envvar)

    if version:
        dist.metadata.version = version


def init_plugin_kw(dist, attr, kw_value):
    """
    A :term:`setuptools` kwd for deriving subproject versions from PKG-INFO or git tags.

    :param dist:
        class:`distutils.Distribution`
    :param str attr:
        the name of the keyword
    :param kw_value:
        The content of the new ``setup(polyversion=...)`` keyword.

        **SYNTAX:** ``'polyversion': (<bool> | <dict>)``

        When it is a dict, its keys roughly mimic those in :func:`polyversion()`
        except those differences:

        :param pname:
            absent; derived from ``setup(name=...)`` keyword
        :param default_version:
            absent; derived from ``setup(version=...)`` keyword:

            - if `None`/not given, any problems will be raised,
              and ``setup.py`` script wil abort
            - if ``version`` is a (possibly empty) string,
              this will be used in case version cannot be auto-retrieved.

        :param is_release:
            absent; always `False` when deriving the version,
            and `True` when bdist-checking
        :param basepath:
            if not given, derived from ``setup(package_dirs={...})`` keyword
            or '.' (and never from caller-stack).

        See :func:`polyversion()` for keyword-dict's content.

    - It tries first to see if project contained in a distribution-archive
      (e.g. a "wheel"), and tries to derive the version from egg-infos.
      Then it falls through retrieving it from git tags.

      .. Tip::
          For cases where a shallow git-clone does not finds any *vtags*
          back in history, or simply because the project is new, and
          there are no *vtags*, we set default-version to empty-string,
          to facilitate pip-installing these projects from sources.

    """
    ## Registered in `distutils.setup_keywords` *entry_point*
    #  of this project's ``setup.py``.
    if kw_value is False:
        return
    if kw_value is True:
        kw_value = {}

    pvargs = _parse_kw_content(attr, kw_value)
    _establish_setup_py_version(dist, **pvargs)


def _monkeypathed_run_command(dist, cmd, defver_envvar):
    """
    A ``distutils.run_command()`` that screams on `bdist...` cmds not from rtags.
    """
    ## Flag value may originate from 2 places:
    #    - from `setup.py:setup()` kwd,
    #    - from `setup.cfg:[global]` section.
    #  Cast-bool would yield `True` on "False" str-value from the later!!
    #
    run_check = getattr(dist, 'polyversion_check_bdist_enabled', False)
    run_check_bval = bool(run_check)
    if run_check_bval:
        import distutils.util as dstutils

        try:
            run_check_bval = dstutils.strtobool(str(run_check))
        except ValueError as ex:
            import logging

            run_check_bval = False
            logging.getLogger(__name__).warning(
                "Invalid value '%s' for boolean `polyversion_check_bdist_enabled` option, "
                "assuming False;"
                "\n  expected: (y yes t true on 1) OR (n no f false off 0)",
                run_check)

    if cmd.startswith('bdist') and run_check_bval:
        ## Cache results to avoid multiple calls into `polyversion(r-tag)`.
        #
        rtag_err = getattr(dist, 'polyversion_rtag_err', None)
        if rtag_err is None:
            pvargs = dist.polyversion_args.copy()
            pvargs['default_version'] = None  # scream if missing
            pvargs['is_release'] = True

            try:
                polyversion(**pvargs)

                rtag_err = False
            except Exception as ex:
                rtag_err = str(ex)

            dist.polyversion_rtag_err = rtag_err

        if rtag_err is not False:
            from distutils.errors import DistutilsSetupError

            raise DistutilsSetupError(
                "Attempted to run '%s' from a non release-tag?\n  error: %s"
                "\n\n  If you really want to build a binary distribution package "
                "\n  from non-engraved sources, you may either: "
                "\n  - set `%s` env-var to some version, or "
                "\n  - set `polyversion_check_bdist_enabled = false` in your "
                "`$CWD/setup.cfg:[global]` section " %
                (cmd, rtag_err, defver_envvar))

    return dist._polyversion_orig_run_cmd(cmd)


def check_bdist_kw(dist, _attr, kw_value):
    """
    A *setuptools* kwd for aborting `bdist...` commands if not on r-tag.

    **SYNTAX:** ``'polyversion_check_bdist_enabled': <any>``

    When `<any>` evaluates to false (default),  any `bdist...` (e.g. ``bdist_wheel``),
    :term:`setuptools` commands will abort if not run from a :term:`release tag`.

    By default it this check is bypassed.  To enable it, without editing your sources
    add this in your ``$CWD/setup.cfg`` file::

        [global]
        polyversion_check_bdist_enabled = true
        ...

    - Ignored, if `polyversion` kw is not enabled.
    - Registered in `distutils.setup_keywords` *entry_point* of this project's
      ``setup.py`` file.
    """
    ## NOTE: code here runs only if kw set in `setup.py:setup()`` - BUT
    #  NOT from `$CWD/setup.cfg:[global]` section!!
    dist.polyversion_check_bdist_enabled = bool(kw_value)
