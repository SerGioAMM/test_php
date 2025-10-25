#!/usr/bin/env python3
"""
check_vulnerabilities.py report_summary.json

Salida:
 - Primera línea: "true"  -> OK para desplegar (no hay vulnerabilidades bloqueantes)
                 "false" -> NO ok para desplegar (hay vulnerabilidades bloqueantes)
 - Líneas siguientes: mensaje legible para logs / email.

Exit codes:
 - 0 : ejecución correcta (tanto true como false)
 - 2 : error leyendo/parsing del archivo summary (archivo ausente o corrupto)
"""
import sys
import json
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('summary', help='report_summary.json')
    ap.add_argument('--blocking', '-b', default='critical,major,high',
                    help='Coma-separated severities consideradas bloqueantes (por defecto: critical,major,high)')
    args = ap.parse_args()

    try:
        with open(args.summary, 'r', encoding='utf-8') as fh:
            js = json.load(fh)
    except Exception as e:
        print(f"ERROR leyendo summary: {e}", file=sys.stderr)
        return 2

    blocking = [s.strip().lower() for s in args.blocking.split(',') if s.strip()]
    total_blocking = 0
    details = []
    for sev in blocking:
        try:
            count = int(js.get(sev, 0))
        except Exception:
            count = 0
        total_blocking += count
        details.append(f"{sev}={count}")

    # Primera línea: booleano simple
    if total_blocking > 0:
        # false -> no desplegar
        print("false")
        print("Despliegue abortado: se detectaron vulnerabilidades bloqueantes.")
        print("Detalles:", ", ".join(details))
        print(f"Total bloqueantes: {total_blocking}")
        return 0
    else:
        # true -> ok desplegar
        print("true")
        print("Despliegue autorizado: no se detectaron vulnerabilidades bloqueantes.")
        print("Detalles:", ", ".join(details))
        return 0

if __name__ == '__main__':
    sys.exit(main())