#!/bin/bash
mypy \
    pvcmd/polyvers/vermath.py \
    pvcmd/polyvers/cmdlet/cmdlets.py \
    pvcmd/polyvers/cmdlet/errlog.py \
    pvcmd/polyvers/pvproject.py \
    pvcmd/polyvers/engrave.py \
    pvcmd/polyvers/pvtags.py \
    pvcmd/polyvers/cli.py \
    pvcmd/polyvers/bumpcmd.py
flake8 --show-source

