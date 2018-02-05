#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#

"Cmd-line entrypoint to bump independently PEP-440 versions on multi-project Git repos."
import io
import logging
import sys

from ruamel import yaml

import functools as fnt
import os.path as osp


APPNAME = 'polyvers'

log = logging.getLogger('%s.main' % APPNAME)

def chain_cmds(app_classes, argv=None, **root_kwds):
    """
    Instantiate(optionally) and run a list of ``[cmd, subcmd, ...]``, linking each one as child of its predecessor.

    :param app_classes:
        A list of cmd-classes: ``[root, sub1, sub2, app]``
        Note: you have to "know" the correct nesting-order of the commands ;-)
    :param argv:
        cmdline args passed to the root (1st) cmd only.
        Make sure they do not contain any sub-cmds.
        Like :meth:`initialize()`, if undefined, replaced with ``sys.argv[1:]``.
    :return:
        The root(1st) cmd to invoke :meth:`Aplication.start()`
        and possibly apply the :func:`pump_cmd()` on its results.

    - Normally `argv` contain any sub-commands, and it is enough to invoke
      ``initialize(argv)`` on the root cmd.  This function shortcuts
      arg-parsing for subcmds with explict cmd-chaining in code.
    - This functions is the 1st half of :meth:`Cmd.launch_instance()`.
    """
    if not app_classes:
        raise ValueError("No cmds to chained passed in!")

    app_classes = list(app_classes)
    root = app = None
    for app_cl in app_classes:
        if type(app_cl).__name__ != 'Application':
                    raise ValueError("Expected an Application-class instance, got %r!" % app_cl)
        if not root:
            ## The 1st cmd is always orphan, and gets returned.
            root = app = app_cl(**root_kwds)
        else:
            app.subapp = app = app_cl(parent=app)
        app.initialize(argv)

    app_classes[0]._instance = app

    return root


class ConsumerBase:
    """Checks if all boolean items (if any) are True, to decide final bool state."""
    any_none_bool = False
    all_true = True

    def __call__(self, item):
        if isinstance(item, bool):
            self.all_true &= item
        else:
            self.any_none_bool = True
        self._emit(item)

    def __bool__(self):
        """
        :return:
            True if all ok, False if any boolean items was false.
        """
        return self.any_none_bool or self.all_true


class PrintConsumer(ConsumerBase):
    """Prints any text-items while checking if all boolean ok."""
    def _emit(self, item):
        if not isinstance(item, bool):
            print(item)


class ListConsumer(ConsumerBase):
    """Collect all items in a list, while checking if all boolean ok."""
    def __init__(self):
        self.items = []

    def _emit(self, item):
        self.items.append(item)



def pump_cmd(cmd_res, consumer=None):
    """
    Sends (possibly lazy) cmd-results to a consumer (by default to STDOUT).

    :param cmd_res:
        Whatever is returnened by a :meth:`Cmd.start()`/`Cmd.run()`.
    :param consumer:
        A callable consuming items and deciding if everything was ok;
        defaults to :class:`PrintConsumer`
    :return:
        ``bool(consumer)``

    - Remember to have logging setup properly before invoking this.
    - This the 2nd half of the replacement for :meth:`Application.launch_instance()`.
    """
    import types

    if not consumer:
        consumer = PrintConsumer()

    if cmd_res is not None:
        if isinstance(cmd_res, types.GeneratorType):
            for i in cmd_res:
                consumer(i)
        elif isinstance(cmd_res, (tuple, list)):
            for i in cmd_res:
                consumer(i)
        else:
            consumer(cmd_res)

    ## NOTE: Enable this code to update `/logconf.yaml`.
    #print('\n'.join(sorted(logging.Logger.manager.loggerDict)))

    return bool(consumer)


