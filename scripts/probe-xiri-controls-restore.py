#!/usr/bin/env python3
"""Replay captured original panel/desk profiles on a fresh CHD and reboot."""
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys
import textwrap

from xiri_lab import ROOT, sha256

spec = importlib.util.spec_from_file_location('controls', ROOT/'scripts/probe-xiri-desktop-controls.py')
controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls)


class Suite(controls.Suite):
    def run(self):
        source = json.loads(PROFILES.read_text())
        assert source['base_chd_sha256'] == self.r['base_chd_sha256']
        assert source['probe_sha256'] == sha256(ROOT/'scripts/probe-xiri-desktop-controls.py')
        self.r['saved_profile_input'] = dict(path=str(PROFILES), sha256=sha256(PROFILES),
            setup='Replay exact files saved by original panels in the recorded GUI run; panel interaction is qualified separately.')
        self.cmd('cp /tmp/windows /tmp/type /tmp/doc-input /root/documents/')
        expected = {}
        for user, uid, name in [('xiritest', 1234, 'Work'), ('xiritest2', 1237, 'Reading')]:
            home = '/usr/people/'+user
            prefs = source['preferences'][user+'-saved']['files']
            assert set(prefs) == {home+'/.Sgiresources', home+'/.desktop-xiri-indy/panelsession',
                                 home+'/.desktop-xiri-indy/layouts/Default'}
            desks = source['profiles'][user+'-saved']['files']
            assert set(desks) == {'4Dwmsession', '4Dwmdesks', '4Dwmdeskname'}
            files = {**prefs, **{home+'/.desktop-127.0.0.1/0.0/'+k: v for k, v in desks.items()}}
            for path, contents in files.items():
                parent = str(Path(path).parent)
                # Interactive shells can interpret literal tabs as completion.
                # Transfer ASCII encoding and verify bytes before opening X.
                data = contents.encode()
                encoded = base64.b64encode(gzip.compress(data, mtime=0)).decode()
                transfer = shlex.join(['printf', '%s\\n', 'begin-base64 600 profile',
                                      *textwrap.wrap(encoded, 76), '===='])
                digest = hashlib.sha256(data).hexdigest()
                self.cmd('install -d -o '+str(uid)+' -g '+str(uid)+' -m 700 '+shlex.quote(parent)+
                         '; '+transfer+' | uudecode -p | gzip -d >'+shlex.quote(path)+
                         '; chown '+str(uid)+':'+str(uid)+' '+shlex.quote(path)+
                         '; chmod 600 '+shlex.quote(path)+
                         '; test "$(sha256 -q '+shlex.quote(path)+')" = '+digest)
                self.r.setdefault('staged_profile_sha256', {})[path] = digest
            expected[user] = dict(preferences=prefs, name=name,
                                 settings=source['settings'][user+'-changed']['values'])
        self.checkpoint('original-profiles-staged')
        for self.user in ('xiritest', 'xiritest2'):
            entry = expected[self.user]
            self.login(self.user)
            self.restored(self.user+'-restored', entry['settings'])
            assert self.preferences(self.user+'-restored') == entry['preferences']
            self.capture(self.user+'-restored-controls')
            self.logout(self.user+'-restoration-checked')
            self.saved_desks(self.user+'-restoration-checked', entry['name'])
        self.user = 'xiritest'
        entry = expected[self.user]
        assert self.preferences('first-user-after-second') == entry['preferences']
        self.login(self.user)
        self.restored('first-user-before-reboot', entry['settings'])
        lab = self.g.lab
        lab.offset = len(lab.serial_text())
        lab.send('shutdown -r now')
        lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30)
        self.cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; '
                 'ulimit -c 0; cd /root/documents; install -m 555 windows type doc-input /tmp/')
        self.login(self.user)
        self.restored('first-user-after-reboot', entry['settings'])
        assert self.preferences('first-user-after-reboot') == entry['preferences']
        self.capture('preferences-and-desks-after-reboot')
        self.logout('reboot-restoration-checked')
        self.saved_desks('first-user-after-reboot', entry['name'])
        self.r['independent_users'] = True
        self.r['active_shutdown_restore'] = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--saved-profiles', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    PROFILES = args.saved_profiles.resolve()
    sys.argv = [sys.argv[0], *remaining]
    controls.desks.documents.main(Suite, 'controls-restoration',
                                 extra_sources=[('lab/irix-desks/windows.c', 'windows.c')])
