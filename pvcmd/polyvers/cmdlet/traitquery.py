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
from typing import Union, Optional, Sequence, Dict, Any

from .._vendor import traitlets as trt


def _find_1st_mro_with_classprop(has_traits: trt.HasTraits,
                                 classprop_selector: str,
                                 ) -> Optional[trt.MetaHasTraits]:
    """
    :return:
        The 1st baseclass of `has_traits` in its ``mro()`` where
        a non-None class-prop named `classprop_selector` is found.
    """
    for cls in type(has_traits).mro():
        ptraits = vars(cls).get(classprop_selector)
        if ptraits is not None:
            return cls


def _select_traits_from_classprop(has_traits: trt.HasTraits,
                                  classprop_selector: str,
                                  tnames: Union[str, Sequence, None]
                                  ) -> Dict[str, Any]:
    """
    :param has_traits:
        see :meth:`select_traits()`
    :param classprop_selector:
        see :meth:`select_traits()`
    :param tnames:
        its contents
    :raise ValueError:
        when unknown trait-names in `classprop_selector` class-property found.
    """
    first_mro_class = _find_1st_mro_with_classprop(has_traits, classprop_selector)
    assert first_mro_class, (first_mro_class, has_traits, classprop_selector)

    if not isinstance(tnames, (list, tuple)):  # TODO: isinstance([], (). SET)
        tnames = [tnames]

    fetch_own_traits = '-' in tnames
    if fetch_own_traits:
        tnames = [tn for tn in tnames
                  if tn != '-']

    all_traits = has_traits.traits()

    ## Here allow explicit trait-names from all traits,
    #  including above `mixin`` in mro.
    bads = set(tnames) - set(all_traits)
    if bads:
        raise ValueError(
            "Class-property `%s.%s` contains unknown trait-names: %s" %
            (first_mro_class.__name__,
             classprop_selector, ', '.join(bads)))

    traits = {tn: all_traits[tn] for tn in tnames}

    if fetch_own_traits:
        traits.update(first_mro_class.class_own_traits())

    return traits


def _traits_till_mro(traits, mixin) -> Dict[str, Any]:
    if mixin:
        traits = {tn: t for tn, t in traits.items()
                  if issubclass(t.this_class, mixin)}
    return traits


def _select_traits(has_traits: trt.HasTraits,
                   mixin: type = None,
                   classprop_selector: str = None,
                   append_tags=None,
                   **tag_selectors
                   ) -> Dict[str, Any]:
    """the real workhorse, unsorted """
    if mixin:
        if not isinstance(has_traits, mixin):
            raise ValueError(
                "Mixin '%s' is not a subclass of queried '%s'!" %
                (mixin, has_traits))

        sbcname = mixin.__name__.lower()
        if classprop_selector is None:
            classprop_selector = '%s_traits' % sbcname

    ## rule 1: select based on traitnames in class-property.
    #
    cp_traits = None
    if classprop_selector:
        class_tnames = getattr(has_traits, classprop_selector, None)
        if class_tnames is None:
            pass
        elif class_tnames == '*':
            return _traits_till_mro(has_traits.traits(), mixin)
        elif class_tnames:
            cp_traits = _select_traits_from_classprop(
                has_traits, classprop_selector, class_tnames)
            if not append_tags:
                return cp_traits
        else:
            ## If empty, shortcut to "no traits selected" (rule 4).
            return {}

    ## rule 2: select based on trait-tags.
    #
    traits = _traits_till_mro(has_traits.traits(**tag_selectors), mixin)
    if cp_traits:
        traits.update(cp_traits)

    ## rule 3: Select all traits for subclasses
    #  after(above) `mixin` in mro().
    #
    if not traits and mixin:
        subclasses = [cls for cls in type(has_traits).mro()
                      if issubclass(cls, mixin) and
                      cls is not mixin]
        traits = {tname: trait
                  for cls in subclasses
                  for tname, trait in cls.class_own_traits().items()}

    return traits


def select_traits(has_traits: trt.HasTraits,
                  mixin: type = None,
                  classprop_selector: str = None,
                  append_tags=None,
                  **tag_selectors
                  ) -> Dict[str, Any]:
    """
    Follow elaborate rules to select certain traits of a :class:`HasTraits` class.

    :param has_traits:
        the instance to query it's traits
    :param mixin:
        a marker-class denoting that all traits contained in classes above it
        in reverse `mro()` order must be selected.
        The default value for `classprop_selector` is formed out of
        the name of this mixin.
    :param classprop_selector:
        The name of a class-property on the `HasTraits` class to consult
        when querying traits.
        If not given but `mixin` given, it defaults to '<subclass-name>_traits'
        in lower-case,  Otherwise, or if empty-string, rule 1 bypassed.
        See "selection rules" below
    :param append_tags:
        - true: include traits from tags (rule 2), in addition to any from rule 1.
        - false: consider tags (rule 2) only if `classprop_selector` (rule 1)
          were not found / bypassed.
    :param tag_selectors:
        Any tag-names to convey as metadata filters in :meth:`HasTraits.traits()`.
        See "selection rules" below
    :return:
        the trait-names found, or empty

    Selection rules:

    1. Scan the :attr:`classprop_selector` in ``has_traits.mro()`` and select
       class-traits according to its contents:
         - `None`/missing: ignored, visit next in `mro()` / next rule;
         - <empty-str>/<empty-seq>`: shortcut to rule 4, "no traits selected",
           below.
         - <list of trait-names>: selects them, checking for unknowns,
         - <'-' alone or contained in the list>: select ALL class's OWN traits
           in addition to any other traits contained in the list;
         - '*': select ALL traits in mro().

       But if a :attr:`classprop_selector`-named class-property is missing/`None` on
       all baseclasses, or `classprop_selector` was the empty-string...

    2. select any traits in mro() marked with :attr:`tag_selectors` metadata.

       And if none found...

    3. select all traits owned by classes contained in revese `mro()` order
       from the 1st baseclass inheriting :attr:`mixin`  and uppwards.

       And if no traits found, ...

    4. don't select any traits.
    """
    traits = _select_traits(has_traits, mixin, classprop_selector,
                            append_tags, **tag_selectors)
    #return sorted(traits.items(), key=lambda k, v: k)
    return traits
