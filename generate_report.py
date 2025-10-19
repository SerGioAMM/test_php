#!/usr/bin/env python3
"""
generate_report.py
Genera un PDF con métricas e issues de SonarQube usando la API.
Uso:
  python3 generate_report.py --sonar-url http://192.168.100.236:9000 --project-key test_php --token <TOKEN> --output report.pdf
"""

import argparse
import requests
import pdfkit
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import sys

def get_measures(sonar_url, project_key, token):
    metric_keys = ",".join([
        "coverage", "bugs", "code_smells", "vulnerabilities", "duplicated_lines_density", "ncloc"
    ])
    url = f"{sonar_url.rstrip('/')}/api/measures/component"
    params = {"component": project_key, "metricKeys": metric_keys}
    r = requests.get(url, params=params, auth=(token, ''))
    r.raise_for_status()
    data = r.json()
    measures = {m['metric']: m.get('value') for m in data.get('component', {}).get('measures', [])}
    return measures

def get_issues(sonar_url, project_key, token, page_size=100):
    url = f"{sonar_url.rstrip('/')}/api/issues/search"
    params = {"componentKeys": project_key, "ps": page_size}
    r = requests.get(url, params=params, auth=(token, ''))
    r.raise_for_status()
    data = r.json()
    return data.get('issues', [])

def get_analyses(sonar_url, project_key, token):
    url = f"{sonar_url.rstrip('/')}/api/project_analyses/search"
    params = {"project": project_key}
    r = requests.get(url, params=params, auth=(token, ''))
    r.raise_for_status()
    data = r.json()
    return data.get('analyses', [])

def render_pdf(context, template_file, output_file):
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_file) or "."),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tpl = env.get_template(os.path.basename(template_file))
    html = tpl.render(context)
    # Configure path to wkhtmltopdf if necessary
    config = pdfkit.configuration()  # If wkhtmltopdf not in PATH, pass path: pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
    options = {
        'enable-local-file-access': None
    }
    pdfkit.from_string(html, output_file, configuration=config, options=options)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sonar-url', required=True)
    parser.add_argument('--project-key', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--output', default='report.pdf')
    parser.add_argument('--template', default='report_template.html')
    args = parser.parse_args()

    try:
        measures = get_measures(args.sonar_url, args.project_key, args.token)
        issues = get_issues(args.sonar_url, args.project_key, args.token, page_size=200)
        analyses = get_analyses(args.sonar_url, args.project_key, args.token)

        context = {
            'project_key': args.project_key,
            'measures': measures,
            'issues': issues[:200],  # limitar a 200 para el PDF
            'analyses': analyses[:10]
        }

        if not os.path.exists(args.template):
            print(f"Error: plantilla {args.template} no encontrada.", file=sys.stderr)
            sys.exit(2)

        render_pdf(context, args.template, args.output)
        print(f"PDF generado: {args.output}")
    except requests.HTTPError as e:
        print("Error HTTP al consultar SonarQube:", e, file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print("Error al generar reporte:", e, file=sys.stderr)
        sys.exit(4)

if __name__ == '__main__':
    main()