#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"Utils for configuring and using elaborate logs and handling `main()` failures."

import io
import logging
import sys

from ruamel import yaml  # @UnresolvedImport
import functools as fnt
import os.path as osp


default_logging_level = logging.INFO


def patch_new_level_in_logging(level, name,
                               color_spec=('green', None, True)):
    if hasattr(logging, name):
        logging.getLogger().warning(
            "Duplicate attempt to add logging level %s(%s)!", name, level)
        return

    if not (isinstance(level, int)):
        raise ValueError("(level: %s, name: %s) must be int, but was: "
                         "(%s, %s)" % (level, name, type(level), type(name)))
    logging.addLevelName(level, name)
    setattr(logging, name, level)

    def new_log_method(self, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, msg, args, **kwargs)

    setattr(logging.Logger, name.lower(), new_log_method)

    from rainbow_logging_handler import RainbowLoggingHandler

    rlog = logging.getLogger()
    for lh in rlog.handlers:
        if isinstance(lh, RainbowLoggingHandler):
            lh._column_color['%(message)s'][level] = color_spec


def _classify_fpaths(fpaths):
    """
    Split filelist in 3: (confs|'None'), (yaml|yamls) or and missing anc check
    """
    yamls, confs, missing = [], [], []
    for f in fpaths:
        orig_f = f
        f = osp.normpath(osp.abspath(osp.expanduser(f)))
        if osp.exists(f):
            if osp.splitext(f)[1] in '.yaml' or '.yamls':
                yamls.append(f)
            else:
                confs.append(f)
        else:
            missing.append(orig_f)

    return yamls, confs, missing


def _load_logconfs(yaml_fpaths, conf_fpaths):
    """
    Loads one of the two list-of-fpaths using the respective logging methods.

    :return:
        the list of files loaded
    """
    from logging import config as lcfg

    logconf_src = None
    if yaml_fpaths:
        logconf_src = yaml_fpaths
        for fpath in yaml_fpaths:
            log_dict = {}
            with io.open(fpath) as fd:
                log_dict.update(yaml.safe_load(fd))
        lcfg.dictConfig(log_dict)
    elif conf_fpaths:
        logconf_src = conf_fpaths
        lcfg.fileConfig(conf_fpaths)

    return logconf_src


def _setup_color_logs(frmt):
    from rainbow_logging_handler import RainbowLoggingHandler

    color_handler = RainbowLoggingHandler(
        sys.stderr,
        color_message_debug=('grey', None, False),
        color_message_info=('blue', None, False),
        color_message_warning=('yellow', None, True),
        color_message_error=('red', None, True),
        color_message_critical=('white', 'red', True),
    )

    ## NOTE: CLUDGE backreference to `polyvers`!!!
    from .. import NOTICE, TRACE
    color_handler._column_color['%(message)s'][NOTICE] = ('green', None, False)
    color_handler._column_color['%(message)s'][TRACE] = ('grey', None, False)

    formatter = logging.Formatter(frmt)
    color_handler.setFormatter(formatter)

    ## Be conservative and apply color only when
    #  log-config looks like the "basic".
    #
    rlog = logging.getLogger()
    if rlog.handlers and isinstance(rlog.handlers[0], logging.StreamHandler):
        rlog.removeHandler(rlog.handlers[0])
        rlog.addHandler(color_handler)


def _count_multiflag_in_argv(args, short, long, eliminate=False):
    """
    Match flags in `argvs` list, in short/long form, and optionally remove them.

    :param eliminate:
        If true, returned flags will have those matching, removed.
    :return:
        the 2-tuple (num-of-matches, new-args) where `new-args` possibly
        have flags missing.
    """
    import re

    long = '--%s' % long
    nmatches = 0
    new_args = []
    for flag in args:
        if flag == long:
            nmatches += 1
            if eliminate:
                continue

        elif re.match('^-[a-z]+', flag, re.I):
            nmatches += flag.count(short)
            if eliminate:
                flag = flag.replace(short, '')
                if flag == '-':
                    continue

        new_args.append(flag)

    return nmatches, new_args


def log_level_from_argv(args,
                        start_level: int,
                        eliminate_verbose=False,
                        eliminate_quiet=False,
                        verbosity_step=10):
    """
    :param start_level_index:
        some existing level
    """
    if not isinstance(start_level, int):
        raise ValueError(
            "Expecting an *integer* for logging level, got '%s'!" % start_level)
    levels = list(sorted(logging._levelToName))

    nverbose, new_args = _count_multiflag_in_argv(args, 'v', 'verbose',
                                                  eliminate_verbose)
    nquiet, new_args = _count_multiflag_in_argv(new_args, 'q', 'quiet',
                                                eliminate_quiet)

    level = start_level + verbosity_step * (nquiet - nverbose)
    level = max(0, min(levels[-1], level))

    return level, new_args


