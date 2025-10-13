#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys
import subprocess
import os
from datetime import datetime

if len(sys.argv) != 2:
    print("Uso: python3 nessus_to_pdf.py archivo.nessus")
    sys.exit(1)

nessus_file = sys.argv[1]
if not os.path.exists(nessus_file):
    print(f"Error: {nessus_file} no encontrado.")
    sys.exit(1)

# Parsear XML
tree = ET.parse(nessus_file)
root = tree.getroot()

# Extraer info general
policy = root.find('.//Policy/PolicyName').text if root.find('.//Policy/PolicyName') is not None else "N/A"
scan_start = root.find('.//Report/ReportName').text if root.find('.//Report/ReportName') is not None else "N/A"
targets = [item.text for item in root.findall('.//ReportTarget')] if root.findall('.//ReportTarget') else ["N/A"]

# Generar Markdown
md_content = f"""# Reporte de Escaneo Nessus

**Política:** {policy}  
**Fecha de Inicio:** {scan_start}  
**Targets:** {', '.join(targets)}  
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumen de Vulnerabilidades

"""

severity_counts = {'info': 0, 'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
vulns_by_host = {}

for report_host in root.findall('.//ReportHost'):
    hostname = report_host.get('NAME', 'Unknown')
    vulns_by_host[hostname] = []

    md_content += f"\n### Host: {hostname}\n\n"

    for item in report_host.findall('.//ReportItem'):
        plugin_id = item.get('PLUGIN_ID', 'N/A')
        plugin_name = item.get('PLUGIN_NAME', 'N/A')
        severity = item.get('SEVERITY', '0')
        description = item.find('description')
        desc_text = description.text[:300] + "..." if description is not None and description.text else "Sin descripción."
        solution = item.find('solution')
        sol_text = solution.text if solution is not None and solution.text else "No disponible."

        # Contar severidades (mapeo Nessus: 0=info, 1=low, 2=medium, etc.)
        if severity == '0': severity_counts['info'] += 1
        elif severity == '1': severity_counts['low'] += 1
        elif severity == '2': severity_counts['medium'] += 1
        elif severity == '3': severity_counts['high'] += 1
        elif severity == '4': severity_counts['critical'] += 1

        vulns_by_host[hostname].append({
            'plugin': plugin_name,
            'severity': severity,
            'desc': desc_text,
            'solution': sol_text
        })

        # Agregar a MD solo si severidad >=2 (medium+), para no inflar; quita el if para todo
        if int(severity) >= 2:
            md_content += f"- **Plugin ID: {plugin_id} - {plugin_name}** (Severidad: {severity})  \n  **Descripción:** {desc_text}  \n  **Solución:** {sol_text}  \n\n"

# Agregar resumen al inicio
md_content = f"""# Reporte de Escaneo Nessus

**Política:** {policy}  
**Fecha de Inicio:** {scan_start}  
**Targets:** {', '.join(targets)}  
**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

## Resumen de Severidades
- Info: {severity_counts['info']}
- Low: {severity_counts['low']}
- Medium: {severity_counts['medium']}
- High: {severity_counts['high']}
- Critical: {severity_counts['critical']}

{md_content[2:]}  # Quita el ## duplicado
"""

# Guardar MD
md_file = nessus_file.replace('.nessus', '.md')
with open(md_file, 'w') as f:
    f.write(md_content)

# Convertir a PDF con Pandoc
pdf_file = nessus_file.replace('.nessus', '.pdf')
cmd = [
    'pandoc', md_file, '-o', pdf_file,
    '--pdf-engine=pdflatex',
    '-V', 'geometry:margin=1in',
    '-V', 'mainfont=DejaVuSans',  # Fuente para tablas
    '--toc'  # Tabla de contenidos opcional
]
subprocess.run(cmd, check=True)

print(f"PDF generado: {pdf_file}")
print(f"Markdown intermedio: {md_file}")

    # Limpiar MD si quieres (opcional)
    # os.remove(md_file)