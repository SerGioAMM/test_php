#!/usr/bin/env bash
# scripts/scan_nessus_html_then_pandoc.sh
set -euo pipefail

: "${NESSUS_HOST:=https://127.0.0.1:8834}"
: "${NESSUS_ACCESS_KEY:?set NESSUS_ACCESS_KEY}"
: "${NESSUS_SECRET_KEY:?set NESSUS_SECRET_KEY}"
: "${POLICY_ID:=32}"
: "${TARGET:=192.168.100.129}"
: "${OUT_HTML:=nessus-report.html}"
: "${OUT_PDF:=nessus-report-pandoc.pdf}"
: "${SCAN_NAME:=API-Jenkins-HTML-Scan}"

AUTH_HEADER=(-H "X-ApiKeys: accessKey=${NESSUS_ACCESS_KEY}; secretKey=${NESSUS_SECRET_KEY}" -H "Content-Type: application/json" -k)

echo "[*] Creating scan..."
CREATE_RESP=$(curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans" -d \
  "{\"uuid\":\"scan\",\"settings\":{\"name\":\"${SCAN_NAME}\",\"policy_id\":${POLICY_ID},\"text_targets\":\"${TARGET}\"}}")

SCAN_ID=$(echo "$CREATE_RESP" | jq -r '.scan.id // empty')
if [ -z "$SCAN_ID" ]; then
  echo "ERROR: no se pudo crear el scan"
  echo "$CREATE_RESP" | jq '.' || true
  exit 2
fi
echo "[+] Scan ID: $SCAN_ID"

echo "[*] Launching..."
curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans/${SCAN_ID}/launch" >/dev/null

echo "[*] Waiting for completion..."
while true; do
  STATUS=$(curl -s "${AUTH_HEADER[@]}" "${NESSUS_HOST}/scans/${SCAN_ID}" | jq -r '.info.status // .info.state // empty')
  echo "   → status: $STATUS"
  [[ "$STATUS" == "completed" ]] && break
  sleep 8
done

echo "[*] Requesting export (HTML)..."
TOKEN=$(curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans/${SCAN_ID}/export" -d '{"format":"html"}' | jq -r '.token // empty')
if [ -z "$TOKEN" ]; then
  echo "ERROR: no se obtuvo token de exportación"
  exit 3
fi

echo "[*] Waiting for export ready..."
while true; do
  EXP_STATUS=$(curl -s "${AUTH_HEADER[@]}" "${NESSUS_HOST}/scans/${SCAN_ID}/export/${TOKEN}/status" | jq -r '.status // empty')
  echo "   → export status: $EXP_STATUS"
  [[ "$EXP_STATUS" == "ready" ]] && break
  sleep 4
done

echo "[*] Downloading HTML..."
curl -s "${AUTH_HEADER[@]}" -o "${OUT_HTML}" "${NESSUS_HOST}/scans/${SCAN_ID}/export/${TOKEN}/download"

if [ ! -s "${OUT_HTML}" ]; then
  echo "ERROR: ${OUT_HTML} no generado o vacío"
  exit 4
fi

# Convertir a PDF usando pandoc o wkhtmltopdf
echo "[*] Convirtiendo ${OUT_HTML} -> ${OUT_PDF}"
if command -v wkhtmltopdf >/dev/null 2>&1; then
  wkhtmltopdf "${OUT_HTML}" "${OUT_PDF}"
else
  pandoc "${OUT_HTML}" -o "${OUT_PDF}"
fi

if [ ! -s "${OUT_PDF}" ]; then
  echo "ERROR: ${OUT_PDF} no generado"
  exit 5
fi

echo "[✅] PDF generado via pandoc: ${OUT_PDF}"
