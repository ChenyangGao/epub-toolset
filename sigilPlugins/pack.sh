#!/usr/bin/env bash
PROJDIR=$(dirname "$0")

for name in ${PROJDIR}/*/pack.sh; do
    bash "$name"
done
