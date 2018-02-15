#!/usr/bin/env pythonw
#
# Copyright 2014-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Commands to inspect configurations and other cli infos."""

from collections import OrderedDict
import os
import sys
from typing import Sequence, Text, List, Tuple  # @UnusedImport

from toolz import dicttoolz as dtz

import functools as fnt
import os.path as osp

from . import cmdlets
from ._vendor import traitlets as trt
from ._vendor.traitlets import (
    Bool, Unicode, FuzzyEnum, Instance)  # @UnresolvedImport


def prepare_matcher(terms, is_regex):
    import re

    def matcher(r):
        if is_regex:
            return re.compile(r, re.I).search
        else:
            return lambda w: r.lower() in w.lower()

    matchers = [matcher(t) for t in terms]

    def match(word):
        return any(m(word) for m in matchers)

    return match


def prepare_search_map(all_classes, own_traits):
    """
    :param own_traits:
        bool or None (no traits)
    :return:
        ``{'ClassName.trait_name': (class, trait)`` When `own_traits` not None,
        ``{clsname: class}``) otherwise.
        Note: 1st case might contain None as trait!
    """
    if own_traits is None:
        return OrderedDict([
            (cls.__name__, cls)
            for cls in all_classes])

    if own_traits:
        class_traits = lambda cls: cls.class_own_traits(config=True)
    else:
        class_traits = lambda cls: cls.class_traits(config=True)

    ## Not using comprehension
    #  to work for classes with no traits.
    #
    smap = []
    for cls in all_classes:
        clsname = cls.__name__
        traits = class_traits(cls)
        if not traits:
            smap.append((clsname + '.', (cls, None)))
            continue

        for attr, trait in sorted(traits.items()):
            smap.append(('%s.%s' % (clsname, attr), (cls, trait)))

    return OrderedDict(smap)


def prepare_help_selector(only_class_in_values, verbose):
    from ._vendor.traitlets import config as trc

    if only_class_in_values:
        if verbose:
            def selector(ne, cls):
                return cls.class_get_help()
        else:
            def selector(ne, cls):
                from ipython_genutils.text import wrap_paragraphs

                help_lines = []
                base_classes = ', '.join(p.__name__ for p in cls.__bases__)
                help_lines.append(u'%s(%s)' % (cls.__name__, base_classes))
                help_lines.append(len(help_lines[0]) * u'-')

                cls_desc = getattr(cls, 'description', None)
                if not isinstance(cls_desc, str):
                    cls_desc = cls.__doc__
                if cls_desc:
                    help_lines.extend(wrap_paragraphs(cls_desc))
                help_lines.append('')

                try:
                    txt = cls.examples.default_value.strip()
                    if txt:
                        help_lines.append("Examples")
                        help_lines.append("--------")
                        help_lines.append(trc.indent(trc.dedent(txt)))
                        help_lines.append('')
                except AttributeError:
                    pass

                return '\n'.join(help_lines)

    else:
        def selector(name, v):
            cls, attr = v
            if not attr:
                #
                ## Not verbose and class not owning any trait.
                return "--%s" % name
            else:
                return cls.class_get_trait_help(attr)

    return selector


class ConfigCmd(cmdlets.Cmd):
    "Commands to manage configurations and other cli infos."

    examples = Unicode("""
        - Ask help on parameters affecting the source of the configurations::
              %(cmd_chain)s desc  config_paths  show_config

        - Show config-param values for all params containing word "mail"::
              %(cmd_chain)s show  --versbose  mail

        - Show values originating from files::
              %(cmd_chain)s show  --source file

        - Show configuration paths::
              %(cmd_chain)s paths
    """)

    def __init__(self, **kwds):
            super().__init__(
                subcommands=cmdlets.build_sub_cmds(*config_subcmds),
                **kwds)


class WriteCmd(cmdlets.Cmd):
    """
    Store config defaults into specified path(s); '{confpath}' assumed if none specified.

    SYNTAX
        %(cmd_chain)s [OPTIONS] [<config-path-1>] ...

    - If a path resolves to a folder, the filename '{appname}_config.py' is appended.
    - It OVERWRITES any pre-existing configuration file(s)!
    """

    examples = Unicode("""
        - Generate a config-file at your home folder::
              %(cmd_chain)s ~/my_conf

        - To re-use the generated custom config-file alone, use the option::
              --config-paths=~/my_conf  ...
    """)

    def run(self, *args):
        ## Prefer to modify `classes` after `initialize()`, or else,
        #  the cmd options would be irrelevant and fatty :-)
        self.classes = all_configurables(self)
        args = args or [None]
        for fpath in args:
            self.write_default_config(fpath, self.force)


