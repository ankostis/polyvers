# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""AutoInstance traitlet creates an instance from config-params."""

from ._vendor.traitlets.traitlets import Instance
from ._vendor.traitlets.config.configurable import Configurable


class AutoInstance(Instance):
    _cast_types = dict

    def cast(self, value):
        iclass = self.klass
        if (issubclass(iclass, Configurable) and isinstance(value, dict)):
            value = iclass(**value)
            ## Mark it, to set `parent` when known (on `validate()`).
            value._auto_instanciated_dict = value
        else:
            value = iclass(value)

        return value

    def validate(self, obj, value):
        iclass = self.klass
        if isinstance(value, iclass):
            return value
        elif (issubclass(iclass, Configurable) and isinstance(value, dict)):
            value = iclass(parent=obj, **value)
        else:
            values_dict = getattr(value, '_auto_instanciated_dict', None)
            if values_dict is not None:
                delattr(value, '_auto_instanciated_dict')
                if isinstance(obj, Configurable):
                    value.parent = obj
                    value.config = obj.config
                    vars(value).update(values_dict)

        return super().validate(obj, value)
