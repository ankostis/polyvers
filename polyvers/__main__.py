#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"Cmd-line entrypoint to bump independently PEP-440 versions on multi-project Git repos."
import logging
import sys

import os.path as osp


APPNAME = 'polyvers'

log = logging.getLogger('%s.main' % APPNAME)


def main(argv=None, **app_init_kwds):
    """
    Handles some exceptions politely and returns the exit-code.

    :param argv:
        If `None`, use :data:`sys.argv`; use ``[]`` to explicitly use no-args.
    """
    from . import mlogutils as mlu

    if sys.version_info < (3, 6):
        return mlu.exit_with_pride(
            "Sorry, Python >= 3.4 is required, found: %s" % sys.version_info,
            logger=log)

    ## At these early stages, any log cmd-line option
    #  enable DEBUG logging ; later will be set by `baseapp` traits.
    log_level = logging.DEBUG if mlu.is_any_log_option(argv) else None

    mlu.init_logging(level=log_level,
                     default_logconf_file=osp.join('~', '.%s.yaml' % APPNAME))

    ## Imports in separate try-block due to CmdException.
    try:
        from . import traitcmdutils as tcu
        from ._vendor.traitlets import TraitError
        from .polyvers import CmdException, Polyvers
    except Exception as ex:
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)

    try:
        cmd = tcu.make_cmd(Polyvers, argv, **app_init_kwds)
        return tcu.pump_cmd(cmd.start()) and 0
    except (CmdException, TraitError) as ex:
        log.debug('App exited due to: %r', ex, exc_info=1)
        ## Suppress stack-trace for "expected" errors but exit-code(1).
        return mlu.exit_with_pride(str(ex), logger=log)
    except Exception as ex:
        ## Log in DEBUG not to see exception x2, but log it anyway,
        #  in case log has been redirected to a file.
        log.debug('App failed due to: %r', ex, exc_info=1)
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)


if __name__ == '__main__':
    if __package__ is None:
        __package__ = "polyvers"  # @ReservedAssignment

    __import__('polyvers').__main__.main(*sys.argv[1:])