class InfosCmd(cmdlets.Cmd):
    """
    List paths and other intallation infos.

    Some of the environment-variables affecting configurations:
        HOME, USERPROFILE,          : where configs & DICE projects are stored
                                      (1st one defined wins)
        <APPNAME>_CONFIG_PATHS      : where to read configuration-files.
    """

    app_infos = Instance(
        dict,
        default_value={},
        help="Extra infos to put at the top of the output of this command"
    )

    def _collect_env_vars(self, classes):
        classes = (cls
                   for cls
                   in self._classes_inc_parents(classes))
        return [trait.metadata['envvar']
                for cls in classes
                for trait
                in cls.class_own_traits(envvar=(lambda ev: bool(ev))).values()]

    def run(self, *args):
        import inspect

        if len(args) > 0:
            raise cmdlets.CmdException(
                "Cmd %r takes no arguments, received %d: %r!"
                % (self.name, len(args), args))

        sep = osp.sep
        l2_yaml_list_sep = '\n    - '

        def sterilize(func, fallback=None):
            try:
                return func()
            except Exception as ex:
                return "<%s due to: %s(%s)>" % (
                    fallback or 'invalid', type(ex).__name__, ex)

        def format_tuple(path, files: List[Text]):
            endpath = sep if path[-1] != sep else ''
            return '    - %s%s: %s' % (path, endpath, files or '')

        app_name = self.name
        app_path = inspect.getfile(type(self))

        # TODO: paths not valid YAML!  ...and renable TC.
        yield "APP:"
        yield "  %s_path: %s" % (app_name, app_path)
        yield "  python_path: %s" % sys.prefix

        for k, v in self.app_infos.items():
            yield '  %s: %s' % (k, v)

        yield "CONFIG:"
        config_paths = l2_yaml_list_sep.join([''] + self.config_paths)
        yield "  config_paths: %s" % (config_paths or 'null')

        loaded_cfgs = self.loaded_config_files
        if loaded_cfgs:
            yield "  LOADED_CONFIGS:"
            yield from (format_tuple(p, f) for p, f in loaded_cfgs)
        else:
            yield "  LOADED_CONFIGS: null"

        var_names = """HOME HOMEDRIVE HOMEPATH USERPROFILE
                     TRAITLETS_APPLICATION_RAISE_CONFIG_FILE_ERROR"""
        yield "ENV_VARS:"
        trait_envvars = self._collect_env_vars(all_configurables(self))
        for vname in sorted(set(var_names.split() + trait_envvars)):
            yield "  %s: %r" % (vname, os.environ.get(vname))


