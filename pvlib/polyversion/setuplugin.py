#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
A *setuptools* plugin with x2 ``setup()`` kwds and monkeypatch all ``bdist...`` cmds.
"""
from polyversion import polyversion


__all__ = 'init_plugin_kw skip_plugin_check_kw'.split()


def _get_version_from_pkg_metadata(package_name):
    """Get the version from package metadata if present.

    This looks for PKG-INFO if present (for sdists), and if not looks
    for METADATA (for wheels) and failing that will return None.
    """
    import email

    pkg_metadata_filenames = ['PKG-INFO', 'METADATA']
    pkg_metadata = {}
    for filename in pkg_metadata_filenames:
        try:
            pkg_metadata_file = open(filename, 'r')
        except (IOError, OSError):
            continue
        try:
            pkg_metadata = email.message_from_file(pkg_metadata_file)
        except email.errors.MessageError:
            continue

    # Check to make sure we're in our own dir
    if pkg_metadata.get('Name', None) != package_name:
        return None
    return pkg_metadata.get('Version', None)


def _parse_kw_content(attr, kw_value):
    good_keys = set('mono_project tag_format tag_regex '
                    'vprefixes repo_path git_options'.split())

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


def _establish_setup_py_version(dist, repo_path=None, **pvargs):
    "Derive version from PKG-INFO or Git rtags, and trigger bdist-check in later case."
    pname = dist.metadata.name

    version = _get_version_from_pkg_metadata(pname)
    if not version:
        ## Prepare pvargs for calling `polyversion()` below,
        #  and optionally in bdist-check.
        #
        #  If `pname` is None, `polyversion()` would call `_caller_module_name()`.
        #  which is nonsense from `setup()`.
        pvargs['pname'] = pname or '<UNKNOWN>'
        ## Avoid also `_caller_path()`.
        #  I confirm, `setuptools.find_packages()` assume '.'.
        pvargs['repo_path'] = (repo_path or
                               (dist.package_dir and dist.package_dir.get('')) or
                               '.')

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
            DistClass._polyversion_orig_run_cmd = DistClass.run_command
            DistClass.run_command = _monkeypathed_run_command

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
            absent; derrived from ``setup(name=...)`` keyword
        :param default_version:
            absent; derrived from ``setup(version=...)`` keyword:

            - if `None`/not given, any problems will be raised,
              and ``setup.py`` script wil abort
            - if ``version`` is a (possibly empty) string,
              this will be used in case version cannot be auto-retrived.

        :param is_release:
            absent; always `False` when derriving the version,
            and `True` when bdist-checking
        :param repo_path:
            if not given, derrived from ``setup(package_dirs={...})`` keyword
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


def _monkeypathed_run_command(dist, cmd):
    """
    A ``distutils.run_command()`` that screams on `bdist...` cmds not from rtags.
    """
    if cmd.startswith('bdist') and not getattr(dist,
                                               'skip_polyversion_check',
                                               False):
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
                "Attempted to run '%s' from a non release-tag?"
                "\n  error: %s"
                "\n  Use --skip-polyversion-check if you really want to build"
                "\n  a binary distribution package from non-engraved sources." %
                (cmd, rtag_err))

    return dist._polyversion_orig_run_cmd(cmd)


def skip_plugin_check_kw(dist, _attr, kw_value):
    """
    A *setuptools* kwd for aborting `bdist...` commands if not on r-tag.

    **SYNTAX:** ``'skip_polyversion_check': <any>``

    When `<any>` evaluates to false (default),  any `bdist...` (e.g. ``bdist_wheel``),
    :term:`setuptools` commands will abort if not run from a :term:`release tag`.
    You may bypass this check when you really wish to create
    binary distributions with non-engraved sources (although it might not
    work correctly) by invoking the setup-script from command-line
    like this::

        $ python setup.py bdist_wheel --skip-polyversion-check

    Ignored, if `polyversion` kw is not enabled.
    """
    ## Registered in `distutils.setup_keywords` *entry_point*
    #  of this project's ``setup.py``.
    dist.skip_polyversion_check = bool(kw_value)
