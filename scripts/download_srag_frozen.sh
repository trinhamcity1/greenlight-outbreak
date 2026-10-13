#!/usr/bin/env bash
# Frozen final test data (docs/frozen_test_plan.md): SIVEP-Gripe SRAG 2023-2025, same dataset and release as the
# development files ("srag-2019-a-2026", CC-BY, https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026).
# Kept in their own folder so the development library is never rebuilt with them.
set -euo pipefail
RELEASE="${RELEASE:-23-03-2026}"
YEARS="${YEARS:-23 24 25}"
BASE=https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG
OUT="$(dirname "$0")/../data/raw/srag_frozen"
mkdir -p "$OUT"
for yy in $YEARS; do
  f="INFLUD${yy}-${RELEASE}.parquet"
  [ -s "$OUT/$f" ] || curl -fSL --retry 4 --retry-delay 2 -o "$OUT/$f" "$BASE/20${yy}/$f"
done
(cd "$OUT" && sha256sum *.parquet > SHA256SUMS && cat SHA256SUMS)
