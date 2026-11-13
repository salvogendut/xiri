#!/usr/bin/env python3
"""Qualify document actions and per-user editor preferences on a disposable CHD."""
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


class Suite:
    def __init__(self, guest, directory, result):
        self.g, self.d, self.r = guest, directory, result
        self.home = '/usr/people/xiritest'
        self.files = self.home + '/DocumentProbe'

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
        return self.cmd(shlex.join(['/tmp/doc-input', window, *map(str, gesture)]))

    def type(self, command, window='winterm'):
        return self.cmd('/tmp/type "$DISPLAY" '+shlex.quote(window)+' '+shlex.quote(command+'\n'))

    def capture(self, name):
        path = self.d/(name+'.png')
        self.g.monitor('disp compositor gl')
        self.g.monitor('screen wait 500 10000')
        self.g.monitor('screen shot '+str(path))
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        self.r.setdefault('screenshots', {})[path.name] = sha256(path)

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
        self.checkpoint(label)

    def preferences(self, editor):
        # GUI panel saving is an independent observed workflow. This cold
        # regression stages its original shell format through the user's
        # terminal, then tests the runtime's login-time consumption.
        command = ('desktop="$HOME/.desktop-$(hostname)"; mkdir -p "$desktop"; '
                   "printf 'WINEDITOR=\"%s\"\\nexport WINEDITOR\\n' "+shlex.quote(editor)+
                   ' >>"$desktop/desktopenv"')
        self.type(command)
        self.g.wait_for('grep -F '+shlex.quote('WINEDITOR="'+editor+'"')+' '+
                        self.home+'/.desktop-$(hostname)/desktopenv >/dev/null',30)
        self.r['preference_setup'] = 'Original saved shell format, written by each desktop user; GUI panel observations are separate.'

    def document_windows(self):
        self.source = 'xiri-indy:'+self.files+'/Source'
        self.apps = 'xiri-indy:'+self.files+'/Applications'
        self.type('/emul/irix/usr/sbin/fm '+shlex.quote(self.files+'/Source')+
                  ' >"$XIRI_SESSION_DIR/source.log" 2>&1 & '+
                  '/emul/irix/usr/sbin/fm '+shlex.quote(self.files+'/Applications')+
                  ' >"$XIRI_SESSION_DIR/apps.log" 2>&1 &')
        for title in (self.source, self.apps):
            self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null', 60)
        self.ui(self.source,'place',20,100,550,480)
        self.ui(self.apps,'place',640,100,600,480)
        self.ui('winterm','place',10,740,1000,220)

    def open_text(self):
        self.ui(self.source,'double',1,130,125)

    def xedit(self, label):
        self.g.wait_for('xwininfo -root -tree | grep \'"xedit"\' >/dev/null', 60)
        processes=self.read('ps -axww -o uid,pid,ppid,args | grep \'[x]edit\'')
        path=self.files+'/Source/notes with spaces.txt'
        assert re.search(r'^\s*'+str(self.uid)+r'\s+\d+\s+\d+\s+\S*xedit '+re.escape(path)+r'\s*$', processes, re.M), processes
        self.r.setdefault('launches', {})[label]=processes
        self.capture(label)
        self.ui('xedit','click',1,20,10)
        self.g.wait_for('! pgrep -u '+str(self.uid)+' -x xedit >/dev/null',30)

    def unchanged(self, label):
        value=self.read('sha256 -q '+shlex.quote(self.files+'/Source/notes with spaces.txt')).strip()
        assert value==hashlib.sha256(self.payload.encode()).hexdigest(), (label,value)
        self.cmd('test "$(find '+shlex.quote(self.files+'/Source')+' -type f | wc -l)" -eq 1; '+
                 'test "$(find '+shlex.quote(self.files+'/Applications')+' -type l | wc -l)" -eq 1; '+
                 'test "$(find '+shlex.quote(self.files+'/Applications')+' -type f | wc -l)" -eq 0')
        self.r.setdefault('unchanged_documents',{})[label]=value

    def run(self):
        self.r['runtime_hashes']=self.read('sha256 /usr/local/bin/xiri-session '+
            '/usr/local/sbin/xiri-update-filetypes /usr/local/share/xiri/netbsd.ftr '+
            '/emul/irix/usr/lib/filetype/desktop.otr /emul/irix/usr/sbin/fftr')
        for user,uid,editor in [('xiritest',1234,'/usr/freeware/bin/gedit'),
                                ('xiritest2',1237,'/usr/X11R7/bin/xedit')]:
            self.home='/usr/people/'+user;self.files=self.home+'/DocumentProbe';self.uid=uid
            self.payload='Xiri document opening check for '+user+'\nSpaces survive.\n'
            self.login(user)
            dimensions=self.read('xdpyinfo | grep dimensions:')
            assert '1280x1024 pixels' in dimensions
            self.r['dimensions']=dimensions.strip()
            self.type('mkdir -m 700 -p '+shlex.quote(self.files+'/Source')+' '+shlex.quote(self.files+'/Applications')+
                '; printf %s '+shlex.quote(self.payload)+' >'+shlex.quote(self.files+'/Source/notes with spaces.txt')+
                '; ln -s /usr/X11R7/bin/xedit '+shlex.quote(self.files+'/Applications/xedit'))
            self.preferences(editor)
            self.logout(user+'-preferences-saved');self.login(user)
            self.type('printf "%s\\n" "$WINEDITOR" "$HOME" "$(id -u)" >"$XIRI_SESSION_DIR/document-environment"')
            self.g.wait_for('test -s "$job/document-environment"',30)
            environment=self.read('cat "$job/document-environment"').splitlines()
            assert environment==[editor,self.home,str(uid)],environment
            self.r.setdefault('environments',{})[user]=environment
            self.document_windows()
            self.ui(self.apps,'click',1,100,125)
            self.ui(self.source,'cancel-drag',1,130,125,720,125)
            self.cmd('sleep 2; ! pgrep -u '+str(uid)+' -x xedit >/dev/null')
            self.unchanged(user+'-cancel')
            self.ui(self.source,'drag',1,130,125,720,125)
            self.xedit(user+'-native-icon-drop')
            self.unchanged(user+'-native-icon-drop')
            self.open_text()
            if user=='xiritest':
                title='gedit - ['+self.files+'/Source/notes with spaces.txt]'
                self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null',60)
                self.ui(title,'click',1,70,14);self.ui(title,'click',1,100,162)
                self.ui(title,'key','Ctrl+c')
                self.cmd('/tmp/clip-selection get CLIPBOARD STRING /tmp/document-content')
                contents=self.read('cat /tmp/document-content')
                assert contents==self.payload,(contents,self.payload)
                self.r['gedit_exact_content']=dict(bytes=len(self.payload),sha256=hashlib.sha256(contents.encode()).hexdigest())
                self.capture('irix-gedit-document-open');self.ui(title,'key','Ctrl+q')
                self.g.wait_for('! pgrep -u 1234 -x gedit >/dev/null',30)
            else:self.xedit(user+'-native-document-open')
            self.unchanged(user+'-document-open')
            self.logout(user+'-complete')
        self.login('xiritest')
        self.type('printf "%s\\n" "$WINEDITOR" >"$XIRI_SESSION_DIR/document-environment"')
        self.g.wait_for('test -s "$job/document-environment"',30)
        assert self.read('cat "$job/document-environment"').strip()=='/usr/freeware/bin/gedit'
        self.r['first_user_preference_survives_second_user']=True
        self.logout('first-user-recheck')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--local-processes', action='store_true',
        help='For the documented direct Distrobox adapter: terminate recorded local session groups.')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    runs = ROOT/'.work/documents'; runs.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='qualified-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    (directory/'owner.pid').write_text(str(os.getpid())+'\n')
    shutil.copyfile(__file__, directory/'probe-source.py')
    media = directory/'media'; media.mkdir()
    sources = [('lab/clipboard/selection.c', 'clip-selection.c'),
        ('lab/documents/input.c', 'doc-input.c'),
        ('lab/irix-4dwm/type-ready.c', 'type.c')]
    for source, name in sources:
        shutil.copyfile(ROOT/source, media/name)
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
        raise RuntimeError('Document probe interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start(boot=False); lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30); lab.logged_in = True
        suite.cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0; '
            'mount -t cd9660 -o ro /dev/cd0a /cdrom; mkdir /root/documents; cp /cdrom/*.c /root/documents/; cd /root/documents')
        suite.cmd('for n in clip-selection doc-input type; do cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include '
            '"$n.c" -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o /tmp/"$n" || exit; done', 240)
        result['loaded_module'] = suite.read('modstat | grep compat_irix_o32; sha256 '+manifest['irix_module']['path'])
        assert result['module_sha256'] in result['loaded_module']
        assert 'filesys' in result['loaded_module']
        suite.run()
        result['status'] = 'checks-passed'
    except Exception as error:
        result['status'] = 'error'; result['error'] = repr(error)
        try:
            suite.capture('failure')
        except Exception as capture_error:
            result['failure_capture_error'] = repr(capture_error)
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
