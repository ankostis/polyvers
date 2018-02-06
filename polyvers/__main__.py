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


def main(argv=None, **app_init_kwds):
    """
    Handle some exceptions politely and return the exit-code.

    :param argv:
        Invoke it without anything, or ``sys.argv[1:]``, or [].
    """
    req_ver = (3, 6)
    if sys.version_info < req_ver:
        raise NotImplemented(
            "Sorry, Python >= %s is required, found: %s" %
            (req_ver, sys.version_info))

    if argv is None:
        argv = sys.argv[1:]

    ## At these early stages, any log cmd-line option
    #  enable DEBUG logging ; later will be set by `baseapp` traits.
    log_level = logging.DEBUG if (set('-v --verbose'.split()) & set(argv)) else None

    ## Rename app!
    #
    #  NOTE: All imports in this file must be absolute!
    import polyvers as mypack
    if sys.argv:
        mypack.APPNAME = osp.basename(sys.argv[0])

    from polyvers import logconfutils as mlu
    log = logging.getLogger('%s.main' % mypack.APPNAME)
    mlu.init_logging(level=log_level,
                     logconf_files=osp.join('~', '.%s.yaml' % mypack.APPNAME))

    ## Imports in separate try-block due to CmdException.
    #
    try:
        from polyvers import cmdutils as cu, mainpump as mpu
        from polyvers._vendor.traitlets import TraitError
        from polyvers.cli import PolyversCmd
    except Exception as ex:
        ## Print stacktrace to stderr and exit-code(-1).
        return mlu.exit_with_pride(ex, logger=log)

    try:
        cmd = cu.make_cmd(PolyversCmd, argv, **app_init_kwds)
        return mpu.pump_cmd(cmd.start()) and 0
    except (cu.CmdException, TraitError) as ex:
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

    main(sys.argv[1:])
