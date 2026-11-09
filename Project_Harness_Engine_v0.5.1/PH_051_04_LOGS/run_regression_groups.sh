#!/bin/bash
set -u
cd /mnt/data/ph05104_work/input/Project_Harness_Engine_v0.5.1
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests
n=0
while IFS= read -r mods; do
  n=$((n+1))
  echo "START group $n $(date -u +%H:%M:%S)"
  timeout 160s python -m unittest -v $mods > /mnt/data/ph05104_work/logs/REGRESSION/group_${n}.log 2>&1
  rc=$?
  echo "$n $rc $(tail -4 /mnt/data/ph05104_work/logs/REGRESSION/group_${n}.log | tr '\n' '|')" | tee -a /mnt/data/ph05104_work/logs/REGRESSION/STATUS
  if [ "$rc" -ne 0 ]; then echo "FAIL $n"; fi
done < /mnt/data/ph05104_work/logs/regression_groups.txt
