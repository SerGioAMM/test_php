#!/usr/bin/env python3
"""
check_vulnerabilities.py report_summary.json

Lee report_summary.json y devuelve:
 - exit 0 si no hay vulnerabilidades bloqueantes
 - exit 1 si hay >=1 vulnerabilidad en severidad bloqueante (critical/major)
Por defecto también trata "high" como bloqueante (ajústalo si prefieres).
"""
import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Uso: check_vulnerabilities.py <report_summary.json>")
        return 2

    path = sys.argv[1]
    try:
        js = json.load(open(path, 'r'))
    except Exception as e:
        print("ERROR leyendo summary:", e)
        return 2

    # severidades que consideramos bloqueantes
    blocking = ['critical', 'major', 'high']
    total_blocking = 0
    for sev in blocking:
        total_blocking += int(js.get(sev, 0))

    print("Resumen de severidades encontrado:", js)
    if total_blocking > 0:
        print(f"Vulnerabilidades bloqueantes detectadas: {total_blocking} (severidades: {blocking})")
        return 1

    print("No se han detectado vulnerabilidades bloqueantes. OK para desplegar.")
    return 0

if __name__ == '__main__':
    sys.exit(main())