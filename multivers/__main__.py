#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"Cmd-line entrypoint to bump independently PEP-440 versions on multi-project Git repos."
import sys


if __name__ == '__main__':
    __import__('multivers').main(*sys.argv[1:])
