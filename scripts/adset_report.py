#!/usr/bin/env python3
"""Work brief: what the user directed and what the agent did, in ASD-STE100 style.
Usage: adset_report.py trace.json [--last N] [--lint] [--json]
Output has one block for each user direction: Direction, Read, Looked for, Did, Found.
This is a draft built by rules. The agent that runs the skill must rewrite weak lines from the --json work log."""
import sys, json, re, os, collections
SKIP = ('Your response above was cut off', 'Background', '<', '[Request', 'Linked', 'Caveat', '[Image')

def clean(s, n):
    s = re.sub(r'\s+', ' ', s or '').strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '...'

def first_sentence(s, n=150):
    s = re.sub(r'[`*#>]', '', s or ''); s = re.sub(r'\s+', ' ', s).strip()
    m = re.match(r'(.+?[.!?])(\s|$)', s)
    return clean(m.group(1) if m else s, n)

BASH = [  # (regex, template). First match wins.
    (r'git commit .*?-m\s+["\']?(?:\$\(cat <<.?EOF\s*)?([^"\'\n]{5,90})', 'Committed: {0}'),
    (r'git push', 'Pushed code to the remote'),
    (r'(wrangler|cf)\s+(pages\s+)?deploy|deploy\.py|vercel (--prod|deploy)', 'Deployed the project'),
    (r'\b(pytest|vitest|jest|cargo test|npm (run )?test|node --test|python3? -m unittest)\b', 'Ran the tests'),
    (r'\b(npm|pnpm|bun|pip3?|cargo) (install|add|i)\b', 'Installed packages'),
    (r'\bcrontab\b', 'Changed the cron schedule'),
    (r'\bssh\s+(\S+)', 'Ran a command on {0}'),
    (r'\bpython3?\s+(\S+\.py)', 'Ran {0}'),
    (r'\bnpx tsx\s+(\S+)', 'Ran {0}'),
    (r'\bcurl\b.*?(https?://[^\s"\']+)', 'Called {0}'),
    (r'\b(rm|mv|cp)\s', None),
]

RD = re.compile(r'\b(?:cat|head|tail|less|bat)\s+(?:-\S+\s+)*(\S+)')
GR = re.compile(r'\b(?:rg|grep|egrep)\s+(?:-\S+\s+)*["\']?([^"\'\s|]{2,60})')

def investigate(seg):
    """Return reads, looked-for, did-actions from the calls in one stretch of work."""
    reads, looks, did = [], [], []
    def add(l, x):
        x = clean(x, 60)
        if x and x not in l: l.append(x)
    for c in seg:
        n, a = c['name'], c['arg']
        if n == 'Read': add(reads, os.path.basename(a))
        elif n == 'Grep': add(looks, '"' + a + '"')
        elif n == 'Glob': add(looks, 'files named ' + a)
        elif n == 'WebSearch': add(looks, a)
        elif n == 'WebFetch': add(reads, re.sub(r'^https?://', '', a))
        elif n in ('Agent', 'Task'):
            sp = c.get('spawn') or {}; add(did, 'Asked a subagent: ' + (sp.get('desc') or a))
        elif n == 'Bash':
            m = GR.search(a)
            if m: add(looks, '"' + m.group(1).strip('()\\') + '"')
            m = RD.search(a)
            if m and re.search(r'[./]', m.group(1)) and not m.group(1).startswith(('-', '>', '<', '|', '$(')) and 'output' not in m.group(1): add(reads, os.path.basename(m.group(1)))
            for rx, tpl in BASH:
                m = re.search(rx, a)
                if m and tpl and not tpl.startswith(('Called', 'Ran a command')):
                    add(did, tpl.format(*[clean(g, 70) for g in m.groups() if g])); break
            for u in re.findall(r'curl\b[^|]*?(https?://[^\s"\']+)', a): add(reads, re.sub(r'^https?://', '', u)[:50])
            m = re.search(r'\bssh\s+(\S+)', a)
            if m: add(reads, 'live state on ' + m.group(1))
        elif n in ('Edit', 'Write', 'NotebookEdit'):
            add(did, 'Changed ' + os.path.basename(a))
        elif n.startswith('Artifact'): add(did, 'Published or changed an artifact')
    return reads, looks, did

def lst(x, k=5):
    return ', '.join(x[:k]) + (f' and {len(x)-k} more' if len(x) > k else '')

def worklog(tr):
    ps = [p for p in tr['prompts'] if p['text'] and not p['text'].startswith(SKIP)]
    notes, calls = tr['notes'], tr['calls']
    log = []
    for i, p in enumerate(ps):
        t0, t1 = p['t'], ps[i+1]['t'] if i + 1 < len(ps) else 1e18
        seg = [c for c in calls if t0 <= c['t0'] < t1]
        reads, looks, did = investigate(seg)
        nt = [x for x in notes if t0 <= x['t'] < t1 and len(x['text']) > 30 and 'subscription' not in x['text'][:80]]
        found = [first_sentence(x['text']) for x in nt[-2:]]
        log.append(dict(t=p['t'], direction=clean(p['text'], 140), read=reads, looked_for=looks, did=did,
                        found=found, failed=sum(1 for c in seg if c['err'])))
    return log

def report(tr, last=5):
    log = [b for b in worklog(tr) if b['read'] or b['looked_for'] or b['did'] or b['found']][-last:]
    if not log: return 'No user direction found in this run.'
    out = []
    for b in log:
        out.append(f"Direction: {b['direction']}")
        if b['read']: out.append('Read: ' + lst(b['read']) + '.')
        if b['looked_for']: out.append('Looked for: ' + lst(b['looked_for'], 4) + '.')
        if b['did']: out.append('Did: ' + '. '.join(b['did'][:4]) + '.')
        if b['found']: out.append('Found: ' + ' '.join(dict.fromkeys(b['found'])))
        out.append('')
    return '\n'.join(out).strip()

def lint(text, max_words=25):
    issues = []
    for i, line in enumerate(text.split('\n'), 1):
        if line.startswith(('Direction:', 'Read:', 'Looked for:')): continue  # user words, not ours
        for s in re.split(r'(?<=[.!?])\s+', line):
            if len(s.split()) > max_words: issues.append(f'line {i}: {len(s.split())} words: {s[:40]}')
            if re.search(r"\b\w+n't\b|\b\w+'(re|ve|ll)\b", s): issues.append(f'line {i}: contraction: {s[:40]}')
            if re.search(r'\b(is|are|was|were|been|being)\s+\w+ed\b', s): issues.append(f'line {i}: possible passive: {s[:40]}')
    return issues

if __name__ == '__main__':
    tr = json.load(open(sys.argv[1])); last = int(sys.argv[sys.argv.index('--last') + 1]) if '--last' in sys.argv else 5
    if '--json' in sys.argv: print(json.dumps(worklog(tr), indent=1))
    else:
        r = report(tr, last); print(r)
        if '--lint' in sys.argv: [print('LINT', x) for x in lint(r)]
