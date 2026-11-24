#!/usr/bin/env python3
"""Parse a Claude Code session .jsonl (plus subagents/) into one compact trace.json.
Usage: parse_trace.py <session.jsonl | session-id | project-dir> [-o out.json] [--since ISO]
"""
import json, sys, os, glob, argparse, collections, re
from datetime import datetime

def ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp() if s else None

def resolve(arg):
    if os.path.isfile(arg): return arg
    base = os.path.expanduser('~/.claude/projects')
    if os.path.isdir(arg):
        fs = glob.glob(os.path.join(arg, '*.jsonl'))
        return max(fs, key=os.path.getmtime)
    fs = glob.glob(f'{base}/*/{arg}*.jsonl')
    if not fs: sys.exit(f'no session for {arg}')
    return fs[0]

def summarize_input(name, inp):
    if not isinstance(inp, dict): return ''
    for k in ('command', 'file_path', 'pattern', 'url', 'query', 'description', 'prompt', 'path', 'skill'):
        if inp.get(k): return str(inp[k]).replace('\n', ' ')[:260]
    return json.dumps(inp)[:120]

def load(path):
    out = []
    for l in open(path, errors='replace'):
        try: out.append(json.loads(l))
        except Exception: pass
    return out

def walk(records, agent_id, agent_label, ev, pending):
    for o in records:
        t = o.get('type')
        if t not in ('assistant', 'user'): continue
        T = ts(o.get('timestamp'))
        m = o.get('message') or {}
        c = m.get('content')
        if t == 'assistant':
            u = m.get('usage') or {}
            ev['tokens'].append(dict(t=T, agent=agent_id, model=m.get('model'),
                inp=u.get('input_tokens', 0), out=u.get('output_tokens', 0),
                cr=u.get('cache_read_input_tokens', 0), cw=u.get('cache_creation_input_tokens', 0)))
        if not isinstance(c, list): 
            if t == 'user' and isinstance(c, str) and agent_id == 'main':
                c = re.sub(r'^(\s*<system-reminder>.*?</system-reminder>\s*)+', '', c, flags=re.S)
                ev['prompts'].append(dict(t=T, text=c[:300].replace('\n', ' ')))
            continue
        for b in c:
            bt = b.get('type')
            if bt == 'tool_use':
                pending[b['id']] = dict(id=b['id'], agent=agent_id, name=b['name'], t0=T,
                    arg=summarize_input(b['name'], b.get('input')), t1=None, err=False)
                if b['name'] in ('Agent', 'Task'):
                    inp = b.get('input') or {}
                    pending[b['id']]['spawn'] = dict(type=inp.get('subagent_type', 'general'),
                        desc=(inp.get('description') or '')[:80], bg=bool(inp.get('run_in_background')))
            elif bt == 'tool_result':
                p = pending.get(b.get('tool_use_id'))
                if p:
                    p['t1'] = T
                    p['err'] = bool(b.get('is_error'))
                    rc = b.get('content')
                    if isinstance(rc, list): rc = ' '.join(x.get('text', '') for x in rc if isinstance(x, dict))
                    p['res'] = str(rc or '')[:240].replace('\n', ' ')
            elif bt == 'text' and t == 'assistant' and agent_id == 'main':
                ev['notes'].append(dict(t=T, text=b['text'][:320].replace('\n', ' ')))
            elif bt == 'text' and t == 'user' and agent_id == 'main' and not str(b['text']).startswith('<'):
                ev['prompts'].append(dict(t=T, text=b['text'][:320].replace('\n', ' ')))