def init_logging(
        level=default_logging_level,
        logconf=None,
        color=None,
        logger=None,
        **kwds):
    """
    :param level:
        Root-logger's level; Overrides `logconf` if given, INFO otherwise.
    :param logconf:
        File(s) to configure loggers; set `[]` to prohibit loading any logconf file.
        Allowed file-extensions:

          - '.conf' (implied if missing) .
          - '.yml'/'yaml'

        The `~` in the path expanded to $HOME.
        See https://docs.python.org/3/library/logging.config.html
    :type logconf:
        None, str, seq[str]
    :param color:
        Whether to color log-messages; if undefined, true only in consoles.
    :param logger:
        Which logger to use to log logconf source(must support info and debug).
        if missing, derived from this module.
    :param kwds:
        Passed directly to :func:`logging.basicConfig()` (e.g. `filename`);
        used only id default HOME ``logconf.yaml`` file is NOT read.
    """
    logconf_src = None
    missing_logconfs = None
    self_level = logging.DEBUG if level is None else logging.INFO
    if not logger:
        logger = logging.getLogger(__name__)

    if logconf and not isinstance(logconf, (list, tuple)):
        logconf = [logconf]
    if logconf:
        yamls, confs, missing_logconfs = _classify_fpaths(logconf)
        if bool(yamls) and bool(confs):
            raise ValueError(
                "Cannot handle MIXED logconf-file extensions: %s\n"
                "  Specify either '.yaml' or '.conf'" % (logconf, ))

        logconf_src = _load_logconfs(yamls, confs)

    if logconf_src:  # Some logconf applied
        if level is not None:
            # Respect given level, overriding Logconf-file on root-logger
            logging.getLogger().setLevel(level)

    else:  # No logconf applied
        logconf_src = 'explicit(level=%s, default_level=%s, kw=%s)' % (
            level, default_logging_level, kwds)

        if level is None:
            ## Apply default Logging-config.
            #
            level = logging.INFO
        frmt = kwds.pop('format',
                        "%(asctime)-15s|%(levelname)5.5s|%(name)s|%(message)s")
        logging.basicConfig(level=level, format=frmt, **kwds)
        # Because `basicConfig()` ignores root-logger if this re-invoked.
        logging.getLogger().setLevel(level)

        if color is None:
            color = sys.stderr.isatty()
        if color:
            _setup_color_logs(frmt)

    logging.captureWarnings(True)

    logger.log(self_level, "Logging-configurations source: %s\n"
               "  missing logconf-files: %s",
               logconf_src, missing_logconfs)


def exit_with_pride(reason=None,
                    warn_color='\x1b[31;1m', err_color='\x1b[1m',
                    logger=None):
    """
    Return an *exit-code* and logs error/fatal message for ``main()`` methods.

    :param reason:
        - If reason is None, exit-code(0) signifying OK;
        - if exception,  print colorful (if tty) stack-trace, and exit-code(-1);
        - otherwise, prints str(reason) colorfully (if tty) and exit-code(1),
    :param warn_color:
        ansi color sequence for stack-trace (default: red)
    :param err_color:
        ansi color sequence for stack-trace (default: white-on-red)
    :param logger:
        Which logger to use to log reason (must support info and fatal).
        if missing, derived from this module.

    :return:
        (0, 1 -1), for reason == (None, str, Exception) respectively.

    Note that returned string from ``main()`` are printed to stderr and
    exit-code set to bool(str) = 1, so print stderr separately and then
    set the exit-code.

    For colors use :meth:`RainbowLoggingHandler.getColor()`, defaults:
    - '\x1b[33;1m': yellow+bold
    - '\x1b[31;1m': red+bold

    Note: it's better to have initialized logging.
    """
    if reason is None:
        return 0
    if not logger:
        logger = logging.getLogger(__name__)

    if isinstance(reason, BaseException):
        color = err_color
        exit_code = -1
        logmeth = fnt.partial(logger.fatal, exc_info=True)
    else:
        color = warn_color
        exit_code = 1
        logmeth = logger.error

    if sys.stderr.isatty():
        reset = '\x1b[0m'
        reason = '%s%s%s' % (color, reason, reset)

    logmeth(reason)
    return exit_code
