#!/usr/bin/env python3
"""build_index.py [-n 12] [--project SUBSTR] [-o index.html]
Builds a viewer for each of the N most recent sessions (any project) and one index page that links them."""
import sys, os, glob, json, argparse, html, datetime
sys.path.insert(0, os.path.dirname(__file__))
from build_viewer import render
ap = argparse.ArgumentParser(); ap.add_argument('-n', type=int, default=12); ap.add_argument('--project', default=''); ap.add_argument('-o'); ap.add_argument('--fragment', action='store_true', help='artifact-ready page: no doctype or head wrapper')
a = ap.parse_args()
out = os.path.expanduser(a.o or '~/agent-trace-out/index.html'); d = os.path.dirname(out); os.makedirs(d, exist_ok=True)
fs = [f for f in glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')) if a.project in f]
fs = sorted(fs, key=os.path.getmtime, reverse=True)[:a.n]
rows = []
for f in fs:
    try:
        o = f'{d}/{os.path.basename(f)[:8]}.html'; tr = render(f, o, False, None)
    except Exception as e:
        print('skip', f, e); continue
    errs = sum(1 for c in tr['calls'] if c['err'])
    rows.append((os.path.getmtime(f), tr['title'], os.path.basename(o), len(tr['calls']), len(tr['agents']) - 1, errs, tr['duration']))
def dur(s): return f'{s/3600:.1f} h' if s > 5400 else f'{s/60:.0f} min'
tr_ = ''.join(f'<a class="card" href="{r[2]}"><b>{html.escape(r[1])}</b><span>{datetime.datetime.fromtimestamp(r[0]):%d %b %H:%M} · {dur(r[6])} · {r[3]} calls · {r[4]} subagent{'' if r[4]==1 else 's'} · {r[5]} failed</span></a>' for r in rows)
STYLE = """<title>Odin Runs</title><meta name="claude:viewport-fit-sides" content="cover"><style>
:root{--bg:#f6f8fa;--panel:#fff;--line:#d0d7de;--fg:#1f2328;--mute:#656d76;--accent:#0969da}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mute:#8b949e;--accent:#58a6ff;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mute:#8b949e;--accent:#58a6ff;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:14px/1.45 Inter,system-ui,sans-serif;max-width:900px;margin:0 auto;padding-block:16px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute)}
.card{display:block;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0;color:inherit;text-decoration:none;min-width:0}
.card:hover,.card:focus-visible{border-color:var(--accent);outline:none}.card b{overflow-wrap:anywhere}.card span{display:block;color:var(--mute);font-size:12px}
</style>"""
body = f'<h1>Odin runs</h1><div class="sub">{len(rows)} most recent agent runs. Open one to replay it.</div>{tr_}'
open(out, 'w').write(STYLE + body if a.fragment else f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{STYLE}</head><body>{body}</body></html>')
print(out, len(rows), 'sessions')
