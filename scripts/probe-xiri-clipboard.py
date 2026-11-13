#!/usr/bin/env python3
"""Qualify text selections between native and IRIX clients on a disposable CHD."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256
from xiri_lab.kernel_log import KernelLog


FIXTURES = {
    'native-line': b'NETBSD_TO_IRIX_13Nov',
    'irix-line': b'IRIX_TO_NETBSD_13Nov',
    'clipboard-line': b'NATIVE_CLIPBOARD_2026',
    'editor': b'IRIX editor source: line one\nline two with a tab\tend\n',
    'short': b'NATIVE clipboard line one\nline two\twith tab\n',
    'latin1': b'Latin1: caf\xe9, cr\xe8me, \xa3 42\n',
    'large': b'Clipboard line with NetBSD and IRIX\t0123456789 abcdefghijklmnopqrstuvwxyz\n' * 1536,
    'second-user': b'SECOND_USER_SELECTION',
    'native-user': b'NATIVE_USER_SELECTION',
}


class Suite:
    def __init__(self, guest, directory, result):
        self.g, self.d, self.r = guest, directory, result
        self.home = '/usr/people/xiritest'
        self.files = self.home + '/xiri-clipboard-probe'

    def checkpoint(self, label):
        self.r['checkpoint'] = label
        (self.d/'checkpoint.json').write_text(json.dumps(self.r, indent=2)+'\n')
        print(label, flush=True)

    def cmd(self, command, timeout=120):
        output = self.g.command(command, timeout)
        with (self.d/'commands.log').open('a') as log:
            log.write(command+'\n'+output+'\n')
        return output

    def read(self, command):
        return self.g.read_text(command)

    def ui(self, window, *gesture):
        return self.cmd(shlex.join(['/tmp/clip-input', window, *map(str, gesture)]))

    def type(self, command, window='winterm'):
        return self.cmd('/tmp/type "$DISPLAY" '+shlex.quote(window)+' '+shlex.quote(command+'\n'))

    def capture(self, name):
        path = self.d/(name+'.png')
        self.g.monitor('disp compositor gl')
        self.g.monitor('screen wait 500 10000')
        self.g.monitor('screen shot '+str(path))
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        self.r.setdefault('screenshots', {})[path.name] = sha256(path)

    def state(self, label, empty=False):
        text = self.read('/tmp/clip-selection state')
        owners = {name:int(value, 16) for name,value in re.findall(r'^(\S+) owner=0x([0-9a-f]+)$', text, re.M)}
        buffers = {name:int(value) for name,value in re.findall(r'^(CUT_BUFFER\d) bytes=(\d+)$', text, re.M)}
        assert len(owners) == 3 and len(buffers) == 8, text
        if empty:
            assert not any(owners.values()) and not any(buffers.values()), text
        state = dict(owners=owners, cut_buffer_bytes=buffers)
        self.r.setdefault('states', {})[label] = state
        return state

    def compare(self, path, fixture, label):
        expected = hashlib.sha256(FIXTURES[fixture]).hexdigest()
        # Wait for the actual paste/save to complete, not just XTest delivery.
        self.g.wait_for('cmp '+shlex.quote(path)+' /cdrom/'+fixture+'.txt >/dev/null 2>&1', 30)
        actual = self.read('sha256 -q '+shlex.quote(path)).strip()
        assert actual == expected, (label, actual, expected)
        self.r.setdefault('transfers', {})[label] = dict(bytes=len(FIXTURES[fixture]), sha256=actual, matched=True)

    def get(self, selection, target, name):
        path = '/tmp/'+name
        output = self.cmd(shlex.join(['/tmp/clip-selection', 'get', selection, target, path]))
        observation = re.search(r'received type=(\S+) format=(\d+) items=(\d+) chunks=(\d+) incr=(\d+)', output)
        assert observation, output
        typ, fmt, count, chunks, incr = observation.groups()
        self.r.setdefault('conversions', {})[name] = dict(selection=selection, requested=target,
            returned=typ, format=int(fmt), items=int(count), chunks=int(chunks), incremental=bool(int(incr)))
        return path

    def server_auth(self):
        self.cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for(i=1;i<NF;i++)if($i=="-auth")print $(i+1)}\'); '
            'export XAUTHORITY; test -s "$XAUTHORITY"')

    def greeter(self):
        self.server_auth()
        self.g.wait_for('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null', 120)

    def login(self, user):
        self.greeter()
        home = '/home/netbsdtest' if user == 'netbsdtest' else '/usr/people/'+user
        self.cmd('rm -f '+home+'/.xsession-errors')
        # Only the public credentials of the selected disposable lab image.
        for value in ('key type '+user, 'key Return', 'key type '+user, 'key Return'):
            self.g.monitor(value)
        if user == 'netbsdtest':
            self.g.wait_for("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null", 120)
            self.server_auth()
            self.g.wait_for('xwininfo -root -tree | grep \'"UXTerm"\' >/dev/null', 120)
            tree = self.read('xwininfo -root -tree')
            terminal = re.search(r'"([^"\n]+)": \("[^"\n]*" "UXTerm"\)', tree)
            assert terminal, tree
            self.native_terminal = terminal[1]
            return
        self.g.wait_for('grep -q "Logs: " '+home+'/.xsession-errors', 120)
        self.cmd('job=$(sed -n "s/.*Logs: //p" '+home+'/.xsession-errors | head -1); '
            'XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
            'test "$XAUTHORITY" != default || XAUTHORITY='+home+'/.Xauthority; '
            'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')
        self.g.wait_for('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
        self.g.wait_for('xwininfo -root -tree | grep \'"Icon Catalog:\' >/dev/null', 120)
        self.r.setdefault('identities', {})[user] = self.read('cat "$job/identity"')

    def logout(self, label):
        self.cmd('oldjob=$job; touch "$job/logout"')
        self.greeter()
        self.r.setdefault('logout_logs', {})[label] = self.read('cat "$oldjob/guard.log"')
        assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ', self.r['logout_logs'][label])
        self.state(label, empty=True)
        self.checkpoint(label)

    def select_all(self):
        # Original gedit 0.9.7 has Edit > Select All, with no Ctrl+A accelerator.
        self.ui(self.editor, 'click', 1, 70, 14)
        self.ui(self.editor, 'click', 1, 100, 162)

    def paste_save(self, fixture, label):
        self.cmd('xprop -id '+self.editor+' WM_NAME > /tmp/clipboard-title-before')
        self.ui(self.editor, 'key', 'Ctrl+v')
        if fixture == 'large':
            self.g.wait_for('grep -q "INCR complete" '+self.files+'/large-owner.log', 45)
        self.g.wait_for('xprop -id '+self.editor+' WM_NAME > /tmp/clipboard-title-after && '
            '! cmp -s /tmp/clipboard-title-before /tmp/clipboard-title-after', 30)
        self.r.setdefault('modified_titles', {})[label] = self.read('cat /tmp/clipboard-title-after').strip()
        self.ui(self.editor, 'key', 'Ctrl+s')
        self.compare(self.files+'/editor.txt', fixture, label)

    def copy_get(self, fixture, label):
        self.select_all()
        self.ui(self.editor, 'key', 'Ctrl+c')
        self.compare(self.get('CLIPBOARD', 'STRING', label), fixture, label)

    def run(self):
        self.login('xiritest')
        self.state('first-login', empty=True)
        self.r['display'] = self.read('xdpyinfo | grep dimensions:').strip()
        assert '1280x1024 pixels' in self.r['display']
        self.r['versions'] = self.read('/usr/X11R7/bin/xterm -version; cc --version | head -1')
        self.type('mkdir -m 700 "$HOME/xiri-clipboard-probe"; cp /cdrom/editor.txt "$HOME/xiri-clipboard-probe/editor.txt"')
        self.type('/usr/freeware/bin/gedit "$HOME/xiri-clipboard-probe/editor.txt" > "$HOME/xiri-clipboard-probe/gedit.log" 2>&1 &')
        self.type('/usr/X11R7/bin/xterm -T ClipNative -geometry 60x12+30+100 -fn fixed -e /bin/sh /cdrom/native-source.sh &')
        self.g.wait_for('xwininfo -root -tree | grep \'"ClipNative"\' >/dev/null', 90)
        self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"gedit - ['+self.files+'/editor.txt')+' >/dev/null', 90)
        tree = self.read('xwininfo -root -tree')
        match = re.search(r'(0x[0-9a-f]+) "gedit - \['+re.escape(self.files)+r'/editor.txt\]"', tree)
        assert match, tree
        self.editor = match[1]  # The title changes when the file is modified.

        self.type('stty -echo; cat > "$HOME/xiri-clipboard-probe/native-to-winterm"; stty echo')
        self.ui('ClipNative', 'drag', 3, 6, 2+6*len(FIXTURES['native-line']), 6)
        self.compare(self.get('PRIMARY', 'STRING', 'native-primary'), 'native-line', 'native-primary')
        self.r.setdefault('targets', {})['xterm'] = self.read('cat '+self.get('PRIMARY', 'TARGETS', 'native-targets')).splitlines()
        self.ui('winterm', 'click', 2, 300, 300)
        self.ui('winterm', 'key', 'Ctrl+d'); self.ui('winterm', 'key', 'Ctrl+d')
        self.compare(self.files+'/native-to-winterm', 'native-line', 'native-to-winterm')

        self.type('/usr/X11R7/bin/xterm -T ClipNativeSink -geometry 60x12+600+80 -fn fixed -e /bin/sh /cdrom/native-sink.sh "$HOME/xiri-clipboard-probe" &')
        self.g.wait_for('xwininfo -root -tree | grep \'"ClipNativeSink"\' >/dev/null', 90)
        self.type('printf "\\033[2J\\033[H"; cat /cdrom/irix-line.txt; printf "\\n"')
        self.ui('winterm', 'drag', 22, 8, 22+11*len(FIXTURES['irix-line']), 8)
        self.compare(self.get('PRIMARY', 'STRING', 'irix-primary'), 'irix-line', 'irix-primary')
        self.r['targets']['winterm'] = self.read('cat '+self.get('PRIMARY', 'TARGETS', 'irix-targets')).splitlines()
        self.ui('ClipNativeSink', 'click', 2, 80, 80)
        self.ui('ClipNativeSink', 'key', 'Ctrl+d'); self.ui('ClipNativeSink', 'key', 'Ctrl+d')
        self.compare(self.files+'/winterm-to-native', 'irix-line', 'winterm-to-native')
        self.checkpoint('terminal-primary-both-directions')

        self.copy_get('editor', 'gedit-original-copy')
        self.r['targets']['gedit'] = self.read('cat '+self.get('CLIPBOARD', 'TARGETS', 'gedit-targets')).splitlines()
        for fixture in ('short', 'large', 'latin1'):
            chunk = 1024 if fixture == 'large' else 4096
            self.type('/tmp/clip-selection serve CLIPBOARD STRING /cdrom/'+fixture+'.txt '+str(chunk)+
                ' > "$HOME/xiri-clipboard-probe/'+fixture+'-owner.log" 2>&1 &')
            self.paste_save(fixture, fixture+'-native-to-irix')
            self.copy_get(fixture, fixture+'-irix-to-native')
            self.r.setdefault('owner_logs', {})[fixture] = self.read('cat '+self.files+'/'+fixture+'-owner.log')
            if fixture == 'large':
                assert 'INCR complete' in self.r['owner_logs'][fixture]
                assert self.r['conversions']['large-irix-to-native']['incremental']
            self.checkpoint('clipboard-'+fixture)
        output = self.cmd('/tmp/clip-selection get CLIPBOARD UTF8_STRING /tmp/unexpected-utf8; rc=$?; echo UTF8_RC=$rc; test "$rc" -eq 5')
        assert 'UTF8_RC=5' in output
        self.r['gedit_utf8_string'] = 'refused (no conversion advertised)'

        self.type('/usr/X11R7/bin/xterm -T ClipboardNative -geometry 60x12+650+500 -fn fixed '
            '-xrm '+shlex.quote('*selectToClipboard: true')+' -e /bin/sh /cdrom/native-clipboard.sh "$HOME/xiri-clipboard-probe" &')
        self.g.wait_for('xwininfo -root -tree | grep \'"ClipboardNative"\' >/dev/null', 90)
        self.ui('ClipboardNative', 'drag', 3, 6, 2+6*len(FIXTURES['clipboard-line']), 6)
        self.compare(self.get('CLIPBOARD', 'STRING', 'xterm-clipboard'), 'clipboard-line', 'native-xterm-clipboard')
        self.type('printf "\\033[2J\\033[H"; cat /cdrom/irix-line.txt; printf "\\n"')
        self.ui('winterm', 'drag', 22, 8, 22+11*len(FIXTURES['irix-line']), 8)
        self.compare(self.get('PRIMARY', 'STRING', 'independent-primary'), 'irix-line', 'independent-primary')
        self.compare(self.get('CLIPBOARD', 'STRING', 'independent-clipboard'), 'clipboard-line', 'independent-clipboard')
        self.paste_save('clipboard-line', 'xterm-clipboard-to-gedit')
        self.copy_get('clipboard-line', 'gedit-copy-for-xterm')
        self.ui('ClipboardNative', 'click', 2, 80, 80)
        self.ui('ClipboardNative', 'key', 'Ctrl+d'); self.ui('ClipboardNative', 'key', 'Ctrl+d')
        self.compare(self.files+'/clipboard-to-native', 'clipboard-line', 'gedit-clipboard-to-xterm')
        self.capture('clipboard-native-irix')
        self.ui(self.editor, 'key', 'Ctrl+q')
        self.g.wait_for('! xwininfo -root -tree | grep -F '+shlex.quote('"gedit - [')+' >/dev/null', 45)
        state = self.state('source-closed')
        assert state['owners']['CLIPBOARD'] == 0
        self.cmd('/tmp/clip-selection get CLIPBOARD STRING /tmp/after-exit; rc=$?; test "$rc" -eq 4')
        self.checkpoint('clipboard-ui-and-source-exit')

        # Keep both an owned clipboard and a legacy cut buffer live for logout.
        self.type('/tmp/clip-selection serve CLIPBOARD STRING /cdrom/short.txt 4096 > "$HOME/xiri-clipboard-probe/logout-owner.log" 2>&1 &')
        state = self.state('before-logout')
        assert state['owners']['CLIPBOARD'] and state['cut_buffer_bytes']['CUT_BUFFER0']
        self.logout('first-user-logout')
        self.login('xiritest2'); self.state('second-user-login', empty=True)
        self.type('printf "\\033[2J\\033[H"; cat /cdrom/second-user.txt; printf "\\n"')
        self.ui('winterm', 'drag', 22, 8, 22+11*len(FIXTURES['second-user']), 8)
        self.compare(self.get('PRIMARY', 'STRING', 'second-user-primary'), 'second-user', 'second-user-primary')
        self.logout('second-user-logout')

        self.login('netbsdtest'); self.state('native-user-login', empty=True)
        self.type('(id -un; id -u; echo "$HOME"; pwd) > "$HOME/xiri-clipboard-proof"; '
            '/usr/X11R7/bin/xterm -T ClipNativeUser -geometry 60x12+200+150 -fn fixed '
            '-e /bin/sh /cdrom/native-user.sh &', self.native_terminal)
        self.g.wait_for('xwininfo -root -tree | grep \'"ClipNativeUser"\' >/dev/null', 90)
        identity = self.read('cat /home/netbsdtest/xiri-clipboard-proof').splitlines()
        assert identity == ['netbsdtest', '1236', '/home/netbsdtest', '/home/netbsdtest'], identity
        self.r['identities']['netbsdtest'] = identity
        self.ui('ClipNativeUser', 'drag', 3, 6, 2+6*len(FIXTURES['native-user']), 6)
        self.compare(self.get('PRIMARY', 'STRING', 'native-user-primary'), 'native-user', 'native-user-primary')
        self.capture('clipboard-native-user')
        self.g.wait_for("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' > /tmp/clipboard-ctwm.pid && "
            'test "$(wc -l < /tmp/clipboard-ctwm.pid)" -eq 1', 30)
        pid = int(self.read('cat /tmp/clipboard-ctwm.pid').strip())
        self.type('(sleep 2; kill -TERM '+str(pid)+') &', self.native_terminal)
        self.greeter(); self.state('native-user-logout', empty=True)
        self.g.wait_for('! pgrep -u 1236', 30)
        self.checkpoint('all-users-and-logouts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--local-processes', action='store_true',
        help='For the documented direct Distrobox adapter: terminate recorded local session groups.')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    runs = ROOT/'.work/clipboard'; runs.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='qualified-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    (directory/'owner.pid').write_text(str(os.getpid())+'\n')
    shutil.copyfile(__file__, directory/'probe-source.py')
    media = directory/'media'; media.mkdir()
    for name, data in FIXTURES.items():
        (media/(name+'.txt')).write_bytes(data)
    sources = [('lab/clipboard/selection.c', 'clip-selection.c'), ('lab/clipboard/input.c', 'clip-input.c'),
        ('lab/irix-4dwm/type-ready.c', 'type.c')]
    for source, name in sources:
        shutil.copyfile(ROOT/source, media/name)
    (media/'native-source.sh').write_text('printf "\\033[2J\\033[H"; cat /cdrom/native-line.txt; printf "\\n"; exec sleep 1800\n')
    (media/'native-user.sh').write_text('cat /cdrom/native-user.txt; printf "\\n"; exec sleep 1800\n')
    (media/'native-sink.sh').write_text('stty -echo; cat > "$1/winterm-to-native"; printf "NATIVE_PASTE_DONE\\n"; exec sleep 1800\n')
    (media/'native-clipboard.sh').write_text('cat /cdrom/clipboard-line.txt; printf "\\n"; stty -echo; cat > "$1/clipboard-to-native"; printf "CLIPBOARD_PASTE_DONE\\n"; exec sleep 1800\n')
    probe = load_probe()
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory/'probe.iso', media])
    probe.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', directory/'disk.chd'])
    shutil.copyfile(bundle/manifest['qualification_nvram'], directory/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"', 'tftp_dir = '+json.dumps(str(directory/'no-tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(directory/'probe.iso'))+'\ncdrom = true\n'
    probe.IRIS, probe.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    for name in ('emulator/iris', 'emulator/iris-ci'):
        assert sha256(bundle/name) == manifest['emulator_files'][name]
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), directory, config_text=config)
    launch = lab.launch
    def launch_chd(command, name):
        if name == 'emulator':
            command = list(command); command[command.index('--scsi1')+1] = str(directory/'disk.chd')
        return launch(command, name)
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
    guest = Guest(lab)
    result = dict(schema=1, status='running', bundle=str(bundle.relative_to(ROOT)),
        base_chd_sha256=manifest['chd_sha256'], module_sha256=manifest['irix_module']['sha256'],
        emulator_sha256=sha256(probe.IRIS), probe_sha256=sha256(Path(__file__)),
        media_inputs={p.name:sha256(p) for p in sorted(media.iterdir())})
    suite = Suite(guest, directory, result)
    def interrupted(*unused):
        raise RuntimeError('Clipboard probe interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start(boot=False); lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30); lab.logged_in = True
        suite.cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0; '
            'mount -t cd9660 -o ro /dev/cd0a /cdrom; mkdir /root/clipboard; cp /cdrom/*.c /root/clipboard/; cd /root/clipboard')
        suite.cmd('for n in clip-selection clip-input type; do cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include '
            '"$n.c" -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o /tmp/"$n" || exit; done', 240)
        result['loaded_module'] = suite.read('modstat | grep compat_irix_o32; sha256 '+manifest['irix_module']['path'])
        assert result['module_sha256'] in result['loaded_module']
        assert 'filesys' in result['loaded_module']
        suite.run()
        result['status'] = 'checks-passed'
    except Exception as error:
        result['status'] = 'error'; result['error'] = repr(error)
        raise
    finally:
        try:
            if lab.logged_in:
                try:
                    result['halt'] = KernelLog(lab, int(manifest['kernel_msgbuf_symbol'], 16)).halt()
                except Exception as error:
                    result['halt_error'] = repr(error)
        finally:
            try:
                lab.close()
            finally:
                result['clean_shutdown'] = lab.clean_shutdown
                result['base_unchanged'] = sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
                if result['status'] == 'checks-passed' and result['clean_shutdown'] and result['base_unchanged']:
                    result['status'] = 'qualified'
                else:
                    result['status'] = 'error'
                (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['status'] == 'qualified'


if __name__ == '__main__':
    main()
