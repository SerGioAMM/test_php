#!/usr/bin/env python3
"""
generate_report_html.py
Genera reporte HTML desde SonarQube API y escribe report_summary.json con conteos por severidad
y report_hotspots.json con resumen de Security Hotspots.

Uso:
  python3 generate_report_html.py --sonar-url http://192.168.100.236:9000 --project-key test_php --token <TOKEN> --output report.html --template report_template_v2.html
"""
import argparse
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import sys
import json
import time

# ---------------- Sonar API helpers ----------------
def _get_json(url, params, token):
    try:
        r = requests.get(url, params=params, auth=(token, ''))
        r.raise_for_status()
        return r.json()
    except requests.HTTPError:
        # re-raise to allow caller to handle/report
        raise
    except Exception as e:
        # wrap to provide context
        raise RuntimeError(f"Error requesting {url} : {e}")

def get_measures(sonar_url, project_key, token):
    metric_keys = ",".join([
        "coverage", "bugs", "code_smells", "vulnerabilities",
        "duplicated_lines_density", "ncloc", "sqale_index"
    ])
    url = f"{sonar_url.rstrip('/')}/api/measures/component"
    params = {"component": project_key, "metricKeys": metric_keys}
    data = _get_json(url, params, token)
    measures = {m['metric']: m.get('value') for m in data.get('component', {}).get('measures', [])}
    return measures

def get_issues(sonar_url, project_key, token, max_pages=5, page_size=200):
    url = f"{sonar_url.rstrip('/')}/api/issues/search"
    issues = []
    page = 1
    while page <= max_pages:
        params = {"componentKeys": project_key, "ps": page_size, "p": page, "resolved": "false"}
        data = _get_json(url, params, token)
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
    data = _get_json(url, params, token)
    return data.get('analyses', [])

# ---------------- Security Hotspots ----------------
def _try_hotspots_api(sonar_url, project_key, token, max_pages=5, page_size=200):
    """
    Intento principal: /api/hotspots/search
    Algunos Sonar usan 'projectKey', otros 'component' o 'componentKeys' - pruebo variantes.
    """
    candidates = [
        (f"{sonar_url.rstrip('/')}/api/hotspots/search", {"projectKey": project_key}),
        (f"{sonar_url.rstrip('/')}/api/hotspots/search", {"component": project_key}),
        (f"{sonar_url.rstrip('/')}/api/hotspots/search", {"componentKeys": project_key}),
    ]
    hotspots = []
    for base_url, base_params in candidates:
        try:
            page = 1
            while page <= max_pages:
                params = dict(base_params)
                params.update({"ps": page_size, "p": page})
                data = _get_json(base_url, params, token)
                # respuesta típica: { "hotspots": [...], "paging": {...} }
                batch = data.get('hotspots') or data.get('hotspot') or data.get('hotSpots') or []
                if not batch:
                    break
                hotspots.extend(batch)
                if len(batch) < page_size:
                    break
                page += 1
            if hotspots:
                return hotspots
        except requests.HTTPError:
            # intentar la siguiente variante
            continue
        except Exception:
            continue
    return []

def _try_issues_fallback(sonar_url, project_key, token, max_pages=5, page_size=200):
    """
    Fallback: consultar /api/issues/search pidiendo tipos de hotspot (si la instalación expone hotspots por issues).
    Probamos 'types=SECURITY_HOTSPOT' y 'types=SECURITY_HOTSPOTS'.
    """
    url = f"{sonar_url.rstrip('/')}/api/issues/search"
    hotspots = []
    page = 1
    tried_types = ["SECURITY_HOTSPOT", "SECURITY_HOTSPOTS", "SECURITY_HOTSPOT, VULNERABILITY"]
    for t in tried_types:
        page = 1
        collected = []
        try:
            while page <= max_pages:
                params = {"componentKeys": project_key, "ps": page_size, "p": page, "types": t, "resolved": "false"}
                data = _get_json(url, params, token)
                batch = data.get('issues', [])
                if not batch:
                    break
                # marcar que esto vino de issues API (normalize)
                for b in batch:
                    b['_from_issues_api'] = True
                collected.extend(batch)
                if len(batch) < page_size:
                    break
                page += 1
            if collected:
                hotspots.extend(collected)
                return hotspots
        except requests.HTTPError:
            continue
        except Exception:
            continue
    return []

