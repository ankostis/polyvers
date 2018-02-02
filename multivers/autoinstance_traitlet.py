# encoding: utf-8
"""AutoInstance traitlet creates an instance from config-params."""

from traitlets import TraitError, Any, Instance, This
from traitlets.config import Config, Configurable


# def _prefix_element_params(element_class_name, element_cfg):
#     """Forbid mixed prefixed & un-prefixed trait-params."""
#     if not element_cfg or all(key[0].islower() for key in element_cfg.keys()):
#         element_cfg = {element_class_name: element_cfg}
#     elif all(key[0].isupper() for key in element_cfg.keys()):
#         pass
#     else:
#         raise TraitError(
#             "AutoInstance's configs must be all (un-)prefixed params for %r"
#             ",\n but keys were: %s" %
#             (element_class_name, list(element_cfg)))
#
#     return element_cfg

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
