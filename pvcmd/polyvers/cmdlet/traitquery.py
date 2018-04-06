#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""
Utility to query traits of :class:`HasTraits` and build classes like `Printable`.

See query reus on :func:`select_traits()`
"""
from typing import Union, Optional, Tuple, Any, Sequence

from .._vendor import traitlets as trt


def _find_1st_mro_with_classprop(has_traits: trt.HasTraits,
                                 classprop_selector: str,
                                 ) -> Optional[Tuple[trt.MetaHasTraits, Any]]:
    classprop = classprop_selector
    for cls in type(has_traits).mro():
        ptraits = vars(cls).get(classprop)
        if ptraits is not None:
            return cls, ptraits  # type: ignore


def _select_traits_from_classprop(has_traits: trt.HasTraits,
                                  classprop_selector: str,
                                  first_mro_class: trt.MetaHasTraits,
                                  tnames: Union[str, Sequence, None]):
    """
    :param has_traits:
        the instance for which it is invokced
    :param first_mro_class:
        the 1st baseclass of :attr:`has_traits` in `mro()` where
        the class-prop named :attr:`classprop_selector` is defined;
        practically, :meth:`_find_1st_mro_with_classprop()` results,
        when not none.
    :param tnames:
        its contents
    """
    if not tnames:
        return ()

    if not isinstance(tnames, (list, tuple)):  # TODO: isinstance([], (). SET)
        tnames = [tnames]

    if '-' in tnames:
        tnames = [tn for tn in tnames
                  if tn != '-'] + list(first_mro_class.class_own_traits())  # type: ignore

    bads = set(tnames) - set(has_traits.traits())
    if bads:
        raise AssertionError(
            "Class-property `%s.%s` contains unknown trait-names: %s" %
            (first_mro_class.__name__,
             classprop_selector, ', '.join(bads)))

    return tnames


def select_traits(has_traits: trt.HasTraits,
                  marker_baseclass: type,
                  classprop_selector: str = None,
                  tag_selector: str = None,
                  ) -> Optional[Sequence[str]]:
    """
    Follow elaborate rules to select certain traits of a :class:`HasTrait` class.

    :param has_trait:
        the instance for which it is invokced
    :param marker_baseclass:
        a mixn-class denoting that all traits contained in classes above it
        in reverse `mro()` order must be selected.
        The remaining 2 string-params receive defaults formed out of the name
        of the class given in this param.
    :param classprop_selector:
        The name of a class-property on the `HasTrait` class that participates
        is considered when deciding which traits to select.
        If not given, it's '<subclass-name>_traits'.
        See "selection rules" below
    :param tag_selector:
        The tag-name used as trait-filter for selecting traits on the `HasTrait` class.
        If not given, defaults to '<subclass-name>'.
        See "selection rules" below

    Selection rules:

    1. Scan the ``HasTraits.mro()`` for a class-property named :attr:`classprop_selector`
       and select traits according to its contents:
         - `None`/missing: ignored, visit new `mro()`;
         - <empty>`: shortcut to rule 4, "no traits selected", below.
         - <list of trait-names>: selects them, checking for unknowns,
         - <'-' alone or contained in the list>: print ALL class's OWN traits
           in addition to any other traits contained in the list;
         - '*': print ALL traits in mro().

       But a :attr:`classprop_selector`-named class-property is missing/`None` on
       all baseclasses...

    2. select any traits in mro() marked with :attr:`tag_selector` metadata.

       And if none found...

    3. select all traits owned by classes contained in revese `mro()` order
       from the 1st baseclass inheriting :attr:`marker_baseclass`  and uppwards.

       And if no traits found, ...

    4. don't select any traits.
    """
    assert has_traits and marker_baseclass, (has_traits, marker_baseclass)

    sbcname = marker_baseclass.__name__.lower()
    classprop_selector = classprop_selector or '%s_traits' % sbcname

    if getattr(has_traits, classprop_selector, None) == '*':
        return has_traits.traits()

    res = _find_1st_mro_with_classprop(has_traits, classprop_selector)
    if res:
        return _select_traits_from_classprop(has_traits, classprop_selector, *res)

    tag_selector = tag_selector or sbcname
    tnames = has_traits.traits(**{tag_selector: True})

    if not tnames:
        ## rule 3: Select all traits for subclasses
        #  after(above) `marker_baseclass` in mro().
        #
        subclasses = [cls for cls in type(has_traits).mro()  # type: ignore
                      if issubclass(cls, marker_baseclass) and
                      cls is not marker_baseclass]
        tnames = [tname
                  for cls in subclasses
                  for tname in cls.class_own_traits()]  # type: ignore

    return tnames or ()
