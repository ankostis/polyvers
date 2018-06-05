#!/bin/bash
#
## SYNTAX:
#       package.sh  [--no-err]
#
#  Build both polyvers(-ion) packages, optionally ingoring lint/bdist-errors.
#

PVLIB_SH="pvlib.run"

my_dir="$(realpath "$(dirname "$0")")"
cd $my_dir/..

## Stop work on dirty repos - need to switch branches.
#  from from https://stackoverflow.com/a/2659808/548792
#
if (git describe --dirty --all|grep dirty >/dev/null); then
    echo "Dirty working directory, packaging aborted." > /dev/stderr
    exit 1;
fi

if [[ "${@#--noerr}" = "$@" ]]; then
    echo "+++Not aborting on errors."
else
    enable_err="set -eE"
fi

build_wheels() {
    ./bin/check_readme.sh

    rm -rf build/* dist/*
    python setup.py bdist_wheel

    rm -rf build/*  pvlib/build/*
    python pvlib/setup.py bdist_wheel
}

## Conditionally CLEANLY fail on errors.
#
checkout_prev() {
    echo "^^^Abort, resoring branch...."
    git checkout -
    exit -1
}

trap checkout_prev EXIT
$enable_err

git checkout latest

./bin/lint.sh
build_wheels

git checkout -
trap '' EXIT


## Create executable AND importable wheel::
#      ./pvlib.run --help                           # from bash
#      python ./pvlib.run --help                    # outer __main__.py
#      python ./pvlib.run -m polyversion  --help    # inner __main__.py
#
cd ./dist
tmpzip=_pvlib.zip
cp polyversion*.whl $tmpzip
## Leave both __main__.py files, one for -m,
#  and the other for executing as scrpt.
#zip -d $tmpzip polyversion/__main__.py
zip -j $tmpzip ../pvlib/polyversion/__main__.py
echo -ne '#!/usr/bin/env python\n' | cat - $tmpzip > "$PVLIB_SH"
chmod a+x "$PVLIB_SH"

## Nice chance to send tags.
git push jrcstu latest --tag -f  # latest always forced.
