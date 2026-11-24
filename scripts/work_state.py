#!/usr/bin/env python3
"""work_state.py <session|id|project-dir> [--last N] [--widget]
Reads the WORK from a transcript, never harness metrics. One record per work thread (a user direction plus
short replies that answer the agent's question). Each record has:
 goal, steps (final plan) and plan frames over time, findings (every recap and the last reply, in order),
 decisions (question, options, the user's answer), outputs (files with edit counts, commits, deploys,
 published links, subagents, sessions started) and the open question, if any.
Sources: user prompts, update_plan/TodoWrite, wrap_up recaps, AskUserQuestion and its answer, Edit/Write,
git commit, deploy commands, Artifact results, Agent spawns, assistant text.
Coverage numbers are printed with --coverage."""
import sys, os, re, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from parse_trace import resolve, redact, ts
SKIP = ('[Your previous', '[Earlier usage', '[Usage limit', 'Base directory', 'This session is being continued',
        'Your response above was cut off', 'Background', '<', '[Request', 'Linked', 'Caveat', '[Image', '[SYSTEM')
URL = re.compile(r'https?://[^\s"\')\]>,]+')
DEPLOY = re.compile(r'(?:^|[;&|]\s*)(?:(?:wrangler|cf)\s+(?:pages\s+)?deploy|vercel\s+(?:--prod|deploy)|git\s+push|scp|rsync)\b|(?:^|[;&|]\s*)(?:python3?\s+\S*)?deploy\.py')

def load(p):
    for l in open(p, errors='replace'):
        try: yield json.loads(l)
        except Exception: pass

def clean(s, n):
    s = re.sub(r'\s+', ' ', s or '').strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '...'

def new(t, text):
    return dict(t0=t, t1=t, goal=clean(text, 200), steps=[], frames=[], findings=[], decisions=[], reply='',
                files=collections.OrderedDict(), commits=[], deploys=[], links=[], subagents=[], sessions=[], ask='', options=[])

def apply_plan(d, i, t):
    st = d['steps']
    its = i.get('items') or i.get('todos')
    if its:
        st[:] = [dict(c=clean(x.get('content') or x.get('subject') or '', 80), s=x.get('status', 'pending')) for x in its]
        d['frames'] = []
    elif i.get('advance'):
        for k, s in enumerate(st):
            if s['s'] == 'in_progress':
                s['s'] = 'completed'
                if k + 1 < len(st) and st[k+1]['s'] == 'pending': st[k+1]['s'] = 'in_progress'
                break
        else:
            for s in st:
                if s['s'] == 'pending': s['s'] = 'in_progress'; break
    else:
        for n in i.get('done', []):
            if 0 < n <= len(st): st[n-1]['s'] = 'completed'
        if i.get('start') and 0 < i['start'] <= len(st): st[i['start']-1]['s'] = 'in_progress'
    d['frames'].append([round(t / 60, 2), ''.join({'completed': 'd', 'in_progress': 'p'}.get(s['s'], '-') for s in st)])

