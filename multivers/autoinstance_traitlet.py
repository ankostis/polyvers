# encoding: utf-8
"""AutoInstance traitlet creates an instance from config-params."""

from traitlets import TraitError, Any, List, Instance, This
from traitlets.config import Config


class AutoList(List):
    def _prefix_element_params(self, element_class_name, element_cfg):
        """Forbid mixed prefixed & un-prefixed trait-params."""
        if not element_cfg or all(key[0].islower() for key in element_cfg.keys()):
            element_cfg = {element_class_name: element_cfg}
        elif all(key[0].isupper() for key in element_cfg.keys()):
            pass
        else:
            raise TraitError(
                "AutoList's configs must be all (un-)prefixed params for %r"
                ",\n but keys were: %s" %
                (element_class_name, list(element_cfg)))

        return element_cfg

    def _merge_with_parent_configs(self, nesting_obj, element_class, element_cfg):
        """Ensure element config params overide all defaults up the parent chain."""
        element_cfg = self._prefix_element_params(element_class.__name__, element_cfg)
        obj_it = nesting_obj
        while obj_it:
            element_cfg = {type(obj_it).__name__: element_cfg}
            obj_it = obj_it.parent

        ## No config means no config in parents, no??
        #
        cfg = getattr(nesting_obj, 'config', None)
        if not cfg:
            return Config(element_cfg)

        cfg = cfg.copy()
        cfg.merge(element_cfg)  # Ensure element's has highest priority,

        return cfg

    def validate_elements(self, obj, value):
        length = len(value)
        if length < self._minlen or length > self._maxlen:
            self.length_error(obj, value)

        validated = []
        eltrait = self._trait
        if eltrait is None or isinstance(eltrait, Any):
            return value

        for v in value:
            try:
                v = eltrait._validate(obj, v)
            except TraitError as error:
                ## Auto-create configurables.
                #
                ok = False
                try:
                    if isinstance(eltrait, Instance):
                        cfg = self._merge_with_parent_configs(obj, eltrait.klass, v)
                        v = eltrait.klass(parent=obj, config=cfg)
                        ok = True
                    elif isinstance(eltrait, This):
                        cfg = self._merge_with_parent_configs(obj, eltrait.klass, v)
                        v = eltrait.this_class(parent=obj, config=cfg)
                        ok = True
                except TraitError as _:
                    self.error(obj, v, error)  # Report original error.
                else:
                    if not ok:
                        self.error(obj, v, error)  # Report original error.

            validated.append(v)

        return self.klass(validated)
