#!/bin/bash
#
## Build both polyvers packages

PVLIB_SH="pvlib.run"

my_dir=`dirname "$0"`
cd $my_dir/..

## Stop work on dirty repos - need to switch branches.
#  from from https://stackoverflow.com/a/2659808/548792
#
if (git describe --dirty --all|grep dirty >/dev/null); then
    echo "Dirty working directory, packaging aborted." > /dev/stderr
    exit 1;
fi


set -e
git checkout latest

    rm -rf build/* dist/*
    python setup.py bdist_wheel

    rm -rf build/*  pvlib/build/*
    python pvlib/setup.py bdist_wheel

git checkout -
set +e

cd ./dist
tmpzip=_pvlib.zip
cp polyversion*.whl $tmpzip
zip -d $tmpzip polyversion/__main__.py
zip -j $tmpzip ../pvlib/polyversion/__main__.py
echo -ne '#!python\n' | cat - $tmpzip > "$PVLIB_SH"
chmod a+x "$PVLIB_SH"

## Nice chance to send tags.
if { ./bin/check_readme.sh && ./bin/lint.sh; }; then
    git push jrcstu latest --tag -f  # latest always forced.
fi