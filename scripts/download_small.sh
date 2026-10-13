#!/usr/bin/env bash
# Small public line lists for the vote-only test (Exp. 13).
#  - Kenema Ebola 2014: Zenodo record 2614046 (mirador/ebola-data v1.4), licence "other-open".
#  - R package outbreaks 1.9.0 (CRAN, GPL >= 2): fluH7N9_china_2013, mers_korea_2015.
set -euo pipefail
OUT="$(dirname "$0")/../data/raw/small"
mkdir -p "$OUT/ebola" "$OUT/outbreaks_pkg"
[ -s "$OUT/ebola/ebola-data-1.4.zip" ] || curl -fSL --retry 4 -o "$OUT/ebola/ebola-data-1.4.zip" \
  "https://zenodo.org/api/records/2614046/files/mirador/ebola-data-1.4.zip/content"
[ -s "$OUT/outbreaks_pkg/outbreaks_1.9.0.tar.gz" ] || curl -fSL --retry 4 -o "$OUT/outbreaks_pkg/outbreaks_1.9.0.tar.gz" \
  "https://cran.r-project.org/src/contrib/outbreaks_1.9.0.tar.gz"
(cd "$OUT/ebola" && unzip -o -q ebola-data-1.4.zip)
(cd "$OUT/outbreaks_pkg" && tar xzf outbreaks_1.9.0.tar.gz)
(cd "$OUT" && sha256sum ebola/ebola-data-1.4.zip outbreaks_pkg/outbreaks_1.9.0.tar.gz | tee SHA256SUMS)
