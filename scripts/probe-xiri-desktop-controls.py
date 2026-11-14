#!/usr/bin/env python3
"""Exercise original preference panels and desk rename/delete on a cold CHD."""
import importlib.util
import json
from pathlib import Path
import re
import shlex

from xiri_lab import ROOT

spec = importlib.util.spec_from_file_location('desks', ROOT/'scripts/probe-xiri-desks.py')
desks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desks)


class Suite(desks.Suite):
    def type(self, command, window='winterm'):
        # Keep shell input on one line and send Return as an input event.
        self.cmd(shlex.join(['/tmp/type', '127.0.0.1:0', window, command]))
        self.ui(window, 'key', 'Return')

    def panel(self, app, title):
        self.type('/emul/irix/usr/sbin/'+app+
                  ' >"$XIRI_SESSION_DIR/'+app+'.out" 2>"$XIRI_SESSION_DIR/'+app+'.err" &')
        self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null', 60)
        c = self.window(self.snapshot(self.user+'-'+app+'-open'), title)['client']
        self.ui(title, 'place', 100, 80, c['width'], c['height'])

    def close_panel(self, title, x, bottom):
        c = self.window(self.snapshot(self.user+'-panel-before-close'), title)['client']
        self.ui(title, 'click', 1, x, c['height']-bottom)
        state = self.snapshot(self.user+'-panel-closed')
        assert not any(w['name']==title and w['client']['map']==2 for w in state['windows'])

    def settings(self, label):
        query = self.read('xset q')
        values = dict(repeat=re.search(r'auto repeat:\s+(on|off)',query)[1],
                      pointer=list(map(int,re.search(r'acceleration:\s+(\d+)/(\d+)\s+threshold:\s+(\d+)',query).groups())),
                      saver=list(map(int,re.search(r'timeout:\s+(\d+)\s+cycle:\s+(\d+)',query).groups())))
        self.r.setdefault('settings', {})[label] = dict(values=values, query=query)
        return values

    def panels(self):
        first = self.user=='xiritest'
        # The maintained seed starts with enabled grid, hidden files off,
        # repeat on and blanking off. Give the two users different choices.
        initial = self.settings(self.user+'-initial')
        assert initial['repeat']=='on' and initial['saver'][0]==0, initial
        self.panel('desktop', 'Desktop Settings')
        for _ in range(1 if first else 2):
            self.ui('Desktop Settings', 'click', 1, 131, 199)
        self.close_panel('Desktop Settings', 111, 43)
        self.panel('fmprefs', 'Default Layout for Icon Views ')
        for _ in range(1 if first else 2):
            self.ui('Default Layout for Icon Views ', 'click', 1, 31, 428)
        self.capture(self.user+'-icon-preferences')
        self.close_panel('Default Layout for Icon Views ', 145, 36)
        self.panel('mouse', 'Mouse Settings')
        self.ui('Mouse Settings', 'click', 1, 157 if first else 69, 131)
        self.capture(self.user+'-mouse')
        self.close_panel('Mouse Settings', 122, 43)
        self.panel('screensaver', 'Screen Saver')
        for _ in range(1 if first else 2):
            self.ui('Screen Saver', 'click', 1, 15, 116)
        self.close_panel('Screen Saver', 96, 42)
        self.panel('keyboard', 'Keyboard Settings ')
        for _ in range(1 if first else 2):
            self.ui('Keyboard Settings ', 'click', 1, 16, 109)
        self.capture(self.user+'-keyboard')
        self.close_panel('Keyboard Settings ', 80, 43)
        values = self.settings(self.user+'-changed')
        assert values['repeat']==('off' if first else 'on'), values
        assert values['pointer']==([7,1,6] if first else [1,4,10]), values
        assert values['saver'][0]==(600 if first else 0), values
        return values

    def preferences(self, label):
        home = '/usr/people/'+self.user
        paths = [home+'/.Sgiresources', home+'/.desktop-xiri-indy/panelsession',
                 home+'/.desktop-xiri-indy/layouts/Default']
        files = {path:self.read('cat '+shlex.quote(path)) for path in paths}
        metadata = self.read("stat -f '%N|%u|%g|%Lp' "+shlex.join([home]+paths))
        uid = 1234 if self.user=='xiritest' else 1237
        assert metadata.splitlines()[0]==home+'|'+str(uid)+'|'+str(uid)+'|700', metadata
        assert all(line.endswith('|'+str(uid)+'|'+str(uid)+'|600') for line in metadata.splitlines()[1:]), metadata
        boolean = 'False' if self.user=='xiritest' else 'True'
        assert re.search(r'\*snapToGrid:\s+'+boolean, files[paths[0]]), files
        boolean = 'True' if self.user=='xiritest' else 'False'
        assert re.search(r'ShowHidden\s*=\s*'+boolean, files[paths[2]]), files
        self.r.setdefault('preferences', {})[label] = dict(files=files, metadata=metadata)
        return files

    def delete_selected(self):
        self.ui('Desks Overview', 'click', 1, 120, 13)
        self.cmd('/tmp/windows click 1 180 687')

    def named_desks(self):
        name = 'Work' if self.user=='xiritest' else 'Reading'
        self.overview()
        self.ui('Desks Overview', 'place', 30, 550, 500, 430)
        self.ui('Desks Overview', 'key', 'Ctrl+n')
        self.ui('Desks Overview', 'click', 1, 65, 160)
        self.ui('Desks Overview', 'key', 'Ctrl+r')
        # The editor is a child widget. Do not move focus to the parent.
        self.g.monitor('key type '+name)
        self.g.monitor('key Return')
        self.ui('Desks Overview', 'click', 1, 65, 160)
        self.ui('Desks Overview', 'key', 'Ctrl+c')
        self.capture(self.user+'-copied-desk')
        self.ui('Desks Overview', 'click', 1, 65, 275)
        self.delete_selected()
        self.capture(self.user+'-deleted-copy')
        # The active starting desk is protected and produces a real dialog.
        self.ui('Desks Overview', 'click', 1, 65, 45)
        self.delete_selected()
        state = self.snapshot(self.user+'-protected-desk')
        c = self.window(state,'Desk Overview Error')['client']
        assert c['map']==2
        self.capture(self.user+'-protected-desk')
        self.ui('Desk Overview Error', 'click', 1, c['width']-42, c['height']-36)
        state = self.snapshot(self.user+'-protected-dialog-closed')
        assert not any(w['name']=='Desk Overview Error' and w['client']['map']==2 for w in state['windows'])
        self.ui('Desks Overview', 'drag', 1, 83, 62, 80, 200)
        self.switch(True)
        self.layout(self.user+'-renamed-desk-active', True)
        self.capture(self.user+'-renamed-desk')
        return name

    def saved_desks(self, label, name):
        profile = self.profile(self.user, label)
        rooms = re.findall(r'^room\s+"([^"]+)"', profile['4Dwmdesks'], re.M)
        assert rooms==['Global','Desk 1',name], rooms
        assert profile['4Dwmdeskname'].strip()=='"'+name+'"', profile
        return profile

    def restored(self, label, expected):
        assert self.settings(label)==expected
        self.layout(label+'-desk', True)
        resources = self.read('xrdb -query')
        boolean = 'False' if self.user=='xiritest' else 'True'
        assert re.search(r'\*snapToGrid:\s+'+boolean, resources), resources
        self.r.setdefault('restored_resources', {})[label]=resources
        assert self.read('cat "$job/panelsession.err"')=='', self.read('cat "$job/panelsession.err"')
        replay = self.read('cat "$job/panelsession"')
        assert '/usr/bin/X11/xset' not in replay and '-art ' not in replay, replay
        self.r.setdefault('panel_replays', {})[label]=replay

    def run(self):
        self.cmd('cp /tmp/windows /tmp/type /tmp/doc-input /root/documents/')
        assert self.read('sha256 -q /emul/irix/usr/sbin/keyboard').strip()==\
            '5a627a6ef06691381a71800b5b0f60f8981f8fdb79d89c18b0029ac15689cf8b'
        originals = {}
        for self.user in ('xiritest','xiritest2'):
            self.login(self.user)
            assert '1280x1024 pixels' in self.read('xdpyinfo | grep dimensions:')
            values = self.panels()
            name = self.named_desks()
            self.logout(self.user+'-saved')
            # Creating/copying desks adds their original background resources.
            # Compare the complete saved profile after those legitimate edits.
            prefs = self.preferences(self.user+'-saved')
            profile = self.saved_desks(self.user+'-saved',name)
            self.login(self.user)
            self.restored(self.user+'-restored',values)
            assert self.preferences(self.user+'-restored')==prefs
            self.logout(self.user+'-restoration-checked')
            profile = self.saved_desks(self.user+'-restoration-checked',name)
            originals[self.user] = dict(settings=values, preferences=prefs, desks=profile, name=name)
        self.user='xiritest'
        assert self.preferences('first-user-after-second')==originals[self.user]['preferences']
        assert self.saved_desks('first-user-after-second','Work')==originals[self.user]['desks']
        self.login(self.user)
        self.restored('first-user-recheck',originals[self.user]['settings'])
        # Save the active desktop through the real shutdown path.
        lab=self.g.lab
        lab.offset=len(lab.serial_text()); lab.send('shutdown -r now')
        lab.wait('login: ',600); lab.send('root'); lab.wait('xiri-indy# ',30)
        self.cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0; '
                 'cd /root/documents; install -m 555 windows type doc-input /tmp/')
        self.login(self.user)
        self.restored('first-user-after-reboot',originals[self.user]['settings'])
        assert self.preferences('first-user-after-reboot')==originals[self.user]['preferences']
        self.capture('preferences-and-desks-after-reboot')
        self.logout('reboot-restoration-checked')
        self.r['independent_users']=True
        self.r['active_shutdown_restore']=True


if __name__=='__main__':
    desks.documents.main(suite_class=Suite, lab_name='desktop-controls-cold',
                         extra_sources=[('lab/irix-desks/windows.c','windows.c')])
