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

from ruamel import yaml

import functools as fnt
import os.path as osp


def init_logging(
        level=None, frmt=None, logconf_file=None,
        color=False,
        default_logconf_file=None,
        logger=None,
        **kwds):
    """
    :param level:
        tip: use :func:`is_any_log_option()` to decide if should be None
        (only if None default HOME ``logconf.yaml`` file is NOT read).
    :param default_logconf_file:
        Read from HOME only if ``(level, frmt, logconf_file)`` are none.
    :param logger:
        Which logger to use to log logconf source(must support debug level).
        if missing, derived from this module.
    :param kwds:
        Passed directly to :func:`logging.basicConfig()` (e.g. `filename`);
        used only id default HOME ``logconf.yaml`` file is NOT read.
    """
    ## Only read default logconf file in HOME
    #  if no explicit arguments given.
    #
    no_args = all(i is None for i in [level, frmt, logconf_file])
    if no_args and default_logconf_file and osp.exists(default_logconf_file):
        logconf_file = default_logconf_file

    if logconf_file:
        from logging import config as lcfg

        logconf_file = osp.expanduser(logconf_file)
        if osp.splitext(logconf_file)[1] in '.yaml' or '.yml':
            with io.open(logconf_file) as fd:
                log_dict = yaml.safe_load(fd)
                lcfg.dictConfig(log_dict)
        else:
            lcfg.fileConfig(logconf_file)

        logconf_src = logconf_file
    else:
        if level is None:
            level = logging.INFO
        if not frmt:
            frmt = "%(asctime)-15s:%(levelname)5.5s:%(name)s:%(message)s"
        logging.basicConfig(level=level, format=frmt, **kwds)
        rlog = logging.getLogger()
        rlog.level = level  # because `basicConfig()` does not reconfig root-logger when re-invoked.

        logging.getLogger('pandalone.xleash.io').setLevel(logging.WARNING)

        if color and sys.stderr.isatty():
            from rainbow_logging_handler import RainbowLoggingHandler

            color_handler = RainbowLoggingHandler(
                sys.stderr,
                color_message_debug=('grey', None, False),
                color_message_info=('blue', None, False),
                color_message_warning=('yellow', None, True),
                color_message_error=('red', None, True),
                color_message_critical=('white', 'red', True),
            )
            formatter = formatter = logging.Formatter(frmt)
            color_handler.setFormatter(formatter)

            ## Be conservative and apply color only when
            #  log-config looks like the "basic".
            #
            if rlog.handlers and isinstance(rlog.handlers[0], logging.StreamHandler):
                rlog.removeHandler(rlog.handlers[0])
                rlog.addHandler(color_handler)
        logconf_src = 'explicit(level=%s)' % level

    logging.captureWarnings(True)

    if not logger:
        logger = logging.getLogger(__name__)
    logger.debug('Logging-configurations source: %s', logconf_src)


def is_any_log_option(argv):
    """
    Return true if any -v/--verbose/--debug etc options are in `argv`

    :param argv:
        Main's args to search for log-flags.
    """
    log_opts = '-v --verbose -d --debug --vlevel'.split()
    if argv is None:
        argv = sys.argv
    return argv and set(log_opts) & set(argv)


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
