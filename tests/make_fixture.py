#!/usr/bin/env python3
"""Writes examples/demo-session.jsonl: a small made-up Claude Code session (no real data).
Used by the smoke test and the landing-page demo. Run: python3 tests/make_fixture.py"""
import json, os, datetime as dt
out = os.path.join(os.path.dirname(__file__), '..', 'examples', 'demo-session.jsonl')
t = dt.datetime(2026, 3, 9, 9, 0, 0, tzinfo=dt.timezone.utc); n = [0]; L = []
def tick(s=20):
    global t; t += dt.timedelta(seconds=s); return t.isoformat().replace('+00:00', 'Z')
def user(text): L.append(dict(type='user', timestamp=tick(60), message=dict(role='user', content=text)))
def asst(*blocks): L.append(dict(type='assistant', timestamp=tick(), message=dict(role='assistant', content=list(blocks))))
def use(name, **inp):
    n[0] += 1; return dict(type='tool_use', id=f'tu{n[0]}', name=name, input=inp)
def result(b, text): L.append(dict(type='user', timestamp=tick(2), message=dict(role='user', content=[dict(type='tool_result', tool_use_id=b['id'], content=text)])))
def say(x): return dict(type='text', text=x)
def plan(items): return use('mcp__ccd_turn__update_plan', items=[dict(content=c, status=s) for c, s in items])

user('Add rate limiting to our public API so one client cannot take it down.')
asst(plan([('Read the current request flow', 'in_progress'), ('Write the limiter', 'pending'), ('Add tests', 'pending'), ('Update the docs', 'pending')]))
asst(use('Read', file_path='/work/api/src/server.ts'))
asst(use('mcp__ccd_turn__update_plan', advance=True))
asst(use('Write', file_path='/work/api/src/limiter.ts', content='...'))
asst(use('Edit', file_path='/work/api/src/server.ts', old_string='a', new_string='b'))
asst(use('mcp__ccd_turn__update_plan', advance=True))
asst(use('Write', file_path='/work/api/test/limiter.test.ts', content='...'))
b = use('Bash', command='git commit -m "Add token-bucket rate limiter"'); asst(b); result(b, 'ok')
asst(use('mcp__ccd_turn__update_plan', advance=True), use('Edit', file_path='/work/api/README.md', old_string='a', new_string='b'))
asst(use('mcp__ccd_turn__wrap_up', recap='The API now limits each client to 60 requests a minute. Tests pass. The limit is a constant in limiter.ts.'))

user('Make the limit per API key, not per IP.')
asst(plan([('Find where keys are read', 'in_progress'), ('Choose a counter store', 'pending'), ('Switch the limiter to keys', 'pending')]))
q = use('AskUserQuestion', questions=[dict(question='Which store should hold the counters?', options=[dict(label='In-memory (Recommended)'), dict(label='Redis'), dict(label='D1')])])
asst(q); result(q, 'User has answered your questions: "Which store should hold the counters?"="In-memory (Recommended)". You can now continue.')
asst(use('mcp__ccd_turn__update_plan', done=[1, 2], start=3), use('Edit', file_path='/work/api/src/limiter.ts', old_string='a', new_string='b'))
asst(use('Edit', file_path='/work/api/src/auth.ts', old_string='a', new_string='b'))
asst(use('mcp__ccd_turn__wrap_up', recap='Limits are now per API key and kept in memory. A key over its limit gets a 429 with a Retry-After header.'))

user('ok ship it to staging')
asst(plan([('Run the test suite', 'in_progress'), ('Deploy to staging', 'pending'), ('Check the live limit', 'pending')]))
b = use('Bash', command='npm test'); asst(b); result(b, '14 passed')
asst(use('mcp__ccd_turn__update_plan', advance=True))
b = use('Bash', command='cf deploy --env staging', description='Deploy to staging'); asst(b); result(b, 'deployed')
asst(use('mcp__ccd_turn__update_plan', advance=True))
asst(use('mcp__ccd_turn__wrap_up', recap='Staging is live. The 61st request in a minute returns 429, as planned.', ask='Deploy to production?', actions=[dict(label='Yes, deploy'), dict(label='Not yet')]))
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w').write('\n'.join(json.dumps(o) for o in L) + '\n'); print(out, len(L), 'records')
