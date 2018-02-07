#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Utils pumping results out of yielding functions for `main()`."""


def chain_cmds(app_classes, argv=None, **root_kwds):
    """
    Instantiate(optionally) and run a list of ``[cmd, subcmd, ...]``, linking each one as child of its predecessor.

    :param app_classes:
        A list of cmd-classes: ``[root, sub1, sub2, app]``
        Note: you have to "know" the correct nesting-order of the commands ;-)
    :param argv:
        cmdline args passed to the root (1st) cmd only.
        Make sure they do not contain any sub-cmds.
        Like :meth:`initialize()`, if undefined, replaced with ``sys.argv[1:]``.
    :return:
        The root(1st) cmd to invoke :meth:`Aplication.start()`
        and possibly apply the :func:`pump_cmd()` on its results.

    - Normally `argv` contain any sub-commands, and it is enough to invoke
      ``initialize(argv)`` on the root cmd.  This function shortcuts
      arg-parsing for subcmds with explict cmd-chaining in code.
    - This functions is the 1st half of :meth:`Cmd.launch_instance()`.
    """
    if not app_classes:
        raise ValueError("No cmds to chained passed in!")

    app_classes = list(app_classes)
    root = app = None
    for app_cl in app_classes:
        if type(app_cl).__name__ != 'Application':
                    raise ValueError("Expected an Application-class instance, got %r!" % app_cl)
        if not root:
            ## The 1st cmd is always orphan, and gets returned.
            root = app = app_cl(**root_kwds)
        else:
            app.subapp = app = app_cl(parent=app)
        app.initialize(argv)

    app_classes[0]._instance = app

    return root


class ConsumerBase:
    """Checks if all boolean items (if any) are True, to decide final bool state."""
    any_none_bool = False
    all_true = True

    def __call__(self, item):
        if isinstance(item, bool):
            self.all_true &= item
        else:
            self.any_none_bool = True
        self._emit(item)

    def __bool__(self):
        """
        :return:
            True if all ok, False if any boolean items was false.
        """
        return self.any_none_bool or self.all_true


class PrintConsumer(ConsumerBase):
    """Prints any text-items while checking if all boolean ok."""
    def _emit(self, item):
        if not isinstance(item, bool):
            print(item)


class ListConsumer(ConsumerBase):
    """Collect all items in a list, while checking if all boolean ok."""
    def __init__(self):
        self.items = []

    def _emit(self, item):
        self.items.append(item)


def pump_cmd(cmd_res, consumer=None):
    """
    Sends (possibly lazy) cmd-results to a consumer (by default to STDOUT).

    :param cmd_res:
        Whatever is returnened by a :meth:`Cmd.start()`/`Cmd.run()`.
    :param consumer:
        A callable consuming items and deciding if everything was ok;
        defaults to :class:`PrintConsumer`
    :return:
        ``bool(consumer)``

    - Remember to have logging setup properly before invoking this.
    - This the 2nd half of the replacement for :meth:`Application.launch_instance()`.
    """
    import types

    if not consumer:
        consumer = PrintConsumer()

    if cmd_res is not None:
        if isinstance(cmd_res, types.GeneratorType):
            for i in cmd_res:
                consumer(i)
        elif isinstance(cmd_res, (tuple, list)):
            for i in cmd_res:
                consumer(i)
        else:
            consumer(cmd_res)

    ## NOTE: Enable this code to update `/logconf.yaml`.
    #print('\n'.join(sorted(logging.Logger.manager.loggerDict)))

    return bool(consumer)


def collect_cmd(cmd_res, dont_coalesce=False, assert_ok=False):
    """
    Pumps cmd-result in a new list.

    :param cmd_res:
        A list of items returned by a :meth:`Cmd.start()`/`Cmd.run()`.
        If it is a sole item, it is returned alone without a list.
    :param assert_ok:
        if true, checks :class:`ListConsumer`'s exit-code is not false.
    """
    cons = ListConsumer()
    pump_cmd(cmd_res, cons)
    items = cons.items

    assert not assert_ok or bool(cons), items

    if dont_coalesce:
        return items

    if items:
        if len(items) == 1:
            items = items[0]

        return items


def make_cmd(app, argv=None, **kwargs):
    """
    Instanciate, initialize and return application.

    :param argv:
        Like :meth:`initialize()`, if undefined, replaced with ``sys.argv[1:]``.

    - Tip: Apply :func:`pump_cmd()` on return values to process
      generators of :meth:`run()`.
    - This functions is the 1st half of :meth:`launch_instance()` which
      invokes and discards :meth:`start()` results.
    """
    ## Overriden just to return `start()`.
    cmd = app.instance(**kwargs)
    cmd.initialize(argv)

    return cmd
