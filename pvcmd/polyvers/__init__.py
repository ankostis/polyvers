# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Top-level package for *polyvers* version-configuration tool."""

from polyversion import polyversion, polytime  # @UnresolvedImport
from .utils import logconfutils as lcu


__all__ = ['polyversion', 'polytime']

APPNAME = __name__.split('.')[0]

__version__ = '0.1.1a1'
__updated__ = '2018-08-07T13:30:07.601687'
__title__ = APPNAME
__summary__ = "Bump independently versions on multi-project git repos"
__uri__ = "https://github.com/JRCSTU/polyvers"
__license__ = "EUPL 1.2"
__copyright__ = "Copyright (C) 2015-2017 European Commission (JRC)"
__music__ = {
    "Patria, by David August":
    "https://soundcloud.com/davidaugust/david-august-patria-feat-sissi-rada",
    "mix by Sissi Rada":
    "https://www.mixcloud.com/sissy-makropoulou/52s-show-on-dfwallace/",
    "mix by Elsa Hewitt":
    "https://www.mixcloud.com/elsarosemaryx/eh-autumn-mixtape-003/",
}


NOTICE = 25
TRACE = 5
lcu.patch_new_level_in_logging(NOTICE, 'NOTICE')
lcu.patch_new_level_in_logging(TRACE, 'TRACE')
lcu.default_logging_level = NOTICE
