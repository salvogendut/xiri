#!/usr/bin/env python3
"""Exercise cross-filesystem File Manager moves and failures on a fresh CHD."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

spec = importlib.util.spec_from_file_location('documents', Path(__file__).with_name('probe-xiri-documents.py'))
documents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(documents)


class Suite(documents.Suite):
    def type(self, command, window='winterm'):
        # Avoid a literal newline in the serial shell's quoted argument: its
        # continuation-prompt transition can lose the following quote. Return
        # is still a real XTest key event delivered to the terminal.
        self.cmd('/tmp/type "$DISPLAY" '+shlex.quote(window)+' '+shlex.quote(command))
        return self.ui(window, 'key', 'Return')

    def checked(self, command):
        return self.cmd('(set -e; '+command+')')

    def native(self, command):
        return self.checked('su -m '+self.user+' -c '+shlex.quote('set -e; umask 022; '+command))

    def file(self, path, payload, mode=0o640):
        self.native('printf %s '+shlex.quote(payload)+' >'+shlex.quote(path)+
                    '; chmod '+oct(mode)[2:]+' '+shlex.quote(path)+
                    '; TZ=UTC touch -t 200001010000.12 '+shlex.quote(path))

    def verify(self, path, payload, mode=0o640):
        value = self.read('sha256 -q '+shlex.quote(path)).strip()
        assert value == hashlib.sha256(payload.encode()).hexdigest(), (path, value)
        metadata = self.read("stat -f '%u|%g|%Lp|%m' "+shlex.quote(path)).strip()
        assert metadata == f'{self.uid}|{self.uid}|{mode:o}|946684812', (path, metadata)
        self.r.setdefault('files', {})[path] = dict(sha256=value, metadata=metadata)

    def settle(self):
        self.cmd('sleep 3')

    def move(self):
        # Native rename notifications may allocate a different icon slot.
        # Record live changes before this layout action; Sort is used only
        # to give the subsequent mouse gesture a stable starting position.
        self.ui(self.source, 'click', 1, 185, 14)
        self.ui(self.source, 'click', 1, 205, 40)
        self.cmd('sleep 1')
        # Middle-button drag of the first icon onto unused destination space.
        self.ui(self.source, 'drag', 2, 100, 125, 1000, 350)
        self.settle()

    def dialog(self, label, action):
        self.g.wait_for('xwininfo -root -tree | grep \'"File Manager Information"\' >/dev/null', 30)
        client = self.dialog_state(label+'-posted', visible=True)
        self.capture(self.user+'-'+label)
        # The original popup's buttons are anchored to its lower right.
        # Escape/Return can leave this reusable popup mapped: unchanged files
        # alone never proved that Cancel was actually selected.
        right = {'cancel': 164, 'overwrite': 266, 'ok': 112}[action]
        assert client['width'] > right and client['height'] >= 100, client
        self.ui('File Manager Information', 'click', 1,
                client['width']-right, client['height']-36)
        self.settle()
        self.dialog_state(label+'-dismissed', visible=False)
        self.capture(self.user+'-'+label+'-dismissed')

    def dialog_state(self, label, *, visible=False):
        # Xt keeps an unmapped popup for reuse. Its name in xwininfo's tree
        # alone does not mean a dialog is still on the screen.
        state = json.loads(self.read('/tmp/windows list'))
        dialogs = [w for w in state['windows']
                   if w['name'] == 'File Manager Information']
        self.r.setdefault('dialogs', {})[self.user+'-'+label] = dialogs
        mapped = [w for w in dialogs if w['client']['map'] == 2]
        assert len(mapped) == int(visible), (label, dialogs)
        return mapped[0]['client'] if mapped else None

    def windows(self):
        self.source = 'xiri-indy:'+self.src
        self.destination = 'xiri-indy:'+self.dst
        self.type('/emul/irix/usr/sbin/fm '+shlex.quote(self.src)+
                  ' >"$XIRI_SESSION_DIR/edges-source.log" 2>&1 & '+
                  '/emul/irix/usr/sbin/fm '+shlex.quote(self.dst)+
                  ' >"$XIRI_SESSION_DIR/edges-destination.log" 2>&1 &')
        for title, x in ((self.source, 20), (self.destination, 640)):
            self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null', 60)
            self.ui(title, 'place', x, 120, 550, 480)
        self.ui('winterm', 'place', 10, 760, 1000, 200)

    def run(self):
        self.checked('mkdir /tmp/XiriFileManagerFS; mount_tmpfs -s 16m tmpfs /tmp/XiriFileManagerFS')
        for self.user, self.uid in [('xiritest', 1234), ('xiritest2', 1237)]:
            self.home = '/usr/people/'+self.user
            self.src = self.home+'/FileManagerChecks/Source'
            self.dst = '/tmp/XiriFileManagerFS/'+self.user
            self.checked('mkdir '+self.dst+'; chown '+str(self.uid)+':'+str(self.uid)+' '+self.dst+'; chmod 700 '+self.dst)
            self.native('mkdir -m 700 -p '+self.src)
            devices = self.read("stat -f '%d' "+self.src+' '+self.dst).splitlines()
            assert len(devices) == 2 and devices[0] != devices[1], devices
            self.r.setdefault('filesystem_devices', {})[self.user] = devices
            self.login(self.user)
            assert '1280x1024 pixels' in self.read('xdpyinfo | grep dimensions:')
            self.windows()
            self.checkpoint(self.user+'-live-native-changes')
            payload = 'Native file changes for '+self.user+'\n'
            self.file(self.src+'/native change.txt', payload)
            self.settle(); self.capture(self.user+'-native-created')
            self.native('mv '+shlex.quote(self.src+'/native change.txt')+' '+shlex.quote(self.src+'/moved file.txt'))
            self.settle(); self.capture(self.user+'-native-renamed')
            self.move()
            self.checked('test ! -e '+shlex.quote(self.src+'/moved file.txt'))
            self.verify(self.dst+'/moved file.txt', payload)
            self.capture(self.user+'-cross-filesystem-file')

            self.checkpoint(self.user+'-collision')
            replacement = 'Replacement for '+self.user+'\n'
            self.file(self.src+'/moved file.txt', replacement, 0o600)
            self.settle(); self.move(); self.dialog('collision-cancel', 'cancel')
            self.verify(self.src+'/moved file.txt', replacement, 0o600)
            self.verify(self.dst+'/moved file.txt', payload)
            self.move(); self.dialog('collision-overwrite', 'overwrite')
            self.checked('test ! -e '+shlex.quote(self.src+'/moved file.txt'))
            self.verify(self.dst+'/moved file.txt', replacement, 0o600)
            self.native('rm '+shlex.quote(self.dst+'/moved file.txt'))
            self.settle(); self.capture(self.user+'-native-deleted')

            self.checkpoint(self.user+'-directory-and-symlink')
            self.native('mkdir -m 750 '+self.src+'/folder')
            nested = 'Nested payload for '+self.user+'\n'
            self.file(self.src+'/folder/child.txt', nested)
            self.native('ln -s child.txt '+self.src+'/folder/link; TZ=UTC touch -t 200001010000.12 '+self.src+'/folder')
            self.settle(); self.move()
            self.checked('test ! -e '+self.src+'/folder; test "$(readlink '+self.dst+'/folder/link)" = child.txt')
            self.verify(self.dst+'/folder/child.txt', nested)
            metadata = self.read("stat -f '%u|%g|%Lp|%m' "+self.dst+'/folder').strip()
            assert metadata == f'{self.uid}|{self.uid}|750|946684812', metadata
            self.r.setdefault('directories', {})[self.user] = metadata
            self.dialog_state('directory-moved')
            self.capture(self.user+'-directory-moved')
            self.native('rm '+self.dst+'/folder/link '+self.dst+'/folder/child.txt; rmdir '+self.dst+'/folder')

            self.checkpoint(self.user+'-permission-and-retry')
            denied = 'Permission failure preserves this payload.\n'
            self.file(self.src+'/denied.txt', denied, 0o600)
            self.native('chmod 500 '+self.dst)
            self.settle(); self.move(); self.dialog('permission-denied', 'ok')
            self.verify(self.src+'/denied.txt', denied, 0o600)
            self.checked('test ! -e '+self.dst+'/denied.txt')
            self.native('chmod 700 '+self.dst)
            self.settle(); self.move()
            self.checked('test ! -e '+self.src+'/denied.txt')
            self.verify(self.dst+'/denied.txt', denied, 0o600)
            self.capture(self.user+'-permission-restored')

            self.checkpoint(self.user+'-readonly-filesystem')
            self.file(self.src+'/readonly.txt', denied, 0o600)
            self.type('/emul/irix/usr/sbin/fm /cdrom >"$XIRI_SESSION_DIR/edges-readonly.log" 2>&1 &')
            self.g.wait_for('xwininfo -root -tree | grep \'"xiri-indy:/cdrom"\' >/dev/null', 60)
            self.ui('xiri-indy:/cdrom', 'place', 640, 120, 550, 480)
            self.settle(); self.move(); self.dialog('readonly-filesystem', 'ok')
            self.verify(self.src+'/readonly.txt', denied, 0o600)
            self.checked('test ! -e /cdrom/readonly.txt')
            self.logout(self.user+'-complete')
        self.checked('umount /tmp/XiriFileManagerFS')
        self.r['scope'] = 'Native create/rename/delete notifications; FFS to tmpfs; regular files, directory and relative symlink; collision cancel/overwrite; permission failure/retry; read-only CD; two authenticated users.'


if __name__ == '__main__':
    documents.main(Suite, 'file-manager-edges',
                   extra_sources=[('lab/irix-desks/windows.c', 'windows.c')])
