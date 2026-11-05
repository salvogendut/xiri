import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('type1_qualification', ROOT/'scripts/qualify-type1-scaler.py')
qualification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualification)


class NativeFpuEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT/'docs/results/2026-11-05-type1-scaler.json').read_text())['native_registers']

    def test_observed_baseline_and_candidate(self):
        qualification.registers(self.records['baseline']['output'], False)
        qualification.registers(self.records['candidate']['output'], True)

    def test_old_kernel_cannot_pass_as_fixed(self):
        with self.assertRaises(AssertionError):
            qualification.registers(self.records['baseline']['output'], True)

    def test_missing_rounding_mode_rejected(self):
        text = self.records['candidate']['output']
        with self.assertRaises(AssertionError):
            qualification.registers(text.split('\n', 1)[1], True)

    def test_lost_fcsr_rejected_even_with_pass_marker(self):
        text = self.records['candidate']['output'].replace('csr=00000004', 'csr=00000000', 1)
        with self.assertRaises(AssertionError):
            qualification.registers(text, True)
