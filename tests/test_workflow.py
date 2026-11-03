"""Host-side failure and lifecycle checks; no guest or imported IRIX files needed."""
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from xiri_lab import Guest, sha256
from xiri_lab.workflow import integration_worktree, selected_image, verify_image, build_command


class ShellLab:
    def __init__(self, cwd=None):
        self.cwd = cwd
        self.args = SimpleNamespace(mode='ci')
        self.text = ''
        self.send = object()

    def serial_text(self):
        return self.text

    def command(self, command, timeout):
        # Exercise the actual shell framing, including echoes of delimiter text.
        result = subprocess.run(['sh', '-c', command], capture_output=True, text=True, timeout=timeout, cwd=self.cwd)
        self.text += command+'\n'+result.stdout
        return result.returncode


class GuestTests(unittest.TestCase):
    def test_binary_transfer_and_non_utf8_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)/'data'
            payload = bytes(range(256))*100
            data.write_bytes(payload)
            lab = ShellLab(directory)
            original = lab.send
            guest = Guest(lab)
            self.assertEqual(guest.read('cat '+str(data)), payload)
            self.assertEqual(guest.read_text("printf '\\377'"), '\\xff')
            self.assertIs(lab.send, original)

    def test_command_failure_is_not_a_successful_observation(self):
        with self.assertRaisesRegex(RuntimeError, 'guest command failed.*7'):
            Guest(ShellLab()).command('printf failure; exit 7')

    def test_truncated_transfer_rejected(self):
        lab = ShellLab()
        with patch.object(lab, 'command', return_value=0):
            with self.assertRaisesRegex(RuntimeError, 'transfer frame'):
                Guest(lab).read('printf ok')

    def test_paced_uart_preserves_bytes(self):
        sent = []
        lab = SimpleNamespace(args=SimpleNamespace(mode='ordinary'),
                              serial=SimpleNamespace(sendall=sent.append))
        Guest(lab, pace_seconds=0)
        lab.send('hello')
        lab.send('\x03', newline=False)
        self.assertEqual(b''.join(sent), b'hello\r\x03')

    def test_failed_monitor_capture_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lab = SimpleNamespace(args=SimpleNamespace(mode='ci'), directory=Path(directory),
                                  monitor_command=lambda cmd: 'error: display unavailable')
            with self.assertRaisesRegex(RuntimeError, 'monitor command failed'):
                Guest(lab).capture(Path(directory)/'frame.png')


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = self.root/'bundle'
        (self.bundle/'emulator').mkdir(parents=True)
        (self.bundle/'tftp').mkdir()
        names = ['netbsd-xiri.chd', 'seed-result.json', 'iris.toml', 'copy-ledger.json',
                 'permissions.json', 'emulator/iris', 'emulator/iris-ci', 'tftp/netbsd-XIRI_INDY']
        for name in names:
            (self.bundle/name).write_text(name)
        digest = lambda name: sha256(self.bundle/name)
        self.manifest = dict(status='chd-roundtrip-verified', chd_sha256=digest(names[0]),
            source_result_sha256=digest(names[1]), config_sha256=digest(names[2]),
            copy_ledger_sha256=digest(names[3]), permission_manifest_sha256=digest(names[4]),
            emulator_files={name:digest(name) for name in names[5:7]},
            pin=dict(emulator_sha256=digest(names[5]), ci_client_sha256=digest(names[6]),
                     boot_kernel_sha256=digest(names[7])))
        (self.root/'qualification.json').write_text('{}')
        self.pointer = dict(bundle='bundle', chd_sha256=self.manifest['chd_sha256'],
                            qualification='qualification.json', qualification_sha256=sha256(self.root/'qualification.json'))
        (self.root/'pointer.json').write_text(json.dumps(self.pointer))
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))

    def test_user_nvram_changes_are_preserved(self):
        state = self.bundle/'nvram-graphics.bin'
        state.write_bytes(b'my current manual session')
        verify_image(self.root, self.pointer, self.bundle, self.manifest)
        self.assertEqual(state.read_bytes(), b'my current manual session')

    def test_tampered_kernel_rejected(self):
        (self.bundle/'tftp/netbsd-XIRI_INDY').write_text('different kernel')
        with self.assertRaisesRegex(ValueError, 'Artifact hash mismatch'):
            verify_image(self.root, self.pointer, self.bundle, self.manifest)

    def test_module_build_manifest_is_an_immutable_artifact(self):
        path = self.bundle/'irix-module-build.json'
        path.write_text('matching module build')
        self.manifest['pin'].update(module_build_manifest='module/build.json',
                                    module_build_manifest_sha256=sha256(path))
        verify_image(self.root, self.pointer, self.bundle, self.manifest)
        path.write_text('another module build')
        with self.assertRaisesRegex(ValueError, 'Artifact hash mismatch'):
            verify_image(self.root, self.pointer, self.bundle, self.manifest)

    def test_emulator_pin_disagreement_rejected(self):
        self.manifest['pin']['emulator_sha256'] = 'different build'
        with self.assertRaisesRegex(ValueError, 'emulator hashes disagree'):
            verify_image(self.root, self.pointer, self.bundle, self.manifest)

    def test_missing_artifact_rejected(self):
        (self.bundle/'emulator/iris-ci').unlink()
        with self.assertRaises(FileNotFoundError):
            verify_image(self.root, self.pointer, self.bundle, self.manifest)

    def test_image_pointer_disagreement_rejected(self):
        self.pointer['chd_sha256'] = 'wrong image'
        (self.root/'pointer.json').write_text(json.dumps(self.pointer))
        with self.assertRaisesRegex(ValueError, 'pointer and bundle disagree'):
            selected_image(self.root, dict(image_pointer='pointer.json'))

    def test_seed_reuse_keeps_changed_manual_nvram(self):
        output = self.root/'seed'
        output.mkdir()
        (output/'disk.raw').write_bytes(b'previously extracted raw disk')
        self.manifest['source_raw_sha256'] = sha256(output/'disk.raw')
        self.manifest['manual_nvram_sha256'] = 'original prepared state'
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
        (self.bundle/'nvram.bin').write_bytes(b'serial console state')
        (self.bundle/'nvram-graphics.bin').write_bytes(b'user manual state')
        subprocess.run([sys.executable, str(ROOT/'scripts/prepare-xiri-seed.py'),
                        str(self.bundle), '--output-directory', str(output)],
                       check=True, capture_output=True)
        self.assertEqual((output/'disk.raw').read_bytes(), b'previously extracted raw disk')
        self.assertEqual((self.bundle/'nvram-graphics.bin').read_bytes(), b'user manual state')
        self.assertFalse((output/'nvram-graphics.bin').exists())
        self.assertEqual((output/'nvram.bin').read_bytes(), b'serial console state')

    def test_new_image_cannot_be_created_inside_manual_bundle(self):
        from xiri_lab.workflow import main
        (self.root/'config').mkdir()
        (self.root/'config/development.json').write_text(json.dumps(dict(
            schema=1, build_jobs=2, image_pointer='pointer.json')))
        with patch('xiri_lab.workflow.ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'outside the selected manual bundle'):
                main(['image', '--seed-run', str(self.root/'seed'),
                      '--output', str(self.bundle/'new-image'), '--dry-run'])
        self.assertFalse((self.bundle/'new-image').exists())

    def test_build_finds_branch_owner_without_switching_shared_checkout(self):
        repo = self.root/'shared'; owner = self.root/'branch owner'
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL, text=True).strip()
        repo.mkdir()
        git('init', '-b', 'other-task')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'base')
        git('worktree', 'add', '-b', 'xiri', str(owner))
        self.assertEqual(integration_worktree(repo, 'xiri'), owner)
        self.assertEqual(git('branch', '--show-current'), 'other-task')
        config = dict(netbsd_checkout='shared', integration_branch='xiri', build_jobs=2,
                      kernel_config='frame.conf', kernel_arch='mips64eb')
        command, env = build_command(self.root, config, 'netbsd')
        self.assertEqual(env['XIRI_NETBSD_SOURCE_DIR'], str(owner))
        (self.root/'.work/builds').mkdir(parents=True)
        (self.root/'.work/builds/netbsd').symlink_to(self.bundle, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            build_command(self.root, config, 'netbsd')


class RpcLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('image_qualifier', ROOT/'scripts/qualify-xiri-image.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.verify = staticmethod(module.verify_rpc_warnings)

    def test_rotation_does_not_create_a_false_warning(self):
        self.verify(dict(rpcbind_warning_check='RPC_BIND_WARNINGS_BEFORE=2 AFTER=0 XIRI_RC=0',
                         rpcbind_warning_events='XIRI_RPC_WATCH_START\nordinary message\nXIRI_RPC_WATCH_END'))

    def test_new_warning_is_detected_even_if_historical_count_falls(self):
        with self.assertRaises(AssertionError):
            self.verify(dict(rpcbind_warning_check='RPC_BIND_WARNINGS_BEFORE=2 AFTER=1 XIRI_RC=0',
                rpcbind_warning_events='XIRI_RPC_WATCH_START\nrpcbind: cannot bind 127.0.0.1\nXIRI_RPC_WATCH_END'))

    def test_incomplete_watch_rejected(self):
        with self.assertRaises(AssertionError):
            self.verify(dict(rpcbind_warning_check='XIRI_RC=0',rpcbind_warning_events='XIRI_RPC_WATCH_START'))

    def test_historical_observations_keep_their_original_rule(self):
        self.verify(dict(rpcbind_warning_check='RPC_BIND_WARNINGS_BEFORE=2 AFTER=2 XIRI_RC=0'))
        with self.assertRaises(AssertionError):
            self.verify(dict(rpcbind_warning_check='RPC_BIND_WARNINGS_BEFORE=2 AFTER=0 XIRI_RC=0'))


class ModuleImageTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('module_image_qualifier', ROOT/'scripts/qualify-xiri-image.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.verify = module.verify_irix_module
        self.pin = dict(module_build_manifest='build.json', module_build_manifest_sha256='build-hash',
                        native_kernel_sha256='native-hash', boot_kernel_sha256='boot-hash')
        self.build = dict(artifacts={name:dict(sha256=digest) for name, digest in [
            ('netbsd', 'native-hash'), ('netbsd.boot', 'boot-hash'), ('compat_irix_o32.kmod', 'module-hash')]})
        evidence = dict(name='compat_irix_o32', path='/stand/sgimips/test/modules/compat_irix_o32/compat_irix_o32.kmod',
                        sha256='module-hash', modstat='compat_irix_o32 exec filesys 0 - exec_elf32,compat_netbsd32\n', securelevel=1,
                        build_manifest='build.json', build_manifest_sha256='build-hash')
        self.seed = dict(irix_module=dict(evidence), installed_files={evidence['path']:'module-hash',
                         '/etc/modules.conf':'modules-conf-hash', '/etc/rc.conf':'rc-conf-hash'})
        self.result = dict(irix_module=dict(evidence))

    def test_matching_module_boot_passes(self):
        self.verify(self.pin, self.seed, self.build, self.result)

    def test_mismatched_kernel_or_module_rejected(self):
        for artifact in ['netbsd', 'netbsd.boot', 'compat_irix_o32.kmod']:
            with self.subTest(artifact=artifact):
                build = json.loads(json.dumps(self.build))
                build['artifacts'][artifact]['sha256'] = 'wrong'
                with self.assertRaises(AssertionError):
                    self.verify(self.pin, self.seed, build, self.result)

    def test_absent_builtin_or_weakened_boot_rejected(self):
        for changes in [dict(modstat=''), dict(modstat='compat_irix_o32 exec builtin 0 - -\n'),
                        dict(securelevel=0), dict(sha256='wrong')]:
            with self.subTest(changes=changes):
                result = dict(irix_module={**self.result['irix_module'], **changes})
                with self.assertRaises(AssertionError):
                    self.verify(self.pin, self.seed, self.build, result)

    def test_missing_boot_configuration_rejected(self):
        del self.seed['installed_files']['/etc/modules.conf']
        with self.assertRaises(AssertionError):
            self.verify(self.pin, self.seed, self.build, self.result)


class LifecycleTests(unittest.TestCase):
    def test_termination_waits_for_child_cleanup_and_records_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            child = path/'child.py'
            (path/'grandchild.py').write_text("import signal,time\nfrom pathlib import Path\n"
                "def stop(*args):\n Path('grandchild-cleaned').touch()\n raise SystemExit(0)\n"
                "signal.signal(signal.SIGINT,stop)\nPath('grandchild-ready').touch()\nwhile True: time.sleep(.1)\n")
            child.write_text("import signal,subprocess,sys,time\nfrom pathlib import Path\n"
                "grandchild=subprocess.Popen([sys.executable,'grandchild.py'])\n"
                "def stop(*args):\n grandchild.wait(timeout=3)\n time.sleep(.3)\n Path('cleaned').write_text('yes')\n raise SystemExit(0)\n"
                "signal.signal(signal.SIGINT,stop)\n"
                "while not Path('grandchild-ready').exists(): time.sleep(.05)\n"
                "Path('ready').touch()\nwhile True: time.sleep(.1)\n")
            parent = path/'parent.py'
            parent.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(ROOT/'scripts'))+')\n'
                'from xiri_lab.workflow import run_step\n'
                'try: run_step(Path.cwd(),Path.cwd(),"command",[sys.executable,"child.py"])\n'
                'except KeyboardInterrupt: raise SystemExit(130)\n')
            with (path/'parent.log').open('w') as log:
                process = subprocess.Popen([sys.executable,str(parent)], cwd=path, stdout=log, stderr=log)
                try:
                    deadline = time.monotonic()+10
                    while not (path/'ready').exists() and process.poll() is None and time.monotonic()<deadline:
                        time.sleep(.05)
                    self.assertTrue((path/'ready').exists())
                    process.send_signal(signal.SIGTERM)
                    self.assertEqual(process.wait(timeout=10), 130)
                    self.assertEqual((path/'cleaned').read_text(), 'yes')
                    self.assertTrue((path/'grandchild-cleaned').exists())
                    result = json.loads((path/'command.json').read_text())
                    self.assertEqual(result['status'], 'interrupted')
                    self.assertEqual(result['exit_status'], 0)
                finally:
                    if process.poll() is None:
                        process.kill(); process.wait()


if __name__ == '__main__':
    unittest.main()
