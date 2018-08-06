#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""
A launch script to execute the *polyversion*.

- Gives pyhon opportunity to setup sys-path so relative imports work in wheel.
- Invokes :func:`~run()` with ``sys.argv[1:]``.
- To specify different than cmd-line arguments, invoke directly that function above.
"""


import sys


def main():
    import polyversion
    polyversion.run(*sys.argv[1:])


if __name__ == '__main__':
    ## Pep366 must always be the 1st thing to run.
    if not globals().get('__package__'):
        __package__ = "polyversion"  # noqa: A001 F841 @ReservedAssignment

    sys.exit(main())