class ShowCmd(cmdlets.Cmd):
    """
    Print configurations (defaults | files | merged) before any validations.

    SYNTAX
        %(cmd_chain)s [OPTIONS] [--source=(merged | default)] [<search-term-1> ...]
        %(cmd_chain)s [OPTIONS] --source file

    - Search-terms are matched case-insensitively against '<class>.<param>'.
    - Use --verbose to view values for config-params as they apply in the
      whole hierarchy (not
    - Results are sorted in "application order" (later configurations override
      previous ones); use --sort for alphabetical order.
    - Warning: Defaults/merged might not be always accurate!
    - Tip: you may also add `--show-config` global option on any command
      to view configured values accurately on runtime.
    """

    examples = Unicode("""
        - View all "merged" configuration values::
              %(cmd_chain)s

        - View all "default" or "in file" configuration values, respectively::
              %(cmd_chain)s --source defaults
              %(cmd_chain)s --s f

        - View help on specific parameters::
              %(cmd_chain)s config_paths
              %(cmd_chain)s -e '.*path.*'

        - List classes matching a regex::
              %(cmd_chain)s -ecl '.*cmd$'
    """)

    verbose = Bool(
        config=True,
        help="Print infos from the whole hierarchy, including intermediate classes."
    )

    source = FuzzyEnum(
        'defaults files merged'.split(),
        default_value='merged',
        allow_none=False,
        help="""
        Show configuration parameters in code, stored on disk files, or merged,
        respectively."""
    ).tag(config=True)

    list = Bool(
        help="Just list any matches."
    ).tag(config=True)

    regex = Bool(
        help="Search terms as regular-expressions."
    ).tag(config=True)

    sort = Bool(
        help="""
        Sort classes alphabetically; by default, classes listed in "application order",
        that is, later configurations override previous ones.
        """
    ).tag(config=True)

    def __init__(self, **kwds):
        kwds.setdefault('raise_config_file_errors', False)
        super().__init__(**kwds)
        self.aliases = {
            ('s', 'source'): ('ShowCmd.source',
                              ShowCmd.source.help)
        }
        self.flags = {
            ('l', 'list'): (
                {type(self).__name__: {'list': True}},
                type(self).list.help
            ),
            ('e', 'regex'): (
                {type(self).__name__: {'regex': True}},
                type(self).regex.help
            ),
            ('t', 'sort'): (
                {type(self).__name__: {'sort': True}},
                type(self).sort.help
            ),
        }

    def initialize(self, argv=None):
        ## Copied from `Cmd.initialize()`.
        #
        self.parse_command_line(argv)
        cfg = self.read_config_files()
        self._loaded_config = cfg

    def _yield_file_configs(self, config, classes=None):
        assert not classes, (classes, "should be empty")

        for k, v in config.items():
            yield k
            try:
                for kk, vv in v.items():
                    yield '  +--%s = %s' % (kk, vv)
            except:  # @IgnorePep8
                yield '  +--%s' % v

    def _yield_configs_and_defaults(self, config, search_terms,
                                    merged: bool):
        verbose = self.verbose
        conf_classes = all_configurables(self)
        get_classes = (self._classes_inc_parents
                       if verbose else
                       self._classes_with_config_traits)
        all_classes = list(get_classes(conf_classes))

        ## Merging needs to visit all hierarchy.
        own_traits = not (verbose or merged)

        search_map = prepare_search_map(all_classes, own_traits)

        if search_terms:
            matcher = prepare_matcher(search_terms, self.regex)
            search_map = dtz.keyfilter(matcher, search_map)

        items = search_map.items()
        if self.sort:
            items = sorted(items)  # Sort by class-name (traits always sorted).

        classes_configured = {}
        for key, (cls, trait) in items:
            if self.list:
                yield key
                continue
            if not trait:
                ## Not --verbose and class not owning traits.
                continue

            clsname, trtname = key.split('.')

            ## Print own traits only, even when "merge" visits all.
            #
            sup = super(cls, cls)
            if not verbose and getattr(sup, trtname, None) is trait:
                continue

            ## Instanciate classes once, to merge values.
            #
            obj = classes_configured.get(cls)
            if obj is None:
                try:
                    ## Exceptional rule for Project-zygote.
                    #  TODO: delete when project rule is gone.
                    #
                    if cls.__name__ == 'Project':
                        cls.new_instance('test', None, config)
                    else:
                        obj = cls(config=config)
                except Exception as ex:
                    self.log.warning("Falied initializing class '%s' due to: %r",
                                     clsname, ex)

                    ## Assign config-values as dummy-object's attributes.
                    #  Note: no merging of values now!
                    #
                    class C:
                        pass
                    obj = C()
                    obj.__dict__ = dict(config[clsname])
                classes_configured[cls] = obj

                ## Print 1 class-line for all its traits.
                #
                base_classes = ', '.join(p.__name__ for p in cls.__bases__)
                yield '%s(%s)' % (clsname, base_classes)

            if merged:
                try:
                    val = getattr(obj, trtname, '??')
                except trt.TraitError as ex:
                    self.log.warning("Cannot merge '%s' due to: %r", trtname, ex)
                    val = "<invalid due to: %s>" % ex
            else:
                val = repr(trait.default())
            yield '  +--%s = %s' % (trtname, val)

    def run(self, *args):
        source = self.source.lower()
        self.log.info("Listing '%s' values for search-terms: %s...",
                      source, args)

        if source == 'files':
            if len(args) > 0:
                raise cmdlets.CmdException(
                    "Cmd '%s --source files' takes no arguments, received %d: %r!"
                    % (self.name, len(args), args))

            func = self._yield_file_configs
        elif source == 'defaults':
            func = fnt.partial(self._yield_configs_and_defaults, merged=False)
        elif source == 'merged':
            func = fnt.partial(self._yield_configs_and_defaults, merged=True)
        else:
            raise AssertionError('Impossible enum: %s' % source)

        config = self._loaded_config

        yield from func(config, args)


