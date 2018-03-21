#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from polyvers._vendor.traitlets import traitlets as trt


def test_traitlets_recurse():
    stack = trt.Tuple(trt.Int(), trt.List())
    stack._traits[1]._trait = stack

    ## Class definition will crash if not recursion broken!
    class C(trt.HasTraits):
        t = stack
