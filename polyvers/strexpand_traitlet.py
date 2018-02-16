# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
"""Unicode traitlet interpolating `{abc}` patterns from a "context" dictionary."""

from ._vendor.traitlets import TraitError, Unicode  # @UnresolvedImport


class StrExpand(Unicode):
    """
    PEP-3101 expansion of any  '{key}' from *context* dictionaries (``''.format(d)``).
    """
    def __init__(self, *args, **kw):
        """
        :param ctxt:
            (optional) Either None, the *context* dict to interpolate from,
            or the *context-factory* ``callable(param_name): [dict | None]``.
        """
        self.ctxt = kw.pop('ctxt', None)
        super().__init__(*args, **kw)

    def validate(self, obj, value):
        value = super().validate(obj, value)

        ctxt = self.ctxt
        if ctxt:
            if callable(ctxt):
                ctxt = ctxt(obj, value, self.name)
            if ctxt:
                try:
                    value = value.format(**ctxt)
                except Exception as ex:
                    msg = ("Failed expanding value %r of `%s.%s` %s trait due to: %r"
                           % (value, type(obj).__name__, self.name, self.info(), ex))
                    raise TraitError(msg)

        return value
