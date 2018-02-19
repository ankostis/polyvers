#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Polyvers `config` subcommand with `config_paths` properly setup.

In a separate file to avoid loading it on app startup.
"""

from . import cfgcmd, cli


class ConfigCmd(cfgcmd.ConfigCmd, cli.MyCmd):
    pass
