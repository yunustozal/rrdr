#!/usr/bin/env bash
# Five-city study (Chicago, New York, Boston, Minneapolis, Pittsburgh).
# Run from this folder. Chicago inputs come from the main pipeline:
#   rrdr run --config configs/chicago.yaml   (writes ../../outputs/chicago)
set -e
cd "$(dirname "$0")"
for s in scripts/0[1-4]_*.py; do echo "== $s"; python "$s"; done      # downloads (several GB, slow)
for s in scripts/0[5-9]_*.py scripts/1[0-5]_*.py; do echo "== $s"; python "$s"; done
echo "Results: out/harmonized.json, out/nyc_cross.json, out/mpls_pci.json, out/figs/"
