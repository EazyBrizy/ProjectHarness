#!/bin/bash
set -u
cd /mnt/data/ph05104_work/input/Project_Harness_Engine_v0.5.1
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests
set -- $(sed -n '2p' /mnt/data/ph05104_work/logs/regression_groups.txt)
timeout 480s python -m unittest -v "$@" > /mnt/data/ph05104_work/logs/REGRESSION/group_2_LONG.log 2>&1
rc=$?
printf 'GROUP_2_LONG rc=%s %s\n' "$rc" "$(tail -5 /mnt/data/ph05104_work/logs/REGRESSION/group_2_LONG.log| tr '\n' '|')" > /mnt/data/ph05104_work/logs/REGRESSION/group_2_LONG.STATUS
