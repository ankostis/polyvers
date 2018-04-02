# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""AutoInstance traitlet creates an instance from config-params."""

from .._vendor.traitlets.config.configurable import Configurable
from .._vendor.traitlets.traitlets import HasTraits, Instance


class AutoInstance(Instance):
    _cast_types = dict

    def cast(self, value):
        iclass = self.klass
        if (issubclass(iclass, HasTraits) and isinstance(value, dict)):
            instance = iclass()
            ## Use :meth:`set_trait_values()` to write also `read_only` traits.
            instance.set_trait_values(**value)

            if issubclass(iclass, Configurable):
                ## Store dict-values so when `validate()` provides config
                #  from `obj.parent`, these values overwrite.
                instance._default_dict = value
        else:
            instance = iclass(value)

        return instance

    def validate(self, obj, value):
        iclass = self.klass

        if isinstance(value, iclass):
            default_dict = getattr(value, '_default_dict', None)
            if default_dict is not None:
                ## Instance created in `cast()`, above, from a default-dict,
                #  but could not update config because `obj` did not exist!
                #
                assert isinstance(default_dict, dict), default_dict
                assert isinstance(value, iclass), (value, iclass)

                delattr(value, '_default_dict')
                default_dict['parent'] = obj
                default_dict['config'] = obj.config

                vars(value).update(default_dict)

            return value

        elif (issubclass(iclass, HasTraits) and isinstance(value, dict)):
            if issubclass(iclass, Configurable):
                instance = iclass(parent=obj)
            else:
                instance = iclass()
            ## Use :meth:`set_trait_values()` to write also `read_only` traits.
            instance.set_trait_values(**value)

            return instance

        return super().validate(obj, value)
