"""Never publish a passed lifecycle result when teardown or source isolation failed."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('session_probe', ROOT/'scripts/probe-xiri-session.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ResultTests(unittest.TestCase):
    def test_unclean_or_changed_source_cannot_pass(self):
        for clean, unchanged in [(False, True), (True, False)]:
            with self.subTest(clean=clean, unchanged=unchanged), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'result.json'
                result = dict(status='passed', clean_shutdown=clean, base_raw_unchanged=unchanged)
                with self.assertRaisesRegex(RuntimeError, 'clean halt and unchanged'):
                    probe.record_result(path, result)
                self.assertEqual(json.loads(path.read_text())['status'], 'error')

    def test_original_failure_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.json'
            result = dict(status='error', error='guest startup failed', clean_shutdown=False,
                          base_raw_unchanged=True)
            probe.record_result(path, result)
            self.assertEqual(json.loads(path.read_text()), result)
            self.assertEqual(result['error'], 'guest startup failed')

    def test_clean_pass_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.json'
            result = dict(status='passed', clean_shutdown=True, base_raw_unchanged=True)
            probe.record_result(path, result)
            self.assertEqual(json.loads(path.read_text()), result)
