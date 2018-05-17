#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"A launch script to execute the wheel: ``python polyversion-*.whl <project>``"

## Launch-script sets up sys-path so relative imports work in ``main()`.

import sys


def main():
    """
    Describe the version of a *polyvers* projects from git tags.

    USAGE:
        %(prog)s [PROJ-1] ...

    See http://polyvers.readthedocs.io

    - Invokes :func:`polyversion.run()` with ``sys.argv[1:]``.
    - In order to set cmd-line arguments, invoke directly the function above.
    """
    import polyversion
    polyversion.run(*sys.argv[1:])


if __name__ == '__main__':
    ## Pep366 must always be the 1st thing to run.
    if not globals().get('__package__'):
        __package__ = "polyversion"  # noqa: A001 F841 @ReservedAssignment

    main()
