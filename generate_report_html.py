#!/usr/bin/env python3
"""
generate_report_html.py
Genera reporte HTML desde SonarQube API y escribe report_summary.json con conteos por severidad.

Uso:
  python3 generate_report_html.py --sonar-url http://192.168.100.236:9000 --project-key test_php --token <TOKEN> --output report.html --template report_template_v2.html
"""
import argparse
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import sys
import json

def get_measures(sonar_url, project_key, token):
    metric_keys = ",".join([
        "coverage", "bugs", "code_smells", "vulnerabilities",
        "duplicated_lines_density", "ncloc", "sqale_index"
    ])
    url = f"{sonar_url.rstrip('/')}/api/measures/component"
    params = {"component": project_key, "metricKeys": metric_keys}
    r = requests.get(url, params=params, auth=(token, ''))
    r.raise_for_status()
    data = r.json()
    measures = {m['metric']: m.get('value') for m in data.get('component', {}).get('measures', [])}
    return measures

def get_issues(sonar_url, project_key, token, max_pages=5, page_size=200):
    url = f"{sonar_url.rstrip('/')}/api/issues/search"
    issues = []
    page = 1
    while page <= max_pages:
        params = {"componentKeys": project_key, "ps": page_size, "p": page, "resolved": "false"}
        r = requests.get(url, params=params, auth=(token, ''))
        r.raise_for_status()
        data = r.json()
        batch = data.get('issues', [])
        if not batch:
            break
        issues.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return issues

def get_analyses(sonar_url, project_key, token, limit=10):
    url = f"{sonar_url.rstrip('/')}/api/project_analyses/search"
    params = {"project": project_key, "ps": limit}
    r = requests.get(url, params=params, auth=(token, ''))
    r.raise_for_status()
    data = r.json()
    return data.get('analyses', [])

def render_html(context, template_file, output_file):
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_file) or "."),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tpl = env.get_template(os.path.basename(template_file))
    html = tpl.render(context)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

# ----------------- summary writer -----------------
def _normalize_severity(s):
    if s is None:
        return 'info'
    s = str(s).strip().lower()
    # Sonar severities: BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    if s in ('blocker', 'critical', 'crit'):
        return 'critical'
    if s in ('major', 'high'):
        return 'major'
    if s in ('minor', 'medium', 'med'):
        return 'minor'
    if s in ('info', 'informational', 'i'):
        return 'info'
    # fallback by substring
    if 'block' in s or 'crit' in s:
        return 'critical'
    if 'high' in s:
        return 'major'
    if 'major' in s:
        return 'major'
    if 'low' in s or 'min' in s:
        return 'minor'
    return 'info'

def write_summary_from_vulns(vulns, out_path='report_summary.json'):
    """
    vulns: lista de dicts; cada dict debe tener clave 'severity' o similar.
    Escribe conteos por severidad (critical, major, minor, info).
    """
    counts = {}
    for v in vulns or []:
        sev = None
        # Sonar issues include 'severity'
        if isinstance(v, dict):
            for k in ('severity', 'level', 'risk', 'severity_level'):
                if k in v:
                    sev = v[k]
                    break
        normalized = _normalize_severity(sev)
        counts[normalized] = counts.get(normalized, 0) + 1

    # Asegurar claves
    for k in ('critical','major','minor','info'):
        counts.setdefault(k, 0)

    # escribir archivo atomically
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(counts, fh, indent=2)
    os.replace(tmp, out_path)
    print(f"Wrote vulnerability summary to {out_path}: {counts}")

# ----------------- main -----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sonar-url', required=True)
    parser.add_argument('--project-key', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--output', default='report.html')
    parser.add_argument('--template', default='report_template_v2.html')
    parser.add_argument('--max-issue-pages', default=5, type=int)
    args = parser.parse_args()

    if not os.path.exists(args.template):
        print(f"Plantilla {args.template} no encontrada.", file=sys.stderr)
        sys.exit(2)

    try:
        measures = get_measures(args.sonar_url, args.project_key, args.token)
        issues = get_issues(args.sonar_url, args.project_key, args.token, max_pages=args.max_issue_pages)
        analyses = get_analyses(args.sonar_url, args.project_key, args.token)
        context = {
            'project_key': args.project_key,
            'measures': measures,
            'issues': issues,
            'analyses': analyses,
            'sonar_url': args.sonar_url.rstrip('/')
        }
        render_html(context, args.template, args.output)
        print(f"HTML generado: {args.output}")

        # ----- write report_summary.json from Sonar issues -----
        try:
            # issues es la lista de hallazgos de Sonar; la usamos como "vulns"
            print(f"Found {len(issues)} issues; writing report_summary.json ...")
            write_summary_from_vulns(issues, 'report_summary.json')
        except Exception as e:
            print("Warning: fallo escribiendo report_summary.json:", e, file=sys.stderr)
            # garantizar que no quede un archivo vacío: escribir ceros
            try:
                write_summary_from_vulns([], 'report_summary.json')
            except Exception as ee:
                print("ERROR al crear fallback report_summary.json:", ee, file=sys.stderr)
                sys.exit(5)

    except requests.HTTPError as e:
        print("Error HTTP al consultar SonarQube:", e, file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(4)

if __name__ == '__main__':
    main()