def work(path):
    D, cur, t0, pend, ask = [], None, None, {}, None
    for o in load(path):
        T = ts(o.get('timestamp'))
        if T is None or o.get('type') not in ('assistant', 'user'): continue
        t0 = t0 or T; t = T - t0; m = o.get('message') or {}; c = m.get('content')
        if cur: cur['t1'] = t
        if o['type'] == 'user':
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get('type') == 'tool_result' and cur:
                        nm = pend.get(b.get('tool_use_id')); rc = b.get('content')
                        if isinstance(rc, list): rc = ' '.join(x.get('text', '') for x in rc if isinstance(x, dict))
                        rc = str(rc or '')
                        if nm == 'AskUserQuestion':
                            ans = re.findall(r'"="(.+?)"(?:, "|\.|$)', rc)
                            open_ = [dd for dd in cur['decisions'] if not dd['a']]
                            for dd, a in zip(open_[-len(ans):], ans): dd['a'] = clean(a, 100)
                        elif nm == 'Artifact' and rc.startswith('Published /'):
                            for u in URL.findall(rc)[:1]:
                                if u not in cur['links']: cur['links'].append(u[:90])
            txt = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in (c or []) if isinstance(b, dict) and b.get('type') == 'text')
            txt = re.sub(r'^(\s*<system-reminder>.*?</system-reminder>\s*)+', '', txt or '', flags=re.S).strip()
            real = bool(txt) and not txt.startswith(SKIP) and not any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in (c or []))
            if real:
                if ask and cur and len(txt) < 80:  # a short reply answers the open question; same thread
                    cur['decisions'].append(dict(q=ask[0], o=ask[1], a=clean(txt, 100), t=round(t / 60, 1))); ask = None
                else:
                    ask = None; cur = new(t, txt); D.append(cur)
            continue
        if cur is None or not isinstance(c, list): continue
        for b in c:
            bt = b.get('type')
            if bt == 'text' and len(b.get('text', '')) > 40: cur['reply'] = clean(re.sub(r'[`*#>]', '', b['text']), 360)
            if bt != 'tool_use': continue
            n, i = b['name'], b.get('input') or {}; pend[b['id']] = n
            if n.endswith('update_plan') or n == 'TodoWrite': apply_plan(cur, i, t)
            elif n.endswith('wrap_up'):
                for s in cur['steps']: s['s'] = 'completed'
                cur['frames'].append([round(t / 60, 2), 'd' * len(cur['steps'])])
                if i.get('recap'): cur['findings'].append(dict(t=round(t / 60, 1), x=clean(i['recap'], 420)))
                if i.get('ask'):
                    opts = [a.get('label') or a.get('action') for a in i.get('actions', []) if isinstance(a, dict)][:3]
                    ask = (clean(i['ask'], 140), opts); cur['ask'], cur['options'] = ask
                else: ask = None; cur['ask'] = ''; cur['options'] = []
            elif n == 'AskUserQuestion':
                for q in i.get('questions', []):
                    cur['decisions'].append(dict(q=clean(q.get('question', ''), 150), o=[x.get('label') for x in q.get('options', [])][:3], a='', t=round(t / 60, 1)))
            elif n in ('Edit', 'Write', 'NotebookEdit'):
                f = os.path.basename(i.get('file_path', ''))
                if f and not re.search(r'[;*$]', f): cur['files'][f] = cur['files'].get(f, 0) + 1
            elif n == 'Bash':
                cmd = i.get('command', '')
                m2 = re.search(r'git commit .*?-m\s+["\']?(?:\$\(cat <<.?EOF\s*)?([^"\'\n]{5,90})', cmd)
                if m2: cur['commits'].append(m2.group(1).strip())
                for pat in (r'(?:^|[;&|]\s*)cat\s*>>?\s*(\S+)', r'\btee\s+(?:-a\s+)?(\S+)', r'\bsed\s+-i\S*\s+(?:-e\s+)?(?:"[^"]*"|\'[^\']*\'|\S+)\s+(\S+)', r"open\(\s*['\"]([^'\"]+\.\w+)['\"]\s*,\s*['\"]w", r'\b(?:mv|cp)\s+\S+\s+(\S+)'):
                    for mm in re.findall(pat, cmd):
                        f = os.path.basename(mm.strip('"\''))
                        if f and not f.startswith(('-', '$', '/dev')) and '.' in f and not re.search(r'[;*$<>|]', f): cur['files'][f] = cur['files'].get(f, 0) + 1
                if DEPLOY.search(cmd.split('\n')[0]):
                    cur['deploys'].append(clean(i.get('description') or cmd, 70))
            elif n in ('Agent', 'Task'):
                cur['subagents'].append(dict(type=i.get('subagent_type', 'general'), desc=clean(i.get('description') or i.get('prompt', ''), 70)))
            elif n.endswith('start_session'):
                cur['sessions'].append(clean(i.get('title') or i.get('prompt', ''), 60))
    for d in D:
        if not d['findings'] and d['reply']: d['findings'].append(dict(t=round(d['t1'] / 60, 1), x=d['reply'], kind='reply'))
        d['t0'] = round(d['t0'] / 60, 1); d['t1'] = round(d['t1'] / 60, 1)
        d['files'] = dict(d['files']); d['deploys'] = list(dict.fromkeys(d['deploys'])); d['commits'] = list(dict.fromkeys(d['commits']))
    return D

def keep(d): return d['steps'] or d['findings'] or d['files'] or d['commits'] or d['decisions'] or d['subagents'] or d['deploys']

if __name__ == '__main__':
    a = sys.argv[1:]; last = int(a[a.index('--last') + 1]) if '--last' in a else 8
    D = work(resolve(a[0])); K = [d for d in D if keep(d)]
    if '--coverage' in a:
        print(json.dumps(dict(directions_found=len(D), with_work=len(K), shown=min(last, len(K)),
              steps=sum(len(d['steps']) for d in K), findings=sum(len(d['findings']) for d in K), decisions=sum(len(d['decisions']) for d in K),
              files=sum(len(d['files']) for d in K), commits=sum(len(d['commits']) for d in K)))); sys.exit()
    out = K[-last:]
    if '--widget' in a:
        for d in out:
            fr = [f for f in d['frames'] if len(f[1]) == len(d['steps'])]
            d['frames'] = [f for k, f in enumerate(fr) if k == 0 or f[1] != fr[k-1][1]][-14:]
            d.pop('reply', None)
            d['nfind'] = len(d['findings']); d['findings'] = d['findings'][-8:]
            d['files'] = dict(sorted(d['files'].items(), key=lambda x: -x[1])[:12]); d['commits'] = d['commits'][:6]; d['deploys'] = d['deploys'][:4]
    print(json.dumps(json.loads(redact(json.dumps(out))), separators=(',', ':'), ensure_ascii=False))
