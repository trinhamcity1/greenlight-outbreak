#!/usr/bin/env bash
# Historic SIVEP-Gripe SRAG files (2009-2018), Ministério da Saúde open-data portal, license CC-BY.
# Source pages: https://dadosabertos.saude.gov.br/dataset/srag-2009-2012
#               https://dadosabertos.saude.gov.br/dataset/srag-2013-2018
# These files are not versioned in their names; SHA256SUMS records what was downloaded.
set -euo pipefail
CF=https://d26692udehoye.cloudfront.net/SRAG
S3=https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG
OUT="$(dirname "$0")/../data/raw/srag_historic"
mkdir -p "$OUT"
get() { [ -s "$OUT/$2" ] || curl -fSL --retry 4 --retry-delay 2 -o "$OUT/$2" "$1"; }
for yy in 09 10 11 12; do get "$CF/2009-2012/INFLUD$yy.csv" "INFLUD$yy.csv"; done
for yy in 13 14 15 16 17 18; do get "$CF/2013-2018/INFLUD$yy.csv" "INFLUD$yy.csv"; done
get "$CF/2009-2012/dicionario_de_dados_influenza_pandemica_antigo.pdf" dic_2009_pandemica.pdf
get "$S3/2009-2012/DIC_DADOS_SRAG_2012.pdf" dic_2012.pdf
get "$CF/2013-2018/dicionario_de_dados_SRAG.pdf" dic_2013_2018.pdf
(cd "$OUT" && sha256sum *.csv *.pdf > SHA256SUMS && cat SHA256SUMS)
