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


def main(argv=None, cmd_consumer=None, **app_init_kwds):
    """
    Handle some exceptions politely and return the exit-code.

    :param argv:
        If invoked with None, ``sys.argv[1:]`` assumed.
    """
    ## ...so run it again, for when invokced by setuptools cmd.
    if not globals().get('__package__'):
        __package__ = "polyvers"  # noqa: A001 F841 @ReservedAssignment

    req_ver = (3, 6)
    if sys.version_info < req_ver:
        raise NotImplementedError(
            "Sorry, Python >= %s is required, found: %s" %
            (req_ver, sys.version_info))

    if argv is None:
        argv = sys.argv[1:]

    ## At these early stages, any log cmd-line option
    #  enable DEBUG logging ; later will be set by `baseapp` traits.
    from . import logconfutils as mlu
    log_level, argv = mlu.log_level_from_argv(
        argv,
        start_level=25,  # 20=INFO, 25=NOTICE (when patched), 30=WARNING
        eliminate_quiet=True)

    import polyvers as mypack

    # ## Rename app!
    # #
    # if sys.argv:
    #     mypack.APPNAME = osp.basename(sys.argv[0])

    log = logging.getLogger('%s.main' % mypack.APPNAME)
    mlu.init_logging(level=log_level,
                     logconf_files=osp.join('~', '.%s.yaml' % mypack.APPNAME))

    ## Imports in separate try-block due to CmdException.
    #
    try:
        from . import cmdlets, mainpump as mpu
        from ._vendor.traitlets import TraitError
        from .cli import PolyversCmd
    except Exception as ex:
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)

    try:
        cmd = PolyversCmd.make_cmd(argv, **app_init_kwds)  # @UndefinedVariable
        return mpu.pump_cmd(cmd.start(), consumer=cmd_consumer) and 0
    except (cmdlets.CmdException, TraitError) as ex:
        log.debug('App exited due to: %r', ex, exc_info=1)
        ## Suppress stack-trace for "expected" errors but exit-code(1).
        msg = str(ex)
        if type(ex) is not cmdlets.CmdException:
            msg = '%s: %s' % (type(ex).__name__, ex)
        return mlu.exit_with_pride(msg, logger=log)
    except Exception as ex:
        ## Log in DEBUG not to see exception x2, but log it anyway,
        #  in case log has been redirected to a file.
        log.debug('App failed due to: %r', ex, exc_info=1)
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)


if __name__ == '__main__':
    ## Pep366 must always be the 1st thing to run.
    if not globals().get('__package__'):
        __package__ = "polyvers"  # noqa: A001 F841 @ReservedAssignment

    main(sys.argv[1:])
