.. highlight:: shell

============
Contributing
============

Contributions and issue-reports are welcome, with no strings attached;
project is at a very early stage.

Installation
============
Install both sub-projects in *develop* mode using ``pip``
(installing *egg*  with ``python setup.py install develop`` may not work):

.. code-block:: console

    $ git clone  https://github.com/JRCSTU/polyvers  polyvers.git
    $ cd polyvers.git
    $ pip install  -e pvlib[test]  -e .[test]


Tests & integrations
====================
:test-suite:            `pytest <https://pytest.org/>`_
:linters:               `flake8 <https://gitlab.com/pycqa/flake8>`_,
                        `mypy <http://mypy-lang.org/>`_
:integration-services:  - `travis <https://travis-ci.org/>`_ (CI: linux),
                        - `appveyor <https://appveyor.io/>`_ (CI: Windows),
                        - `coveralls.io <https://coveralls.io/>`_ (coverage),
                        - `codacy.com <https://codacy.io/>`_ (code-quality)
                        - `pyup.io <https://pyup.io>`_ (dependency-tracking)
:commit-messages:       guidelines from *angular* repo:
                        https://github.com/angular/angular.js/blob/master/DEVELOPERS.md#-git-commit-guidelines