def collect_cmd(cmd_res, dont_coalesce=False, assert_ok=False):
    """
    Pumps cmd-result in a new list.

    :param cmd_res:
        A list of items returned by a :meth:`Cmd.start()`/`Cmd.run()`.
        If it is a sole item, it is returned alone without a list.
    :param assert_ok:
        if true, checks :class:`ListConsumer`'s exit-code is not false.
    """
    cons = ListConsumer()
    pump_cmd(cmd_res, cons)
    items = cons.items

    assert not assert_ok or bool(cons), items

    if dont_coalesce:
        return items

    if items:
        if len(items) == 1:
            items = items[0]

        return items


def make_cmd(app, argv=None, **kwargs):
    """
    Instanciate, initialize and return application.

    :param argv:
        Like :meth:`initialize()`, if undefined, replaced with ``sys.argv[1:]``.

    - Tip: Apply :func:`pump_cmd()` on return values to process
      generators of :meth:`run()`.
    - This functions is the 1st half of :meth:`launch_instance()` which
      invokes and discards :meth:`start()` results.
    """
    ## Overriden just to return `start()`.
    cmd = app.instance(**kwargs)
    cmd.initialize(argv)

    return cmd


def init_logging(
        level=None, frmt=None, logconf_file=None,
        color=False,
        default_logconf_file=osp.expanduser(osp.join('~', '.%s.yaml' % APPNAME)),
        **kwds):
    """
    :param level:
        tip: use :func:`is_any_log_option()` to decide if should be None
        (only if None default HOME ``logconf.yaml`` file is NOT read).
    :param default_logconf_file:
        Read from HOME only if ``(level, frmt, logconf_file)`` are none.
    :param kwds:
        Passed directly to :func:`logging.basicConfig()` (e.g. `filename`);
        used only id default HOME ``logconf.yaml`` file is NOT read.
    """
    ## Only read default logconf file in HOME
    #  if no explicit arguments given.
    #
    no_args = all(i is None for i in [level, frmt, logconf_file])
    if no_args and osp.exists(default_logconf_file):
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

    log.debug('Logging-configurations source: %s', logconf_src)


def is_any_log_option(argv):
    """
    Return true if any -v/--verbose/--debug etc options are in `argv`

    :param argv:
        If `None`, use :data:`sys.argv`; use ``[]`` to explicitly use no-args.
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
        which logger to use to log reason (must support info and fatal).

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
        logger = log

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


def main(argv=None, **app_init_kwds):
    """
    Handles some exceptions politely and returns the exit-code.

    :param argv:
        If `None`, use :data:`sys.argv`; use ``[]`` to explicitly use no-args.
    """
    if sys.version_info < (3, 6):
        return exit_with_pride(
            "Sorry, Python >= 3.4 is required, found: %s" % sys.version_info,
            logger=log)

    ## At these early stages, any log cmd-line option
    #  enable DEBUG logging ; later will be set by `baseapp` traits.
    log_level = logging.DEBUG if is_any_log_option(argv) else None

    init_logging(level=log_level, color=True)

    ## Imports in separate try-block due to CmdException.
    try:
        from polyvers._vendor.traitlets import TraitError
        from polyvers._vendor.traitlets.config import Application
        from polyvers.polyvers import CmdException, Polyvers
    except Exception as ex:
        ## Print stacktrace to stderr and exit-code(-1).
        return exit_with_pride(ex, logger=log)

    try:
        cmd = make_cmd(Polyvers, argv, **app_init_kwds)
        return pump_cmd(cmd.start()) and 0
    except (CmdException, TraitError) as ex:
        log.debug('App exited due to: %r', ex, exc_info=1)
        ## Suppress stack-trace for "expected" errors but exit-code(1).
        return exit_with_pride(str(ex), logger=log)
    except Exception as ex:
        ## Log in DEBUG not to see exception x2, but log it anyway,
        #  in case log has been redirected to a file.
        log.debug('App failed due to: %r', ex, exc_info=1)
        ## Print stacktrace to stderr and exit-code(-1).
        return exit_with_pride(ex, logger=log)

if __name__ == '__main__':
    if __package__ is None:
        __package__ = "polyvers"  # @ReservedAssignment

    __import__('polyvers').__main__.main(*sys.argv[1:])
