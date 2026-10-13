#!/usr/bin/env bash
# Brazil ESAVI: reports of adverse events following vaccination (Ministério da Saúde, CGFAM/DPNI), CC-BY.
# Source page: https://dadosabertos.saude.gov.br/dataset/esavi . The file is a live snapshot; SHA256SUMS records it.
set -euo pipefail
B=https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/ESAVI
OUT="$(dirname "$0")/../data/raw/esavi"
mkdir -p "$OUT/extracted"
[ -s "$OUT/Esavi_csv.zip" ] || curl -fSL --retry 4 -o "$OUT/Esavi_csv.zip" "$B/Esavi_csv.zip"
[ -s "$OUT/DicionariodeDados.pdf" ] || curl -fSL --retry 4 -o "$OUT/DicionariodeDados.pdf" "$B/DicionariodeDados.pdf"
(cd "$OUT" && sha256sum Esavi_csv.zip DicionariodeDados.pdf | tee SHA256SUMS)
(cd "$OUT/extracted" && unzip -o -q ../Esavi_csv.zip)
