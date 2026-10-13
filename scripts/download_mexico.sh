#!/usr/bin/env bash
# Mexico, Secretaría de Salud / Dirección General de Epidemiología: open COVID-19 surveillance data (SISVER),
# year-closure files for 2020 and 2021, plus the data dictionary. Terms: "Términos de Libre Uso de Datos Abiertos" of the
# DGE (see https://www.gob.mx/salud/documentos/datos-abiertos-152127). SHA256SUMS records what was downloaded.
set -euo pipefail
B=https://datosabiertos.salud.gob.mx/gobmx/salud/datos_abiertos
OUT="$(dirname "$0")/../data/raw/mexico"
mkdir -p "$OUT"
get() { [ -s "$OUT/$2" ] || curl -fSL --retry 4 --retry-delay 2 -o "$OUT/$2" "$1"; }
get "$B/historicos/2020/COVID19MEXICO2020.zip" COVID19MEXICO2020.zip
get "$B/historicos/2021/COVID19MEXICO2021.zip" COVID19MEXICO2021.zip
get "$B/diccionario_datos_abiertos.zip" diccionario_datos_abiertos.zip
(cd "$OUT" && sha256sum *.zip > SHA256SUMS && cat SHA256SUMS)
