#!/bin/bash
#
## Build both polyvers packages

git checkout latest

rm -rf build/* dist/*
python setup.py bdist_wheel

rm -rf build/*
python pvlib/setup.py bdist_wheel

git checkout -
