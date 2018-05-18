#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
from polyvers.utils import oscmd
import sys

import os.path as osp


mydir = osp.dirname(__file__)
proj_path = osp.join(mydir, '..', '..')


def test_README_as_PyPi_landing_page(monkeypatch):
    from docutils import core as dcore

    long_desc = oscmd.PopenCmd(cwd=proj_path).python('setup.py',
                                                     long_description=True)
    assert long_desc

    ## Hide |version| and |today| sphinx-only auto-substitutiond,
    #  that are engraved-out by polyvers.
    long_desc = long_desc.replace('|version|', 'version').replace('|today|', 'today')

    monkeypatch.setattr(sys, 'exit', lambda x: None)
    dcore.publish_string(
        long_desc, enable_exit_status=False,
        settings_overrides={  # see `docutils.frontend` for more.
            'halt_level': 2  # 2=WARN, 1=INFO
        })
