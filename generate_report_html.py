#!/usr/bin/env python3
"""
generate_report_html.py
Genera reporte HTML desde SonarQube API.
Uso:
  python3 generate_report_html.py --sonar-url http://192.168.100.236:9000 --project-key test_php --token <TOKEN> --output report.html --template report_template_v2.html
"""
import argparse
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import sys

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
    except requests.HTTPError as e:
        print("Error HTTP al consultar SonarQube:", e, file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(4)

if __name__ == '__main__':
    main()