class DescCmd(cmdlets.Cmd):
    """
    List and print help for configurable classes and parameters.

    SYNTAX
        %(cmd_chain)s [-l] [-c] [-t] [-v] [<search-term> ...]

    - If no search-terms provided, returns all.
    - Search-terms are matched case-insensitively against '<class>.<param>',
      or against '<class>' if --class.
    - Use --verbose (-v) to view config-params from the whole hierarchy, that is,
      including those from intermediate classes.
    - Use --class (-c) to view just the help-text of classes.
    - Results are sorted in "application order" (later configurations override
      previous ones); use --sort for alphabetical order.
    """

    examples = Unicode(r"""
        - Just List::
              %(cmd_chain)s --list         # List configurable parameters.
              %(cmd_chain)s -l --class     # List configurable classes.
              %(cmd_chain)s -l --verbose   # List config params in all hierarchy.

        -  Exploit the fact that <class>.<param> are separated with a dot('.)::
              %(cmd_chain)s -l Cmd.        # List commands and their own params.
              %(cmd_chain)s -lv Cmd.       # List commands including inherited params.
              %(cmd_chain)s -l ceiver.     # List params of TStampReceiver spec class.
              %(cmd_chain)s -l .user       # List parameters starting with 'user' prefix.

        -  Use regular expressions (--regex)::
              %(cmd_chain)s -le  ^t.+cmd   # List params for cmds starting with 't'.
              %(cmd_chain)s -le  date$     # List params ending with 'date'.
              %(cmd_chain)s -le  mail.*\.  # Search 'mail' anywhere in class-names.
              %(cmd_chain)s -le  \..*mail  # Search 'mail' anywhere in param-names.

        Tip:
          Do all of the above and remove -l.
          For instance::
              %(cmd_chain)s -c DescCmd    # View help for this cmd without its parameters.
              %(cmd_chain)s -t Spec.      # View help sorted alphabetically
    """)

    list = Bool(
        help="Just list any matches."
    ).tag(config=True)

    clazz = Bool(
        help="Print class-help only; matching happens also on class-names."
    ).tag(config=True)

    regex = Bool(
        help="""
        Search terms as regular-expressions.

        Example:
             %(cmd_chain)s -e ^DescCmd.regex

        will print the help-text of this parameter (--regex, -e).
        """
    ).tag(config=True)

    sort = Bool(
        help="""
        Sort classes alphabetically; by default, classes listed in "application order",
        that is, later configurations override previous ones.
        """
    ).tag(config=True)

    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.flags = {
            ('l', 'list'): (
                {type(self).__name__: {'list': True}},
                type(self).list.help
            ),
            ('e', 'regex'): (
                {type(self).__name__: {'regex': True}},
                type(self).regex.help
            ),
            ('c', 'class'): (
                {type(self).__name__: {'clazz': True}},
                type(self).clazz.help
            ),
            ('t', 'sort'): (
                {type(self).__name__: {'sort': True}},
                type(self).sort.help
            ),
        }

    def run(self, *args):
        ## Prefer to modify `class_names` after `initialize()`, or else,
        #  the cmd options would be irrelevant and fatty :-)
        get_classes = (self._classes_inc_parents
                       if self.clazz or self.verbose else
                       self._classes_with_config_traits)
        all_classes = list(get_classes(all_configurables(self)))
        own_traits = None if self.clazz else not self.verbose

        search_map = prepare_search_map(all_classes, own_traits)
        if args:
            matcher = prepare_matcher(args, self.regex)
            search_map = dtz.keyfilter(matcher, search_map)
        items = search_map.items()
        if self.sort:
            items = sorted(items)  # Sort by class-name (traits always sorted).

        selector = prepare_help_selector(self.clazz, self.verbose)
        for name, v in items:
            if self.list:
                yield name
            else:
                yield selector(name, v)


config_subcmds = (
    WriteCmd,
    InfosCmd,
    ShowCmd,
    DescCmd,
)


def all_configurables(cmd):
    return list(config_subcmds) + cmd.root_app().all_app_configurables
