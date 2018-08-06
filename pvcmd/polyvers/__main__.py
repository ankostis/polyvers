#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"Launch-script setting up sys-path so relative imports work in ``main()`."
import sys


def main():
    """
    Cmd-line entrypoint to bump PEP-440 versions on sub-project in Git repos.

    - Invokes :func:`polyvers.cli.run()` with ``sys.argv[1:]``.
    - In order to set cmd-line arguments, invoke directly the function above.
    """
    if not globals().get('__package__'):
        __package__ = "polyvers"  # noqa: A001 F841 @ReservedAssignment

    req_ver = (3, 6)
    if sys.version_info < req_ver:
        raise NotImplementedError(
            "Sorry, Python >= %s is required, found: %s" %
            (req_ver, sys.version_info))

    # ## Rename app!
    # #
    # if sys.argv:
    #     import polyvers
    #     polyvers.APPNAME = osp.basename(sys.argv[0])

    from polyvers import cli
    cli.run(argv=sys.argv[1:])


if __name__ == '__main__':
    ## Pep366 must always be the 1st thing to run.
    if not globals().get('__package__'):
        __package__ = "polyvers"  # noqa: A001 F841 @ReservedAssignment

    sys.exit(main())
