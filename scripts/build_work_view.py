#!/usr/bin/env python3
"""build_work_view.py <session|id|project-dir> [--all | --last N] [--name NAME] [--goal TEXT] [--summary summary.json] [-o out.html] [--standalone] [--live] [--style style.json|auto|default]
--summary takes {"goal": "...", "paragraphs": ["Plain sentence.[3] Another.[5]"]}: write it yourself in short STE sentences; [n] links to task n.
--style takes {"palette": gold|ember|ocean|forest|violet|ink, "font": serif|sans|mono, "motif": ring|grid|dots|none, "density": airy|compact, "order": [live,hero,chips,charts,needs,why,strip], "why": "one sentence"}. The default is auto: a look picked from the project name. Choose one yourself from the work.
--live turns on the Inbox tab, the Live now card, answer buttons and comments. Publish it with the capabilities in references/live.md.
Without --summary Odin writes a short factual summary from the data.
Fills assets/work_view.html with the WORK of a session (goals, steps, findings, decisions, outputs).
Default output is an artifact-ready fragment. Titles are the first sentence of each task's first finding.
Use for long sessions where the data is too big to put into an inline widget."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
from parse_trace import resolve, redact, ts
from work_state import work, keep, load

GENERIC = re.compile(r'^(writing code|working|done|ok|okay|sure|got it|understood|fair point|polishing|nothing changed)\b', re.I)

def first(x, n=72):
    """Title from a result: the first sentence that says something. Skips filler openers; cuts at a colon or dash when long."""
    sents = [t.strip() for t in re.split(r'(?<=[.!?])\s+', x) if t.strip()]
    pick = next((t for t in sents if len(t) >= 25 and not GENERIC.match(t)), sents[0] if sents else x)
    pick = pick.rstrip('.')
    if len(pick) > n:
        cut = re.split(r'[:;]\s|\s[-\u2014]\s', pick)[0]
        pick = cut if 35 <= len(cut) <= n else pick[:n].rsplit(' ', 1)[0] + '...'
    return pick

def trace(notes, n=6):
    """Up to n reasoning snippets in time order, decision-like ones first priority."""
    dec = [x for x in notes if x['k'] == 'd'][:4]
    rest = [x for x in notes if x['k'] != 'd'][:max(0, n - len(dec))]
    pick = sorted(dec + rest, key=lambda x: x['t'])
    return [[x['x'][:230], 'd' if x['k'] == 'd' else 'n'] for x in pick]

PALETTES = ['gold', 'ember', 'ocean', 'forest', 'violet', 'ink']

def auto_style(name, ntasks):
    """A different look per project, so runs do not all look alike. The agent should override this with --style."""
    import hashlib
    h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    return dict(palette=PALETTES[h % 6], motif=['ring', 'grid', 'dots', 'ring', 'grid', 'none'][(h >> 3) % 6],
                font=['serif', 'serif', 'sans'][(h >> 6) % 3], density='compact' if ntasks > 40 else 'airy', why='')

def slim(d):
    fi = [dict(t=round(f['t']), x=f['x'][:300]) for f in d['findings'][-3:]]
    return dict(t=round(d['t0']), e=round(d['t1']), g=d['goal'][:110], ti=first(fi[0]['x']) if fi else d['goal'][:60],
        st=[[s['c'][:70], s['s'][0]] for s in d['steps']][:8], fi=fi,
        de=[dict(q=y['q'][:120], o=y['o'][:3], a=y['a'][:80]) for y in d['decisions'][-4:]],
        fl=dict(sorted(d['files'].items(), key=lambda x: -x[1])[:8]), nfl=len(d['files']), cm=[c[:60] for c in d['commits'][:3]],
        dp=[c[:50] for c in d['deploys'][:3]], ln=[l.split('/')[-1] for l in d['links'][:2]], ask=d['ask'][:120], op=d['options'][:3], tr=trace(d['notes']))

def auto_summary(sl, total):
    """Plain-text summary with [n] footnote refs (n = task number). Short, active sentences."""
    P = []; N = len(sl)
    if not N: return P
    last = sl[-1]
    P.append(f"Latest task: {last['ti'].rstrip('.')}.[{N}]" + (f" It waits for you: {last['ask']}[{N}]" if last['ask'] else ''))
    ship = [i for i, d in enumerate(sl) if d['dp'] or d['cm'] or d['ln']]
    if ship:
        pick = ship[-3:]
        P.append(f"It shipped work in {len(ship)} task{'s' if len(ship) != 1 else ''}. Latest: " + '; '.join(f"{sl[i]['ti']}[{i+1}]" for i in pick) + '.')
    ds = [(i, y) for i, d in enumerate(sl) for y in d['de'] if y['a']]
    if ds:
        i, y = ds[-1]
        P.append(f"You made {len(ds)} decision{'s' if len(ds) != 1 else ''}. Latest: {y['q'].rstrip('?')}? You said: \"{y['a']}\".[{i+1}]")
    files = {f for d in sl for f in d['fl']}
    w = [i + 1 for i, d in enumerate(sl) if d['ask']]
    P.append(f"{len(files)} file{'s' if len(files) != 1 else ''} changed. " + (f"{len(w)} task{'s' if len(w) != 1 else ''} wait on you." if w else 'Nothing waits on you.'))
    return P

if __name__ == '__main__':
    a = sys.argv[1:]; path = resolve(a[0])
    last = None if '--all' in a else int(a[a.index('--last') + 1]) if '--last' in a else 40
    D = work(path); K = [d for d in D if keep(d)]
    for d in K[:-1]: d['ask'] = ''; d['options'] = []   # only the newest task can still wait: the user moved on from older ones
    S = K if last is None else K[-last:]
    base = next(ts(o.get('timestamp')) for o in load(path) if o.get('timestamp')) * 1000
    proj = os.path.basename(os.path.dirname(path)).replace('-home-david-', '').strip('-') or 'Session'
    name = a[a.index('--name') + 1] if '--name' in a else proj
    note = (f'Showing {len(S)} of {len(K)} tasks that had work. Odin reads your requests, plan steps, recaps, questions and answers, file edits '
            '(including files written by shell commands), commits, deploys and links. Work never written to a plan, recap, file or link is not visible. '
            'Titles are the first sentence of each result. Your exact words are under each title. Key-like values are redacted by pattern; check before sharing.')
    sl = [slim(d) for d in S]
    goal = a[a.index('--goal') + 1] if '--goal' in a else ''
    paras = None
    if '--summary' in a:
        sj = json.load(open(a[a.index('--summary') + 1])); goal = sj.get('goal', goal); paras = sj.get('paragraphs')
    if paras is None: paras = auto_summary(sl, len(K))
    if not goal:   # first request when the run is short (one goal); the latest request when it spans many days
        goal = sl[0]['g'] if (sl[-1]['e'] - sl[0]['t']) < 2880 else f"The latest request: {sl[-1]['g']}"
    sty = a[a.index('--style') + 1] if '--style' in a else 'auto'
    style = auto_style(name, len(K)) if sty == 'auto' else {} if sty == 'default' else json.load(open(sty))
    meta = dict(name=name + ' work view', base=base, total=len(K), note=note, goal=goal, paras=paras, live='--live' in a, style=style)
    tpl = open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'work_view.html')).read()
    esc = lambda o: redact(json.dumps(o, separators=(',', ':'), ensure_ascii=False)).replace('</', '<\\/')
    h = tpl.replace('/*TITLE*/', f'{name} Work View').replace('/*META*/{"name":"Work","base":0,"total":0,"note":""}', esc(meta)).replace('/*DATA*/[]', esc(sl))
    if '--standalone' in a:   # a full page, for hosting or a local file; the default is a fragment for the Artifact tool
        h = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + h + '</html>'
    out = a[a.index('-o') + 1] if '-o' in a else os.path.expanduser(f'~/agent-trace-out/{proj}-work.html')
    out = os.path.abspath(out); os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w').write(h)
    print(out, len(S), 'tasks', len(h) // 1024, 'KB')
