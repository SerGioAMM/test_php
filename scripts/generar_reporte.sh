#!/usr/bin/env bash
set -euo pipefail

INPUT_HTML="${1:-report_nessus.html}"
OUTPUT_PDF="${2:-report_scan.pdf}"

if ! command -v pandoc >/dev/null 2>&1; then
    echo "pandoc no está instalado. Intalarlo o instala un agente Jenkins que lo tenga."
    exit 1
fi

echo "[*] Convertiendo ${INPUT_HTML} -> ${OUTPUT_PDF}"
pandoc "${INPUT_HTML}" -o "${OUTPUT_PDF}" || {
    echo "pandoc falló, intentando wkhtmltopdf (si está disponible)"
    if command -v wkhtmltopdf >/dev/null 2>&1; then
        wkhtmltopdf "${INPUT_HTML}" "${OUTPUT_PDF}"
    else
    echo "No hay método alternativo para generar PDF."
    exit 1
    fi
}
echo "[+] PDF generado: ${OUTPUT_PDF}"
