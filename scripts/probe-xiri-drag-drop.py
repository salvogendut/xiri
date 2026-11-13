#!/usr/bin/env python3
"""Qualify real File Manager drops on a disposable, authenticated desktop."""
import hashlib
import importlib.util
from pathlib import Path
import shlex
import struct
import zlib

from xiri_lab import ROOT, sha256

spec = importlib.util.spec_from_file_location('documents', ROOT/'scripts/probe-xiri-documents.py')
documents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(documents)


def image_fixture():
    def chunk(kind, data):
        return struct.pack('!I', len(data))+kind+data+struct.pack('!I', zlib.crc32(kind+data))
    row = b'\0'+b''.join(bytes((220, 40, 40) if x < 32 else
        (40, 200, 80) if x < 64 else (40, 70, 230)) for x in range(96))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!IIBBBBB', 96, 64, 8, 2, 0, 0, 0))+
            chunk(b'IDAT', zlib.compress(row*64))+chunk(b'IEND', b''))


class Suite(documents.Suite):
    def wait_window(self, title, timeout=120):
        self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null', timeout)

    def fm(self, folder):
        path = self.files+'/'+folder
        self.type('/emul/irix/usr/sbin/fm '+shlex.quote(path)+
                  ' >"$XIRI_SESSION_DIR/drop-'+folder+'.log" 2>&1 &')
        title = 'xiri-indy:'+path
        self.wait_window(title)
        return title

    def exact_text(self, title, label):
        self.wait_window(title)
        self.ui(title, 'click', 1, 70, 14)
        self.ui(title, 'click', 1, 100, 162)  # Edit -> Select all, original gedit.
        self.ui(title, 'key', 'Ctrl+c')
        self.cmd('/tmp/clip-selection get CLIPBOARD STRING /tmp/drop-content')
        content = self.read('cat /tmp/drop-content')
        assert content == self.payload, (content, self.payload)
        self.r.setdefault('exact_text', {})[label] = dict(bytes=len(content),
            sha256=hashlib.sha256(content.encode()).hexdigest())
        self.capture(label)
        self.ui(title, 'key', 'Ctrl+q')
        self.g.wait_for('! pgrep -u '+str(self.uid)+' -x gedit >/dev/null', 30)

    def check_source(self, label):
        value = self.read('sha256 -q '+shlex.quote(self.files+'/Text/notes with spaces.txt')).strip()
        assert value == hashlib.sha256(self.payload.encode()).hexdigest()
        self.cmd('test "$(find '+shlex.quote(self.files+'/Text')+' -type f | wc -l)" -eq 1')
        self.r.setdefault('source_unchanged', {})[label] = value

    def run(self):
        self.r['drag_probe_sha256'] = sha256(Path(__file__))
        self.r['runtime_hashes'] = self.read('sha256 /usr/local/libexec/xiri/drop-bridge '
            '/usr/local/libexec/xiri/desktop-clients.sh /usr/local/bin/xiri-session '
            '/usr/local/share/xiri/applications.ftr /emul/irix/usr/lib/filetype/desktop.otr')
        for user, uid in [('xiritest', 1234), ('xiritest2', 1237)]:
            self.home = '/usr/people/'+user
            self.files = self.home+'/DragProbe'
            self.uid = uid
            self.payload = 'Xiri running-window drop for '+user+'\nSpaces survive.\n'
            self.login(user)
            self.cmd('test -s "$job/drop-bridge.pid"; kill -0 "$(cat "$job/drop-bridge.pid")"; '
                     'test "$(pgrep -u '+str(uid)+' -f \'^/usr/local/libexec/xiri/drop-bridge( |$)\' | wc -l)" -eq 1')
            self.r.setdefault('helper_identities', {})[user] = self.read(
                'ps -p "$(cat "$job/drop-bridge.pid")" -o uid,pid,ppid,args; cat "$job/drop-bridge.err"')
            self.type('mkdir -m 700 -p "$HOME/DragProbe/Text" "$HOME/DragProbe/Applications"; '
                'printf %s '+shlex.quote(self.payload)+' >"$HOME/DragProbe/Text/notes with spaces.txt"; '
                'ln -s /usr/freeware/bin/gedit "$HOME/DragProbe/Applications/gedit"')
            source = self.fm('Text')
            apps = self.fm('Applications')
            self.ui(source, 'place', 20, 100, 550, 480)
            self.ui(apps, 'place', 640, 100, 600, 480)
            self.ui('winterm', 'place', 10, 740, 1000, 220)
            self.ui(apps, 'click', 1, 100, 125)
            self.ui(source, 'drag', 1, 130, 125, 720, 125)
            self.exact_text('gedit - ['+self.files+'/Text/notes with spaces.txt]', user+'-gedit-icon')
            self.check_source(user+'-gedit-icon')
            self.type('/usr/freeware/bin/gedit >"$XIRI_SESSION_DIR/gedit-drop.log" 2>&1 &')
            blank = 'gedit - [Untitled 1]'
            self.wait_window(blank)
            self.ui(blank, 'place', 650, 100, 600, 500)
            self.ui(source, 'cancel-drag', 1, 130, 125, 850, 300)
            self.cmd('sleep 2')
            self.wait_window(blank, 20)
            self.cmd('! grep -q "transfer=complete" "$job/drop-bridge.err"')
            self.check_source(user+'-cancel')
            self.ui(source, 'drag', 1, 130, 125, 850, 300)
            # GTK 1.2's gedit retains the URI's slashes in its title.
            self.exact_text('gedit - [//'+self.files+'/Text/notes with spaces.txt]', user+'-gedit-window')
            self.check_source(user+'-gedit-window')
            if user == 'xiritest':
                self.gimp()
            log = self.read('cat "$job/drop-bridge.err"')
            assert 'transfer=complete' in log, log
            self.r.setdefault('transfer_logs', {})[user] = log
            self.logout(user+'-drag-complete')
            self.cmd('! pgrep -u '+str(uid)+' -f \'^/usr/local/libexec/xiri/drop-bridge( |$)\' >/dev/null')
        self.login('netbsdtest')
        self.cmd('! pgrep -f \'^/usr/local/libexec/xiri/drop-bridge( |$)\' >/dev/null')
        self.r['native_ctwm_has_no_bridge'] = True
        self.capture('native-ctwm')
        self.checkpoint('drag-drop-complete')

    def gimp(self):
        png = image_fixture()
        self.type('mkdir -p "$HOME/DragProbe/Image"; printf '+
            shlex.quote(''.join('\\%03o'%b for b in png))+' >"$HOME/DragProbe/Image/colour.png"; '
            '/usr/freeware/bin/gimp >"$XIRI_SESSION_DIR/gimp-drop.log" 2>&1 &')
        self.g.wait_for('xwininfo -root -tree | grep -E \'"(GIMP User Installation|The GIMP)"\' >/dev/null', 180)
        if '"GIMP User Installation"' in self.read('xwininfo -root -tree'):
            self.cmd('for i in 1 2; do /tmp/doc-input "GIMP User Installation" click 1 430 491; sleep 2; done')
            self.g.wait_for('test -s '+self.home+'/.gimp-1.2/gimprc', 90)
            self.cmd('for i in 1 2 3; do /tmp/doc-input "GIMP User Installation" click 1 430 491; sleep 2; done')
        self.wait_window('The GIMP', 240)
        self.cmd('if xwininfo -root -tree | grep \'"GIMP Tip of the Day"\' >/dev/null; '
                 'then /tmp/doc-input "GIMP Tip of the Day" click 1 460 108; fi')
        source = self.fm('Image')
        self.ui('The GIMP', 'place', 650, 100, 250, 500)
        self.ui(source, 'place', 20, 100, 550, 480)
        self.ui(source, 'cancel-drag', 1, 100, 160, 740, 180)
        self.cmd('sleep 2; ! xwininfo -root -tree | grep "colour.png-"')
        self.ui(source, 'drag', 1, 100, 160, 740, 180)
        self.g.wait_for('xwininfo -root -tree | grep "colour.png-" >/dev/null', 120)
        self.r['gimp_image_window'] = self.read('xwininfo -root -tree | grep "colour.png-"')
        digest = self.read('sha256 -q '+shlex.quote(self.files+'/Image/colour.png')).strip()
        assert digest == hashlib.sha256(png).hexdigest()
        self.r['gimp_source_unchanged'] = digest
        self.type("printf '\\033[H\\033[2J'")
        self.capture('gimp-running-window-drop')
        self.ui('The GIMP', 'key', 'Ctrl+q')
        self.g.wait_for('! pgrep -u '+str(self.uid)+' -x gimp >/dev/null', 45)


if __name__ == '__main__':
    documents.main(suite_class=Suite, lab_name='drag-drop')
