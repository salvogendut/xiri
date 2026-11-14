#!/usr/bin/env python3
"""Check saved Icon Views defaults; capture hidden-file visibility for review."""
import importlib.util
import json
import re
import shlex

from xiri_lab import ROOT

spec=importlib.util.spec_from_file_location('documents', ROOT/'scripts/probe-xiri-documents.py')
documents=importlib.util.module_from_spec(spec)
spec.loader.exec_module(documents)


class Suite(documents.Suite):
    def type(self, command, window='winterm'):
        self.cmd(shlex.join(['/tmp/type', '127.0.0.1:0', window, command]))
        self.ui(window, 'key', 'Return')

    def run(self):
        self.r['visibility_review_required']=True
        self.r['loaded_module']=self.read('modstat | grep compat_irix_o32; '
            'sha256 /stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod')
        assert self.r['module_sha256'] in self.r['loaded_module']
        for user in ('xiritest','xiritest2'):
            self.login(user)
            title='Default Layout for Icon Views '
            self.type('/emul/irix/usr/sbin/fmprefs >"$XIRI_SESSION_DIR/fmprefs.out" '
                      '2>"$XIRI_SESSION_DIR/fmprefs.err" &')
            self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null',60)
            for _ in range(1 if user=='xiritest' else 2):
                self.ui(title, 'click', 1, 31, 428)
            self.ui(title, 'click', 1, 145, 490)
            self.logout(user+'-icon-default-saved')
            self.login(user)
            default='/usr/people/'+user+'/.desktop-xiri-indy/layouts/Default'
            saved=self.read('cat '+default)
            expected='True' if user=='xiritest' else 'False'
            assert re.search(r'^ShowHidden = '+expected+r'$',saved,re.M),saved
            # Reopen the original panel and a new, uncached directory view.
            # Both files exist for both users; only the default differs.
            self.type('mkdir -m 700 "$HOME/HiddenViewCheck"; '
                      'touch "$HOME/HiddenViewCheck/visible.txt" "$HOME/HiddenViewCheck/.hidden.txt"; '
                      '/emul/irix/usr/sbin/fm "$HOME/HiddenViewCheck" '
                      '>"$XIRI_SESSION_DIR/hidden-view.out" 2>"$XIRI_SESSION_DIR/hidden-view.err" &')
            view='xiri-indy:/usr/people/'+user+'/HiddenViewCheck'
            self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+view+'"')+' >/dev/null',60)
            self.ui(view,'place',100,80,800,600)
            self.cmd('sleep 2')
            self.capture(user+'-hidden-files-'+('shown' if user=='xiritest' else 'hidden'))
            files=self.read("stat -f '%N|%u|%g|%Lp' /usr/people/"+user+'/HiddenViewCheck/visible.txt '
                            '/usr/people/'+user+'/HiddenViewCheck/.hidden.txt')
            self.r.setdefault('views',{})[user]=dict(default=saved,files=files,
                expected_icons=['.hidden.txt','visible.txt'] if user=='xiritest' else ['visible.txt'])
            self.type('/emul/irix/usr/sbin/fmprefs >"$XIRI_SESSION_DIR/fmprefs-reopen.out" '
                      '2>"$XIRI_SESSION_DIR/fmprefs-reopen.err" &')
            self.g.wait_for('xwininfo -root -tree | grep -F '+shlex.quote('"'+title+'"')+' >/dev/null',60)
            self.ui(title,'place',920,80,341,526)
            self.capture(user+'-icon-default-reopened')
            self.ui(title,'click',1,145,490)
            self.logout(user+'-icon-view-complete')


if __name__=='__main__':
    documents.main(Suite, 'iconviews')
