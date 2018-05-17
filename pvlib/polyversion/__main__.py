#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
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

    main()