def get_hotspots(sonar_url, project_key, token, max_pages=5, page_size=200):
    """
    Devuelve una lista de hotspots normalizados (cada item es dict con keys: rule, message, component, line, status, link)
    """
    raw = _try_hotspots_api(sonar_url, project_key, token, max_pages=max_pages, page_size=page_size)
    if not raw:
        raw = _try_issues_fallback(sonar_url, project_key, token, max_pages=max_pages, page_size=page_size)
    normalized = []
    for h in raw:
        # extraer campos de forma defensiva
        rule = h.get('rule') or h.get('ruleKey') or h.get('securityCategory') or h.get('type') or h.get('subType') or ''
        message = h.get('message') or h.get('text') or h.get('excerpt') or h.get('description') or ''
        component = h.get('component') or h.get('filePath') or h.get('resource') or ''
        # intentar obtener línea
        line = None
        if 'line' in h and h['line'] is not None:
            line = h['line']
        else:
            tr = h.get('textRange') or h.get('range') or {}
            if isinstance(tr, dict):
                line = tr.get('startLine') or tr.get('line') or None
        # estado/review
        status = h.get('status') or h.get('state') or h.get('reviewStatus') or h.get('securityHotspotStatus') or ''
        # Normalizar estado a etiquetas entendibles
        s_norm = ''
        if isinstance(status, str):
            st = status.strip().lower()
            if 'review' in st or 'to_review' in st or st in ('to_review','todo','open'):
                s_norm = 'TO_REVIEW'
            elif 'safe' in st or st in ('safe','resolved'):
                s_norm = 'SAFE'
            elif 'reviewed' in st:
                s_norm = 'REVIEWED'
            else:
                s_norm = status
        else:
            s_norm = status
        # enlace a la vista de hotspots en Sonar para el proyecto (no al hotspot específico porque la URL exacta puede variar por versión)
        link = f"{sonar_url.rstrip('/')}/project/security_hotspots?id={project_key}"
        normalized.append({
            'rule': rule,
            'message': message,
            'component': component,
            'line': line,
            'status': s_norm,
            'link': link,
            # conservar raw por si la plantilla quiere más info
            '_raw': h
        })
    return normalized

# ----------------- summary writer (extendido) -----------------
def _normalize_severity(s):
    if s is None:
        return 'info'
    s = str(s).strip().lower()
    if s in ('blocker', 'critical', 'crit'):
        return 'critical'
    if s in ('major', 'high'):
        return 'major'
    if s in ('minor', 'medium', 'med'):
        return 'minor'
    if s in ('info', 'informational', 'i'):
        return 'info'
    if 'block' in s or 'crit' in s:
        return 'critical'
    if 'high' in s or 'major' in s:
        return 'major'
    if 'low' in s or 'min' in s:
        return 'minor'
    return 'info'

def write_summary_all(vulns, hotspots, out_path='report_summary.json'):
    """
    Escribe un JSON que incluye:
      - severities: counts by critical/major/minor/info (from vulns list)
      - hotspots: counts by status (TO_REVIEW, REVIEWED, SAFE, total)
    """
    severities = {}
    for v in vulns or []:
        sev = None
        if isinstance(v, dict):
            for k in ('severity','level','risk','severity_level'):
                if k in v:
                    sev = v[k]
                    break
        normalized = _normalize_severity(sev)
        severities[normalized] = severities.get(normalized, 0) + 1
    for k in ('critical','major','minor','info'):
        severities.setdefault(k, 0)

    hotspot_counts = {'TO_REVIEW': 0, 'REVIEWED': 0, 'SAFE': 0, 'OTHER': 0, 'TOTAL': 0}
    for h in hotspots or []:
        s = h.get('status') if isinstance(h, dict) else None
        if not s:
            hotspot_counts['OTHER'] += 1
        else:
            key = str(s).upper()
            if key in hotspot_counts:
                hotspot_counts[key] += 1
            else:
                hotspot_counts['OTHER'] += 1
        hotspot_counts['TOTAL'] += 1

    out = {
        'severities': severities,
        'hotspots': hotspot_counts,
        'generated_at': int(time.time())
    }
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2)
    os.replace(tmp, out_path)
    print(f"Wrote combined summary to {out_path}: severities={severities}, hotspots={hotspot_counts}")

# ----------------- HTML rendering -----------------
def render_html(context, template_file, output_file):
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_file) or "."),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tpl = env.get_template(os.path.basename(template_file))
    html = tpl.render(context)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

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
        hotspots = get_hotspots(args.sonar_url, args.project_key, args.token, max_pages=args.max_issue_pages)

        context = {
            'project_key': args.project_key,
            'measures': measures,
            'issues': issues,
            'analyses': analyses,
            'hotspots': hotspots,
            'sonar_url': args.sonar_url.rstrip('/')
        }

        render_html(context, args.template, args.output)
        print(f"HTML generado: {args.output}")

        # escribir resumen combinado (severities + hotspots)
        try:
            print(f"Found {len(issues)} issues and {len(hotspots)} hotspots; writing report_summary.json ...")
            write_summary_all(issues, hotspots, 'report_summary.json')
            # además, escribir un JSON con la lista de hotspots detallada
            try:
                with open('report_hotspots.json.tmp', 'w', encoding='utf-8') as fh:
                    json.dump(hotspots, fh, indent=2)
                os.replace('report_hotspots.json.tmp', 'report_hotspots.json')
                print("Wrote report_hotspots.json")
            except Exception as e:
                print("Warning: fallo escribiendo report_hotspots.json:", e, file=sys.stderr)
        except Exception as e:
            print("Warning: fallo escribiendo report_summary.json:", e, file=sys.stderr)
            try:
                write_summary_all([], [], 'report_summary.json')
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