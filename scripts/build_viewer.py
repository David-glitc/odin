#!/usr/bin/env python3
"""build_viewer.py <session.jsonl|id|project-dir> [-o out.html] [--watch] [--since ISO]
Writes a single self-contained HTML (no network): ASD-STE100 brief, animated replay, swimlanes, charts.
--watch rebuilds every 3s and the page auto-reloads (live observability while an agent works)."""
import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(__file__))
from parse_trace import build, resolve
from adset_report import report
tpl = open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'viewer.html')).read()
def to_fragment(h):
    import re
    h = re.sub(r'<!doctype html>\s*<html[^>]*>\s*<head>', '', h, flags=re.I)
    h = re.sub(r'<meta charset[^>]*>|<meta name="viewport"[^>]*>', '', h)
    return h.replace('</head><body>', '').replace('</body></html>', '')

def render(path, out, live, since, fragment=False, title=None):
    tr = build(path, since)
    ps = [p['text'] for p in tr['prompts'] if p['text'] and not p['text'].startswith(('Your response','Background','<','[Request','Linked','Caveat'))]
    proj = os.path.basename(os.path.dirname(path)).replace('-home-david-','').strip('-') or 'project'
    tr['title'] = (ps[0][:70] if ps else 'Agent run') + '  ·  ' + proj
    h = (tpl.replace('/*TRACE*/null', json.dumps(tr, separators=(',', ':')).replace('</', '<\\/'))
            .replace('/*ADSET*/""', json.dumps(report(tr))).replace('/*LIVE*/false', 'true' if live else 'false'))
    if title: h = h.replace('<title>Agent Trace</title>', f'<title>{title}</title>')
    if fragment: h = to_fragment(h)
    open(out + '.tmp', 'w').write(h); os.replace(out + '.tmp', out)
    return tr
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('-o'); ap.add_argument('--watch', action='store_true'); ap.add_argument('--since'); ap.add_argument('--fragment', action='store_true'); ap.add_argument('--title')
    a = ap.parse_args(); p = resolve(a.src); o = a.o or os.path.expanduser(f'~/agent-trace-out/{os.path.basename(p)[:8]}.html')
    os.makedirs(os.path.dirname(o), exist_ok=True)
    while True:
        tr = render(p, o, a.watch, a.since, a.fragment, a.title); print(f'{o}: {len(tr["calls"])} calls, {len(tr["agents"])} agents', flush=True)
        if not a.watch: break
        time.sleep(3)
