import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.catalog_provider.state import State
from tools.catalog_provider.workers import CodeReviewWorker, DocsLintWorker, parse_note, resolve_target

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'guide.md').write_text('# Title\n\nSome text \n', encoding='utf-8')
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'app.py').write_text('def f():\n    print(\"x\")\n', encoding='utf-8')
    def tearDown(self):
        self.tmp.cleanup()
    def test_parse_note(self):
        self.assertEqual(parse_note('repo=docs\nmodel=local')['repo'], 'docs')
    def test_resolve_target(self):
        self.assertEqual(resolve_target({'note': 'path=docs'}, self.root), (self.root / 'docs').resolve())
    def test_docs_lint(self):
        out = DocsLintWorker(self.root).work({'note': 'path=docs'})
        self.assertIn('Docs lint report', out.content)
        self.assertIn('trailing whitespace', out.content)
    def test_code_review(self):
        out = CodeReviewWorker(self.root).work({'note': 'path=src'})
        self.assertIn('Code review', out.content)
        self.assertIn('debug print call', out.content)

class StateTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = State(path)
            state.record('abc', delivered=True, sha256='deadbeef')
            again = State(path)
            self.assertTrue(again.get('abc')['delivered'])
            self.assertEqual(again.get('abc')['sha256'], 'deadbeef')

if __name__ == '__main__':
    unittest.main()
