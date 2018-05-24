#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Executor of scripts for commands stages."""

from collections import defaultdict
from pathlib import Path
from typing import List, Tuple, Sequence, Set, Match, Dict
import logging
import os

from ._vendor.traitlets import config as trc
from ._vendor.traitlets.traitlets import (
    Unicode, FuzzyEnum,
    Dict as DictTrait, List as ListTrait, Tuple as TupleTrait)  # @UnresolvedImport
from ._vendor.traitlets.traitlets import Bytes, Instance
from .cmdlet import cmdlets
from .utils import fileutil as fu


log = logging.getLogger(__name__)


if 'nt' = os.name:
   d= {
       "*.sh": ['bash', '-c']
       }
class Hooks(trc.Configurable):
    """
    A list of file-paths and file-extension mappings specifying hook-scripts to run.
    """
    globs = ListTrait(
        Unicode(),
        config=True,
        help="Where to search for the scripts.")

    handlers = DictTrait(
        key_trait=Unicode(),
        value_trait=ListTrait(Unicode()),
        default_value={
        },
        config=True,
        help="""
        Mapping of {basename-fnmatch -> exec-prefix} for how to execute globbed scripts

        - where `exec-prefix` is a list of arguments to prefix matched paths:
        - if a '*.d' key is not included in the mapping,

        The default a mapping in Windows allows to execute bash scripts
        (MSYS2, Cygwin), and to use the cmd.exe `start` command.
        """)