REDACT = [
    (re.compile(r'\b[a-z]{2,5}_[A-Za-z0-9]{24,}\b'), '[redacted-token]'),
    (re.compile(r'0x[a-fA-F0-9]{64,}'), '[hex-redacted]'),
    (re.compile(r'\b(sk|pk|rk|ghp|gho|ghs|github_pat|xox[bp]|AKIA|AIza|cfut|cfat)[-_A-Za-z0-9]{16,}'), '[redacted-token]'),
    (re.compile(r'(?i)\b(bearer|authorization:?\s*bearer|authorization:?)\s+[A-Za-z0-9._~+/=-]{12,}'), r'\1 [redacted]'),
    (re.compile(r'(?i)\b([A-Z0-9_]*(?:PRIVATE_?KEY|SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY)[A-Z0-9_]*)(?:\s*[=:]\s*|\s+)(?:0x)?[A-Za-z0-9+/_\-]{16,}'), r'\1=[redacted]'),
    (re.compile(r'0x[a-fA-F0-9]{64}\b'), '[redacted-key]'),
    (re.compile(r'(?i)\b(bearer|authorization:?)\s+[A-Za-z0-9._~+/=-]{12,}'), r'\1 [redacted]'),
    (re.compile(r'(?i)(private key|seed phrase|mnemonic)\b[^"]{0,6}[:=]?\s*(?:\w+\s+){11,23}\w+'), r'\1 [redacted]'),
    (re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{80,100}\b'), '[redacted-key]'),
    (re.compile(r'\b[a-fA-F0-9]{64}\b'), '[redacted-hex]'),
]
def redact(text):
    for rx, rep in REDACT: text = rx.sub(rep, text)
    return text

def build(path, since=None):
    tr = _build(path, since)
    return json.loads(redact(json.dumps(tr)))

def _build(path, since=None):
    recs = load(path)
    ev = dict(tokens=[], prompts=[], notes=[])
    pending = {}
    walk(recs, 'main', 'main', ev, pending)
    agents = [dict(id='main', label='main', type='main', parent=None)]
    sdir = path[:-6] + '/subagents'
    metas = {}
    for mf in glob.glob(sdir + '/*.meta.json'):
        try: metas[os.path.basename(mf)[:-10]] = json.load(open(mf))
        except Exception: pass
    for aid, meta in metas.items():
        jf = f'{sdir}/{aid}.jsonl'
        if not os.path.exists(jf): continue
        agents.append(dict(id=aid, label=meta.get('description', aid)[:60], type=meta.get('agentType', '?'),
                           parent='main', spawn_tool=meta.get('toolUseId'), depth=meta.get('spawnDepth', 1)))
        walk(load(jf), aid, aid, ev, pending)
    calls = sorted(pending.values(), key=lambda x: x['t0'] or 0)
    allt = [x for x in [c['t0'] for c in calls] + [c['t1'] for c in calls] if x]
    allt += [k['t'] for k in ev['tokens'] if k['t']]
    t0, t1 = min(allt), max(allt)
    if since:
        s = ts(since); calls = [c for c in calls if (c['t0'] or 0) >= s]
    for c in calls:
        c['t0'] -= t0
        c['t1'] = (c['t1'] - t0) if c['t1'] else None
    for k in ev['tokens']: k['t'] = (k['t'] or t0) - t0
    for k in ev['prompts'] + ev['notes']: k['t'] = (k['t'] or t0) - t0
    # link spawn calls to agents
    spawn_ids = {a.get('spawn_tool'): a['id'] for a in agents if a.get('spawn_tool')}
    for c in calls:
        if c['id'] in spawn_ids: c['spawned'] = spawn_ids[c['id']]
    # swarm = any time >=2 agents have overlapping tool activity
    ints = collections.defaultdict(list)
    for c in calls:
        if c['t1'] is not None: ints[c['agent']].append((c['t0'], c['t1']))
    peak = 0
    pts = sorted([(a, 1) for v in ints.values() for a, b in v] + [(b, -1) for v in ints.values() for a, b in v])
    cur = 0
    for _, d in pts: cur += d; peak = max(peak, cur)
    return dict(session=os.path.basename(path)[:-6], source=path, start=t0, duration=t1 - t0,
                agents=agents, calls=calls, **ev, peak_parallel_calls=peak,
                swarm=len(agents) > 1)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('-o'); ap.add_argument('--since')
    a = ap.parse_args()
    tr = build(resolve(a.src), a.since)
    s = json.dumps(tr, separators=(',', ':'))
    if a.o: open(a.o, 'w').write(s); print(f'{a.o}: {len(tr["calls"])} calls, {len(tr["agents"])} agents, {tr["duration"]/3600:.1f}h')
    else: print(s)
