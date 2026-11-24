import json, os, re, subprocess, sys, tempfile, unittest
R = os.path.join(os.path.dirname(__file__), '..'); S = os.path.join(R, 'scripts'); FIX = os.path.join(R, 'examples', 'demo-session.jsonl')
sys.path.insert(0, S)
from parse_trace import redact
from work_state import work, keep

class Odin(unittest.TestCase):
    def test_work_threads(self):
        D = [d for d in work(FIX) if keep(d)]
        self.assertEqual(len(D), 3)
        self.assertEqual([len(d['steps']) for d in D], [4, 3, 3])
        self.assertEqual(D[1]['decisions'][0]['a'], 'In-memory (Recommended)')
        self.assertIn('limiter.ts', D[0]['files'])
        self.assertEqual(D[0]['commits'], ['Add token-bucket rate limiter'])
        self.assertEqual(D[2]['ask'], 'Deploy to production?')
        self.assertTrue(D[2]['deploys'])

    def test_redaction(self):
        for secret in ('vcp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3', 'Bearer abcdefghijklmnop1234567890', 'API_KEY=supersecretvalue123', '0x' + 'ab' * 32):
            self.assertNotIn(secret.split('=')[-1], redact('x ' + secret + ' y'))

    def test_build_page(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'v.html')
            subprocess.run([sys.executable, os.path.join(S, 'build_work_view.py'), FIX, '--all', '--standalone', '-o', out], check=True, capture_output=True)
            h = open(out).read()
            self.assertTrue(h.startswith('<!doctype html>'))
            self.assertNotIn('/*DATA*/[]', h); self.assertNotIn('/*META*/', h)
            m = re.search(r'const META=(\{.*?\}),DATA=(\[.*?\]);\n', h, re.S)
            self.assertEqual(len(json.loads(m.group(2))), 3)
            self.assertTrue(json.loads(m.group(1))['paras'])

    def test_summary_file(self):
        with tempfile.TemporaryDirectory() as d:
            sj = os.path.join(d, 's.json'); json.dump(dict(goal='My goal', paragraphs=['Done.[1]']), open(sj, 'w'))
            out = os.path.join(d, 'v.html')
            subprocess.run([sys.executable, os.path.join(S, 'build_work_view.py'), FIX, '--all', '--summary', sj, '-o', out], check=True, capture_output=True)
            self.assertIn('"goal":"My goal"', open(out).read())

    def test_live_flag(self):
        with tempfile.TemporaryDirectory() as d:
            for flag, want in (([], 'false'), (['--live'], 'true')):
                out = os.path.join(d, 'v.html')
                subprocess.run([sys.executable, os.path.join(S, 'build_work_view.py'), FIX, '--all', '-o', out, *flag], check=True, capture_output=True)
                self.assertIn('"live":' + want, open(out).read())

    def test_style(self):
        with tempfile.TemporaryDirectory() as d:
            sj = os.path.join(d, 'st.json'); json.dump(dict(palette='ember', motif='grid', why='Incident run.'), open(sj, 'w'))
            out = os.path.join(d, 'v.html')
            subprocess.run([sys.executable, os.path.join(S, 'build_work_view.py'), FIX, '--all', '--style', sj, '-o', out], check=True, capture_output=True)
            self.assertIn('"palette":"ember"', open(out).read())
            subprocess.run([sys.executable, os.path.join(S, 'build_work_view.py'), FIX, '--all', '-o', out], check=True, capture_output=True)
            self.assertIn('"style":{"palette":', open(out).read())   # auto

if __name__ == '__main__': unittest.main()
