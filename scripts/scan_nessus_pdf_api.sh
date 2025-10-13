#!/usr/bin/env bash
# scripts/scan_nessus_pdf_api.sh
set -euo pipefail

# Configurables (mejor pasarlas como env vars)
: "${NESSUS_HOST:=https://127.0.0.1:8834}"
: "${NESSUS_ACCESS_KEY:?set NESSUS_ACCESS_KEY}"
: "${NESSUS_SECRET_KEY:?set NESSUS_SECRET_KEY}"
: "${POLICY_ID:=32}"
: "${TARGET:=192.168.100.129}"
: "${OUTFILE:=nessus-report.pdf}"
: "${SCAN_NAME:=API-Jenkins-PDF-Scan}"

AUTH_HEADER=(-H "X-ApiKeys: accessKey=${NESSUS_ACCESS_KEY}; secretKey=${NESSUS_SECRET_KEY}" -H "Content-Type: application/json" -k)

echo "[*] Creating scan (policy_id=${POLICY_ID}, target=${TARGET})..."
CREATE_RESP=$(curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans" -d \
  "{\"uuid\":\"scan\",\"settings\":{\"name\":\"${SCAN_NAME}\",\"policy_id\":${POLICY_ID},\"text_targets\":\"${TARGET}\"}}")

SCAN_ID=$(echo "$CREATE_RESP" | jq -r '.scan.id // empty')
if [ -z "$SCAN_ID" ]; then
  echo "ERROR: no se pudo crear el scan. Respuesta:"
  echo "$CREATE_RESP" | jq '.' || true
  exit 2
fi
echo "[+] Scan created: id=${SCAN_ID}"

echo "[*] Launching scan..."
curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans/${SCAN_ID}/launch" >/dev/null

echo "[*] Waiting for completion..."
while true; do
  STATUS=$(curl -s "${AUTH_HEADER[@]}" "${NESSUS_HOST}/scans/${SCAN_ID}" | jq -r '.info.status // .info.state // empty')
  echo "   → status: $STATUS"
  [[ "$STATUS" == "completed" ]] && break
  sleep 8
done

echo "[*] Requesting export (PDF)..."
TOKEN=$(curl -s "${AUTH_HEADER[@]}" -X POST "${NESSUS_HOST}/scans/${SCAN_ID}/export" -d '{"format":"pdf"}' | jq -r '.token // empty')
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

echo "[*] Downloading PDF to ${OUTFILE}..."
curl -s "${AUTH_HEADER[@]}" -o "${OUTFILE}" "${NESSUS_HOST}/scans/${SCAN_ID}/export/${TOKEN}/download"

if [ ! -s "${OUTFILE}" ]; then
  echo "ERROR: ${OUTFILE} no generado o vacío"
  exit 4
fi

echo "[✅] PDF generado: ${OUTFILE}"
