#!/usr/bin/env python3
"""widget_data.py <session> [--events N] [--buckets B]
Prints a small JSON (a few KB) for the host's inline visuals (show_widget, mcp__easel__chart).
Time is idle-compressed: gaps over 30s count as 30s. Fields: agents, families, events [v,fam,agent,err,dur], buckets [{label,calls,errors,out_k}], brief."""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(__file__))
from parse_trace import build, resolve
from adset_report import report
FAM = ['Shell', 'Files', 'Search', 'Agents', 'Browser', 'MCP', 'Other']
RX = [r'^Bash|Monitor|terminal', r'^(Read|Edit|Write|Notebook)', r'^(Grep|Glob|ToolSearch|Web)', r'^(Agent|Task|Send|mcp__ccd_session)', r'chrome|browser', r'^mcp__', r'.']
fam = lambda n: next(i for i, r in enumerate(RX) if re.search(r, n, re.I))
a = sys.argv[1:]; ne = int(a[a.index('--events') + 1]) if '--events' in a else 60; nb = int(a[a.index('--buckets') + 1]) if '--buckets' in a else 24
tr = build(resolve(a[0])); calls = tr['calls']
pts = sorted({0, tr['duration'], *[c['t0'] for c in calls]})
virt, v = {pts[0]: 0}, 0
for p, q in zip(pts, pts[1:]): v += min(q - p, 30); virt[q] = v
VEND = max(v, 1); ids = {x['id']: i for i, x in enumerate(tr['agents'])}
ev = [[round(virt[c['t0']], 1), fam(c['name']), ids.get(c['agent'], 0), int(c['err']), round((c['t1'] - c['t0']) if c['t1'] else 0, 1), c['name'].replace('mcp__', '')[:24]] for c in calls]
bk = [dict(label=f'{i}', calls=0, errors=0, out_k=0.0) for i in range(nb)]
for e in ev: b = bk[min(nb - 1, int(e[0] / VEND * nb))]; b['calls'] += 1; b['errors'] += e[3]
def vt(t): return virt[min(pts, key=lambda p: abs(p - t))]
for k in tr['tokens']: bk[min(nb - 1, int(vt(k['t']) / VEND * nb))]['out_k'] += k['out'] / 1000
for b in bk: b['out_k'] = round(b['out_k'], 1)
print(json.dumps(dict(session=tr['session'][:8], calls=len(calls), duration_s=round(tr['duration']), vend=round(VEND), peak_parallel=tr['peak_parallel_calls'],
    agents=[x['label'][:20] for x in tr['agents']], families=FAM, events=ev[-ne:], buckets=bk, brief=report(tr, 2)), separators=(',', ':')))
