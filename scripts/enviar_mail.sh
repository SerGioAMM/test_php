#!/usr/bin/env bash
set -euo pipefail

TO="${1:-equipo@empresa.com}"
SUBJECT="${2:-Reporte de escaneo}"
BODY="${3:-Adjunto reporte.}"
ATTACH="${4:-report_scan.pdf}"

if command -v mail >/dev/null 2>&1; then
    echo "${BODY}" | mail -s "${SUBJECT}" -a "${ATTACH}" "${TO}"
    echo "[+] Correo enviado a ${TO}"
else
    echo "Comando mail no disponible en este agente. Usa el plugin de Jenkins para enviar correo."
    exit 1
fi
