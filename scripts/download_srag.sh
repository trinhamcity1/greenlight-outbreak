#!/usr/bin/env bash
# Download official SIVEP-Gripe SRAG files from the Brazilian Ministry of Health
# open-data portal (dataset "srag-2019-a-2026", license CC-BY).
# Source page: https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026
# Files are versioned by release date in the filename; pin the release here.
set -euo pipefail
RELEASE="${RELEASE:-23-03-2026}"
YEARS="${YEARS:-19 20 21 22}"
BASE=https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG
OUT="$(dirname "$0")/../data/raw/srag"
mkdir -p "$OUT"
for yy in $YEARS; do
  f="INFLUD${yy}-${RELEASE}.parquet"
  [ -s "$OUT/$f" ] || curl -fSL --retry 4 --retry-delay 2 -o "$OUT/$f" "$BASE/20${yy}/$f"
done
[ -s "$OUT/dicionario-de-dados-2019-a-2025.pdf" ] || \
  curl -fSL --retry 4 -o "$OUT/dicionario-de-dados-2019-a-2025.pdf" "$BASE/dicionario-de-dados-2019-a-2025.pdf"
(cd "$OUT" && sha256sum *.parquet *.pdf > SHA256SUMS && cat SHA256SUMS)
