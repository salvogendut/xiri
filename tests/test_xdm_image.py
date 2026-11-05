"""Reject incomplete cold-boot evidence before an xdm image can be promoted."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from xiri_lab.xdm_qualification import verify_sessions, verify_job_control
from xiri_lab.xdm_image import support_files
from xiri_lab.fonts import verify as verify_fonts


class XdmPromotionTests(unittest.TestCase):
    def setUp(self):
        # Reuse real session evidence; add the independently tested disk/catalog
        # observations as a host-only fixture, never as a qualification record.
        self.r=json.loads((ROOT/'docs/results/2026-11-03-xiri-xdm.json').read_text())
        older=json.loads((ROOT/'docs/results/2026-11-03-irix-module-image.json').read_text())
        self.r.update(scope='xdm-direct-chd',direct_disk_boot=True,base_chd_unchanged=True,
            graphics_console='kern.consdev = ttyE0\n/dev/ttyZ0\n',native_control=self.r['native_after'],
            shutdown_log='unmounting done\nhalting...\n',
            rpcbind_warning_events='XIRI_RPC_WATCH_START\nXIRI_RPC_WATCH_END\n')
        self.r['catalog_launch']={**older['catalog_launch'],**older['desktop_behavior']}

    def test_complete_evidence_accepted(self):
        verify_sessions(self.r)

    def test_boot_generated_motd_does_not_hide_configuration_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)
            (bundle/'copy-ledger.json').write_text(json.dumps({'files':[]}))
            seed=dict(staged={'/emul/irix/bin/sh':'vendor-hash'},installed_files={
                '/etc/motd':'before-kernel-prefix','/etc/xiri/xdm/Xservers':'server-hash'})
            inventory=support_files(bundle,seed)
            self.assertNotIn('/etc/motd',inventory)
            self.assertEqual(inventory['/etc/xiri/xdm/Xservers'],'server-hash')
            self.assertEqual(inventory['/emul/irix/bin/sh'],'vendor-hash')

    def test_cleanup_or_disk_failures_rejected(self):
        for key in ('clean_shutdown','base_chd_unchanged','direct_disk_boot'):
            r=copy.deepcopy(self.r);r[key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):verify_sessions(r)
        r=copy.deepcopy(self.r);r['sessions'][0]['guard']=r['sessions'][0]['guard'].replace('remaining=0','remaining=1')
        with self.assertRaises(AssertionError):verify_sessions(r)
        r=copy.deepcopy(self.r);r['shutdown_log']='Done running shutdown hooks.'
        with self.assertRaises(AssertionError):verify_sessions(r)

    def test_wrong_native_identity_or_small_display_rejected(self):
        for key,value in [('shell',['xiritest','/usr/people/xiritest','/usr/people/xiritest','1234']),
                          ('dimensions','dimensions: 1024x768 pixels'),('greeter_after','')]:
            r=copy.deepcopy(self.r);r['native_login'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):verify_sessions(r)

    def test_missing_retry_or_failed_render_rejected(self):
        for key,value in [('render','RENDER_PASS pixels=8536 mismatches=1'),('greeter_after','')]:
            r=copy.deepcopy(self.r);r['retry'][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):verify_sessions(r)

    def test_catalog_failure_and_rpc_warning_rejected(self):
        r=copy.deepcopy(self.r);r['catalog_launch']['launched_pid']=r['catalog_launch']['initial_pid']
        with self.assertRaises(AssertionError):verify_sessions(r)
        self.r['rpcbind_warning_events']='XIRI_RPC_WATCH_START\nrpcbind: cannot bind\nXIRI_RPC_WATCH_END'
        with self.assertRaises(AssertionError):verify_sessions(self.r)


class TextEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((ROOT/'docs/results/2026-11-05-newport-text-controls.json').read_text())

    def entry(self, name):
        return dict(output=self.record['controls'][name]['output'], metrics=self.record['font_metrics'])

    def test_reproduced_failure_rejected_and_controls_accepted(self):
        with self.assertRaises(AssertionError):verify_fonts(self.entry('original-expanded'))
        verify_fonts(self.entry('software-expanded'))
        verify_fonts(self.entry('shadow-expanded'))

    def test_incomplete_pixels_and_collapsed_font_rejected(self):
        good=self.entry('shadow-expanded')
        incomplete=dict(good, output='\n'.join(good['output'].splitlines()[1:]))
        with self.assertRaises(AssertionError):verify_fonts(incomplete)
        blank=dict(good, output=good['output'].replace('window_ink=425', 'window_ink=0', 1))
        self.assertNotEqual(blank['output'],good['output'])
        with self.assertRaises(AssertionError):verify_fonts(blank)
        collapsed=dict(good, metrics=good['metrics'].replace('ascent=13 descent=5', 'ascent=1 descent=1'))
        with self.assertRaises(AssertionError):verify_fonts(collapsed)


class JobEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.entry = json.loads((ROOT/'docs/results/2026-11-05-irix-terminal-jobs.json').read_text())['job_control']

    def test_real_terminal_sequence_accepted(self):
        verify_job_control(self.entry)

    def test_missing_stop_or_wrong_exit_rejected(self):
        for label in ['native', 'irix']:
            for key, value in [('jobs', 'Running'), ('exit', 124)]:
                entry = copy.deepcopy(self.entry)
                entry['shells'][label]['background_read'][key] = value
                with self.subTest(shell=label, field=key), self.assertRaises(AssertionError):
                    verify_job_control(entry)

    def test_disabled_monitor_or_incomplete_cleanup_rejected(self):
        entry = copy.deepcopy(self.entry)
        entry['shells']['irix']['monitor_enabled_at_start'] = False
        with self.assertRaises(AssertionError):verify_job_control(entry)
        entry = copy.deepcopy(self.entry)
        entry['logout_guard'] = entry['logout_guard'].replace('remaining=0', 'remaining=1')
        with self.assertRaises(AssertionError):verify_job_control(entry)
        entry = copy.deepcopy(self.entry)
        entry['status'] = 'awaiting-logout'
        with self.assertRaises(AssertionError):verify_job_control(entry)

    def test_terminal_failure_is_not_normal_exit(self):
        for old, new in [('exit=0', 'exit=1'), ('stopped=0', 'stopped=1'),
                         ('reason=leader-exit', 'reason=timeout')]:
            entry = copy.deepcopy(self.entry)
            entry['shells']['irix']['terminal_guard'] = entry['shells']['irix']['terminal_guard'].replace(old, new)
            with self.subTest(change=new), self.assertRaises(AssertionError):
                verify_job_control(entry)


if __name__=='__main__':unittest.main()
