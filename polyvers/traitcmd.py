#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 European Commission (JRC);
# Licensed under the EUPL 1.2+ (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl
#
"""Utils for building elaborate Commands/Sub-commands with traitlets Application."""

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
