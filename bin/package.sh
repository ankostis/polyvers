#!/bin/bash
#
## Build both polyvers packages

my_dir=`dirname "$0"`
cd $my_dir/..

## Stop work on dirty repos - need to switch branches.
#  from from https://stackoverflow.com/a/2659808/548792
#
if (git describe --dirty --all|grep dirty >/dev/null); then
    echo "Dirty working directory, packaging aborted." > /dev/stderr
    exit 1;
fi


git checkout latest

rm -rf build/* dist/*
python setup.py bdist_wheel

rm -rf build/* pvlib/build/*
python pvlib/setup.py bdist_wheel
echo -ne '#!python\n' | cat - polyversion*.whl > pvlib.sh

git checkout -
