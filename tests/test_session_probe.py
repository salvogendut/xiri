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
sleep_spec = importlib.util.spec_from_file_location('sleep_probe', ROOT/'scripts/probe-native-sleep.py')
sleep_probe = importlib.util.module_from_spec(sleep_spec)
sleep_spec.loader.exec_module(sleep_probe)


class ResultTests(unittest.TestCase):
    def test_launcher_zero_requires_sleep_completion(self):
        summary = ('SLEEP_RESULT method=usleep iterations=100 child=687 rc=0 '
                   'observer_failed=0 minor_faults=40 major_faults=0 voluntary=101 involuntary=14')
        case = dict(method='usleep', status='0', summary=summary)
        self.assertTrue(sleep_probe.sleep_case_passed(case, 100))
        for damaged in ('Terminated', '', summary.replace('rc=0', 'rc=142'),
                        summary.replace('observer_failed=0', 'observer_failed=1'),
                        summary.replace('iterations=100', 'iterations=99')):
            with self.subTest(summary=damaged):
                self.assertFalse(sleep_probe.sleep_case_passed(dict(case, summary=damaged), 100))
        self.assertFalse(sleep_probe.sleep_case_passed(dict(case, status='1'), 100))

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
