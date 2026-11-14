#!/usr/bin/env python3
"""Collect filesystem ABI observations from a disposable, cold-booted CHD."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256
from xiri_lab.kernel_log import KernelLog
from xiri_lab.transfer import archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--suite', choices=('statvfs', 'remove', 'filemeta'), action='append',
                        help='Repeat to select suites; defaults to statvfs and remove.')
    parser.add_argument('--local-processes', action='store_true',
                        help='Terminate recorded local session groups with the direct Distrobox adapter.')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    build = json.loads((bundle/'irix-module-build.json').read_text())
    runs = ROOT/'.work/file-manager'
    runs.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='abi-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    media = directory/'media'
    media.mkdir()
    inputs = {}
    suites = args.suite or ['statvfs', 'remove']
    assert len(set(suites)) == len(suites)
    for suite in suites:
        path = ROOT/('.work/irix-'+suite)/'inputs.tgz'
        reference = json.loads((ROOT/'lab/irix-pathops'/(suite+'-reference.json')).read_text())
        fixtures = reference['build' if suite == 'statvfs' else 'manifest']['files']
        with tarfile.open(path) as payload:
            for name, entry in fixtures.items():
                assert hashlib.file_digest(payload.extractfile(name), 'sha256').hexdigest() == entry['sha256'], name
        shutil.copyfile(path, media/(suite+'.tgz'))
        inputs[suite] = sha256(path)
    probe = load_probe()
    probe.IRIS, probe.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    assert sha256(probe.IRIS) == manifest['pin']['emulator_sha256']
    assert sha256(probe.CI) == manifest['pin']['ci_client_sha256']
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory/'probe.iso', media])
    probe.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', directory/'disk.chd'])
    shutil.copyfile(bundle/manifest['qualification_nvram'], directory/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(directory/'no-tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(directory/'probe.iso'))+'\ncdrom = true\n'
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600),
                    directory, config_text=config)
    launch = lab.launch

    def launch_chd(command, name):
        if name == 'emulator':
            command = list(command)
            command[command.index('--scsi1')+1] = str(directory/'disk.chd')
        return launch(command, name)

    def interrupted(*unused):
        raise RuntimeError('Interrupted')

    lab.launch = launch_chd
    if args.local_processes:
        def terminate(process, name):
            pid = int((directory/(name+'.pid')).read_text())
            try:
                assert pid > 1 and os.getpgid(pid) == pid
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
        lab.terminate = terminate
    (directory/'owner.pid').write_text(str(os.getpid())+'\n')
    signal.signal(signal.SIGTERM, interrupted)
    guest = Guest(lab)
    result = dict(schema=1, status='error', bundle=str(bundle.relative_to(ROOT)),
                  inputs=inputs, base_chd_sha256=manifest['chd_sha256'],
                  module_sha256=build['artifacts']['compat_irix_o32.kmod']['sha256'],
                  script_sha256=sha256(Path(__file__)))
    try:
        lab.start(boot=False)
        lab.wait('login: ', 600)
        lab.send('root')
        lab.wait('xiri-indy# ', 30)
        lab.logged_in = True
        guest.command('ulimit -c 0; umask 022; mount -t cd9660 -o ro /dev/cd0a /cdrom')
        result['module'] = guest.read_text('modstat | grep irix; sysctl kern.securelevel; '
            'sha256 /stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod')
        assert result['module_sha256'] in result['module']
        assert 'exec' in result['module'] and 'filesys' in result['module']
        assert 'kern.securelevel = 1' in result['module']
        if 'statvfs' in suites:
            guest.command('mkdir /tmp/statvfs; cd /tmp/statvfs; tar xzf /cdrom/statvfs.tgz; '
            'chmod 755 . o32-* n32-*; mkdir results denied; chmod 777 results; '
            'echo payload >file; echo denied >denied/file; chmod 000 denied; '
            'ln -s file link; sh run.sh root; su -m xiritest -c "sh /tmp/statvfs/run.sh user"')
            archive(guest, 'cd /tmp/statvfs && tar cf - results', directory/'statvfs.tar')
        for suite in suites:
            if suite not in ('remove', 'filemeta'):
                continue
            guest.command('(set -e; mkdir /tmp/irix-'+suite+'; cd /tmp/irix-'+suite+
                '; tar xzf /cdrom/'+suite+'.tgz; chmod 755 . o32-* n32-*; '
                'sh run.sh xiritest >run.log 2>&1)', 900)
            archive(guest, 'cd /tmp/irix-'+suite+' && tar cf - results', directory/(suite+'.tar'))
        if 'filemeta' in suites:
            result['native_filemeta_control'] = guest.command('(set -e; '
                'for f in /tmp/irix-filemeta/work/*-t-file/node; do '
                'test "$(stat -f "%a|%m" "$f")" = "946684800|946684812"; '
                'stat -f "%N|%u|%g|%Lp|%a|%m" "$f"; done; '
                'for f in /tmp/irix-filemeta/work/*/file; do test "$(cat "$f")" = payload; done; '
                'for f in /tmp/irix-filemeta/work/*-s-existing-file/node; '
                'do test "$(cat "$f")" = existing; done)')
        result['native_control'] = guest.command('/root/irix-desktop/native-o32; test "$?" = 37')
        assert 'XIRI_ABI_PROBE' in result['native_control']
        result['archives'] = {suite+'.tar':sha256(directory/(suite+'.tar')) for suite in suites}
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        if lab.logged_in:
            try:
                result['halt'] = KernelLog(lab, int(manifest['kernel_msgbuf_symbol'], 16)).halt()
            except Exception as error:
                result['halt_error'] = repr(error)
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_unchanged'] = sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
        if not result['clean_shutdown'] or not result['base_unchanged']:
            result['status'] = 'error'
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['status'] == 'observed'


if __name__ == '__main__':
    main()
