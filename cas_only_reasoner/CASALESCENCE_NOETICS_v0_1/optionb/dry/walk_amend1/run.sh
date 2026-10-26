#!/bin/bash
# [MADE-UP DATA WALK] run one tool copy in the scratch project, through guard_run.py; keep what it printed
# usage: ./run.sh <log name> <tool file> [tool arguments...]
W="C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/dry/walk_amend1"
P="${WALK_PROJECT:-project}"
name="$1"; tool="$2"; shift 2
cd "$W/$P" || exit 9
echo "\$ python -B tools/$tool $*" > "$W/logs/$name.txt"
/c/Python314/python.exe -B "$W/guard_run.py" "tools/$tool" "$@" >> "$W/logs/$name.txt" 2>&1
code=$?
echo "[exit code $code]" >> "$W/logs/$name.txt"
echo "== $name: python -B tools/$tool $* -> exit $code"
exit $code
