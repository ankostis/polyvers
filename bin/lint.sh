#!/bin/bash

my_dir=`dirname "$0"`
cd $my_dir/..

declare -i err=0
set -x

mypy \
    pvcmd/polyvers/vermath.py \
    pvcmd/polyvers/cmdlet/cmdlets.py \
    pvcmd/polyvers/cmdlet/errlog.py \
    pvcmd/polyvers/pvproject.py \
    pvcmd/polyvers/engrave.py \
    pvcmd/polyvers/gitag.py \
    pvcmd/polyvers/cli.py \
    pvcmd/polyvers/bumpcmd.py
let err+=$?

flake8 --show-source
let err+=$?

if [ $err -ne 0 ]; then
    echo "Lint had $err failures!"
    exit 1
fi