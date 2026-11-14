#!/usr/bin/env python3
"""Qualify original 4Dwm window controls and desks on a disposable CHD."""
import importlib.util
import json
from pathlib import Path
import re

from xiri_lab import ROOT

spec = importlib.util.spec_from_file_location('documents', ROOT/'scripts/probe-xiri-documents.py')
documents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(documents)


class Suite(documents.Suite):
    def login(self, user):
        # An inactive desk's Catalog initially has the plain "Icon Catalog"
        # title, without its selected-page suffix. It is still a live client.
        super().login(user,wait_catalog=False)
        self.g.wait_for('xwininfo -root -tree | grep \'"winterm"\' >/dev/null',120)

    def snapshot(self, label, actions=''):
        # A failed gesture must not be hidden by the succeeding observation.
        command = '(set -e; '+(actions+'; sleep 1; ' if actions else '')+'/tmp/windows list)'
        text = self.read(command)
        state = json.loads(text)
        self.r.setdefault('states', {})[label] = state
        self.checkpoint(label)
        return state

    @staticmethod
    def window(state, name):
        matches = [w for w in state['windows'] if w['name'] == name]
        assert len(matches) == 1, (name, matches)
        return matches[0]

    @classmethod
    def geometry(cls, state, name='winterm'):
        return {k: cls.window(state, name)['client'][k] for k in ('x','y','width','height')}

    @classmethod
    def title_button(cls, state, right, name='winterm'):
        frame = cls.window(state, name)['frame_geometry']
        return '/tmp/windows click 1 %d %d' % (frame['x']+frame['width']-right, frame['y']+18)

    @classmethod
    def restore_icon(cls, state, name='winterm'):
        icon = cls.window(state, name)['icon_geometry']
        assert icon and icon['map'] == 2, icon
        return '/tmp/windows click 1 %d %d' % (icon['x']+icon['width']//2, icon['y']+icon['height']//2)

    def controls(self, user):
        state = self.snapshot(user+'-initial')
        normal = self.geometry(state)
        state = self.snapshot(user+'-button-minimize', self.title_button(state,44))
        window = self.window(state,'winterm')
        assert window['state']==3 and window['client']['map']!=2 and window['icon_geometry']['map']==2
        self.capture(user+'-minimized')
        state = self.snapshot(user+'-icon-restore',self.restore_icon(state))
        assert self.window(state,'winterm')['state']==1 and self.geometry(state)==normal
        state = self.snapshot(user+'-button-maximize',self.title_button(state,20))
        maximized = self.geometry(state)
        assert maximized['width']>normal['width'] and maximized['height']>normal['height']
        assert maximized['x']>=0 and maximized['y']>=0
        assert maximized['x']+maximized['width']<=1280 and maximized['y']+maximized['height']<=1024
        state = self.snapshot(user+'-key-restore','/tmp/windows key Alt+F5')
        assert self.geometry(state)==normal
        state = self.snapshot(user+'-key-maximize','/tmp/windows key Alt+F10')
        assert self.geometry(state)==maximized
        state = self.snapshot(user+'-key-normal','/tmp/windows key Alt+F5')
        assert self.geometry(state)==normal
        state = self.snapshot(user+'-key-minimize','/tmp/windows key Alt+F9')
        assert self.window(state,'winterm')['state']==3
        state = self.snapshot(user+'-icon-normal',self.restore_icon(state))
        assert self.geometry(state)==normal
        self.r.setdefault('window_controls',{})[user] = dict(normal=normal,maximized=maximized)

    def keyboard(self, user):
        def focus(state):
            c = self.window(state,'winterm')['client']
            return '/tmp/windows point %d %d' % (c['x']+100,c['y']+50)
        a = self.snapshot(user+'-keyboard-start')
        a = self.snapshot(user+'-pointer-focus',focus(a))
        assert a['focus']==self.window(a,'winterm')['id']
        b = self.snapshot(user+'-pointer-tab','/tmp/windows key Alt+Tab')
        assert b['focus']==a['focus']  # f.next_key needs explicit focus policy.
        c = self.snapshot(user+'-menu-move',focus(b)+'; /tmp/windows key Alt+space m Right Down Return')
        assert self.geometry(c)['x']>self.geometry(a)['x'] and self.geometry(c)['y']>self.geometry(a)['y']
        assert self.geometry(c)['width']==self.geometry(a)['width']
        d = self.snapshot(user+'-menu-size',focus(c)+'; /tmp/windows key Alt+space s Right Down Return')
        assert self.geometry(d)['width']>self.geometry(c)['width'] and self.geometry(d)['height']>self.geometry(c)['height']
        e = self.snapshot(user+'-menu-cancel',focus(d)+'; /tmp/windows key Alt+space m Right Escape')
        assert self.geometry(e)==self.geometry(d)
        b = self.snapshot(user+'-lower',focus(e)+'; /tmp/windows key Alt+F3')
        c = self.snapshot(user+'-raise',focus(b)+'; /tmp/windows key Alt+F1')
        assert self.window(c,'winterm')['stack']>self.window(b,'winterm')['stack']
        self.r['keyboard_menu_controls'] = 'passed'

    def overview(self):
        # The original Toolchest menu invokes /usr/sbin/ov through its shell.
        self.ui('Toolchest','click',1,45,14)
        self.cmd('/tmp/windows click 1 170 107')
        self.g.wait_for('xwininfo -root -tree | grep \'"Desks Overview"\' >/dev/null',60)
        self.ui('Desks Overview','place',30,700,500,260)

    def switch(self, second):
        self.ui('Desks Overview','double',1,65,160 if second else 45)

    def layout(self, label, second, clock_on_second=True):
        state = self.snapshot(label)
        assert (self.window(state,'winterm')['client']['map']==2)==(not second)
        assert (self.window(state,'xclock')['client']['map']==2)==(second if clock_on_second else not second)
        for name in ('Toolchest','Desks Overview'):
            assert self.window(state,name)['client']['map']==2
        # Inactive clients receive their per-desk geometry when that desk is
        # selected. Overview may round its own width by one pixel at startup.
        return {name:self.geometry(state,name) for name in ('winterm','xclock')
                if self.window(state,name)['client']['map']==2}

    def profile(self, user, label):
        path='/usr/people/'+user+'/.desktop-127.0.0.1/0.0'
        files={name:self.read('cat '+path+'/'+name) for name in ('4Dwmsession','4Dwmdesks','4Dwmdeskname')}
        uid=1234 if user=='xiritest' else 1237
        metadata=self.read("stat -f '%N|%u|%g|%Lp' /usr/people/"+user+' '+path+'/4Dwm*')
        assert metadata.splitlines()[0]=='/usr/people/'+user+'|'+str(uid)+'|'+str(uid)+'|700',metadata
        assert all(line.split('|')[1]==str(uid) for line in metadata.splitlines()),metadata
        assert all(line.endswith('|600') for line in metadata.splitlines()[1:]),metadata
        self.r.setdefault('profiles',{})[label]=dict(user=user,files=files,metadata=metadata)
        return files

    def choose_click_focus(self):
        self.type('/emul/irix/usr/sbin/windows >"$XIRI_SESSION_DIR/windows.log" 2>&1 &')
        self.g.wait_for('xwininfo -root -tree | grep \'"Window Settings"\' >/dev/null',60)
        self.ui('Window Settings','click',1,35,215)
        self.g.wait_for('xwininfo -root -tree | grep questionDialog_popup >/dev/null',30)
        self.ui('windows','click',1,445,104)  # Cancel the immediate WM restart.
        self.ui('Window Settings','click',1,70,444)
        self.cmd('grep -q "keyboardFocusPolicy:.*explicit" /usr/people/xiritest/.Sgiresources')

    def click_focus(self):
        resources=self.read('xrdb -query')
        assert re.search(r'4Dwm\*keyboardFocusPolicy:\s+explicit',resources)
        self.r['explicit_focus_resources']=resources
        a=self.snapshot('explicit-click','/tmp/windows click 1 120 230')
        assert a['focus']==self.window(a,'winterm')['id']
        b=self.snapshot('explicit-tab','/tmp/windows key Alt+Tab')
        c=self.snapshot('explicit-reverse-tab','/tmp/windows key Alt+Shift+Tab')
        assert b['focus']!=a['focus'] and c['focus']==a['focus']
        assert any(w['id']==b['focus'] and w['client']['map']==2 for w in b['windows'])
        self.r['explicit_keyboard_navigation']='passed'

    def run(self):
        self.cmd('cp /tmp/windows /tmp/type /tmp/doc-input /root/documents/')
        ledger=json.loads((ROOT/'lab/irix-desks/resources.json').read_text())
        expected=ledger['paths']['/usr/sbin/ov']['sha256']
        actual=self.read('sha256 -q /emul/irix/usr/sbin/ov').strip()
        assert actual==expected
        self.r['ov_sha256']=actual
        self.login('xiritest')
        assert '1280x1024 pixels' in self.read('xdpyinfo | grep dimensions:')
        self.controls('xiritest');self.keyboard('xiritest')
        self.overview()
        self.r['toolchest_launch']=self.read("ps -axww -o uid,pid,ppid,args | grep '[ /]ov\\( \\|$\\)'")
        assert re.search(r'^\s*1234\s+\d+\s+\d+\s+/usr/sbin/ov\s*$',self.r['toolchest_launch'],re.M)
        self.ui('Desks Overview','key','Ctrl+n')
        self.ui('Desks Overview','drag',1,83,62,80,200)
        first_desk=self.layout('clock-moved',False)
        self.switch(True)
        original=self.layout('desk2',True)
        self.capture('two-desks')
        self.logout('first-layout-saved')
        saved=self.profile('xiritest','first-logout')
        assert saved['4Dwmdeskname'].strip()=='"Desk 2"'
        assert re.search(r'^room\s+"Desk 2"\s+visible\s*\{',saved['4Dwmdesks'],re.M)
        self.login('xiritest')
        assert self.layout('restored-after-login',True)==original
        self.switch(False)
        assert self.layout('restored-desk1',False)==first_desk
        self.switch(True)
        self.logout('first-restoration-checked')
        first=self.profile('xiritest','before-second-user')
        self.login('xiritest2')
        self.overview()
        second_start=self.read('cat /usr/people/xiritest2/.desktop-127.0.0.1/0.0/4Dwmdesks')
        assert 'Desk 2' not in second_start
        self.ui('Desks Overview','key','Ctrl+n')
        self.switch(True);self.layout('second-empty-desk',True,False)
        self.switch(False);self.layout('second-original-desk',False,False)
        self.logout('second-layout-saved')
        self.profile('xiritest2','second-logout')
        assert self.profile('xiritest','after-second-user')==first
        self.r['independent_users']=True
        self.login('xiritest')
        assert self.layout('first-user-recheck',True)==original
        self.switch(False);self.choose_click_focus();self.switch(True)
        # Reboot with the desktop active: rc.d must save before xdm stops.
        lab=self.g.lab
        lab.offset=len(lab.serial_text());lab.send('shutdown -r now')
        lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30)
        self.cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0; '
                 'cd /root/documents; install -m 555 windows type doc-input /tmp/')
        self.login('xiritest')
        assert self.layout('restored-after-reboot',True)==original
        self.capture('desks-after-reboot')
        self.switch(False)
        assert self.layout('desk1-after-reboot',False)==first_desk
        self.click_focus()
        self.r['active_shutdown_restore']=True
        self.logout('reboot-restoration-checked')


if __name__ == '__main__':
    documents.main(suite_class=Suite, lab_name='windows-desks',
                   extra_sources=[('lab/irix-desks/windows.c','windows.c')])
