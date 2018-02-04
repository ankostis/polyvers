# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""AutoInstance traitlet creates an instance from config-params."""

from traitlets import TraitError, Any, Instance, This
from traitlets.config import Config, Configurable


class AutoInstance(Instance):
    def validate(self, obj, value):
        iclass = self.klass
        if isinstance(value, iclass):
            return value
        elif not (issubclass(iclass, Configurable) and
                  isinstance(value, dict)):
            self.error(obj, value)  # Report original error.
        else:
            ## Auto-create configurables.
            #
            try:
                value = iclass(parent=obj, **value)
#                 # Ensure element's value has highest priority as config.
#                 value.udate_config(self._prefix_element_params(iclass.__name__, value))
            except TraitError as _:
                self.error(obj, value)  # Report original error.

        return value
