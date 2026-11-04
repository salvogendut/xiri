"""Cold-image application controls and the previous Acrobat focus-timeout path.

The caller owns a disposable guest and its cleanup/CPU/kernel diagnostics.
No vendor bytes or runtime configuration are replaced by these checks.
"""
import re
import shlex
import time

from . import sha256


def check(guest, directory, result, base, repetitions):
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    home = '/usr/people/xiritest'
    record = result['image_apps'] = dict(status='running', stage='initial', replays=[])

    def phase(name):
        record['stage'] = name
        print('Image applications: '+name, flush=True)

    def capture(name):
        # Preserve the original cold-image sequence, including its two waits.
        guest.monitor('disp compositor gl'); time.sleep(2)
        guest.monitor('disp compositor sw'); time.sleep(2)
        path = directory/(name+'.png')
        guest.monitor('screen shot '+str(path))
        assert path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
        result.setdefault('screenshots', {})[name] = sha256(path)
        record.setdefault('captures', []).append(name)

    def type_text(window, text):
        cmd(shlex.join([base+'/type', '127.0.0.1:0', window, text]))

    def click(x, y):
        cmd(shlex.join(['/tmp/click', str(x), str(y)]))

    def gnome_start(name):
        # Submit both commands before Return: the new window can take focus.
        type_text('winterm', '/usr/freeware/bin/gnome-terminal >"$XIRI_SESSION_DIR/'+name+
                  '.out" 2>"$XIRI_SESSION_DIR/'+name+'.err" & '
                  'echo $! >"$XIRI_SESSION_DIR/'+name+'.pid"\n')
        wait('test -s "$job/'+name+'.pid" && xwininfo -name Terminal >/dev/null', 120)
        return int(get('cat "$job/'+name+'.pid"').strip())

    def gnome_exit(name):
        type_text('Terminal', 'exit\n')
        wait('! xwininfo -name Terminal >/dev/null 2>&1', 60)
        type_text('winterm', 'wait "$(cat "$XIRI_SESSION_DIR/'+name+'.pid")"; '
                  'echo $? >"$XIRI_SESSION_DIR/'+name+'.status"\n')
        wait('test -s "$job/'+name+'.status"', 60)
        status = get('cat "$job/'+name+'.status"').strip()
        assert status == '0', status
        return dict(status=0, stderr=get('cat "$job/'+name+'.err"'))

    cmd('ln -s '+shlex.quote(base+'/click-original')+' /tmp/click')
    record['fresh_profiles'] = cmd('test ! -e '+home+'/.gnome/Terminal && '
                                   'test ! -e '+home+'/.acrorc')
    type_text('winterm', '(echo "$ACRO_CONFIG"; id -u; pwd) >"$XIRI_SESSION_DIR/acrobat-environment"\n')
    wait('test "$(wc -l <"$job/acrobat-environment")" -eq 3', 30)
    record['environment'] = get('cat "$job/acrobat-environment"').splitlines()
    assert record['environment'] == ['mipsirix', '1234', home]
    phase('GNOME original shell and preferences')
    first = gnome_start('image-gnome')
    type_text('Terminal', '(echo "$-"; pwd; echo "$HOME"; id -u) >xiri-image-shell-proof\n')
    wait('test "$(wc -l <'+home+'/xiri-image-shell-proof)" -eq 4', 30)
    proof = get('cat '+home+'/xiri-image-shell-proof').splitlines()
    assert 'i' in proof[0] and proof[1:] == [home, home, '1234'], proof
    record['gnome'] = dict(pid=first, shell=proof)
    cmd(base+'/place Terminal 50 60 650 400; sleep 1; /tmp/click 164 73; /tmp/click 194 102; sleep 2')
    capture('apps-gnome-preferences')
    cmd('/tmp/click 145 55; /tmp/click 165 125')
    guest.monitor('key home'); guest.monitor('key shift+end')
    for key in ['2', '5', '7']: guest.monitor('key '+key)
    guest.monitor('key tab')
    cmd('/tmp/click 185 344; sleep 1')
    record['gnome']['saved'] = get('cat '+home+'/.gnome/Terminal')
    assert 'scrollbacklines=257' in record['gnome']['saved']
    click(86, 343)
    record['gnome']['exit'] = gnome_exit('image-gnome')
    second = gnome_start('image-gnome-reopened')
    state = get('xwininfo -name Terminal')
    record['gnome']['reopened_pid'] = second
    record['gnome']['reopened'] = get('cat '+home+'/.gnome/Terminal')
    assert 'scrollbacklines=257' in record['gnome']['reopened']
    x = int(re.search(r'Absolute upper-left X:\s+(\d+)', state)[1])
    y = int(re.search(r'Absolute upper-left Y:\s+(\d+)', state)[1])
    cmd(f'/tmp/click {x+114} {y+13}; sleep 1; /tmp/click {x+144} {y+42}; sleep 1; /tmp/click 145 55; sleep 1')
    capture('apps-gnome-reopened')
    click(286, 343)
    record['gnome']['reopened_exit'] = gnome_exit('image-gnome-reopened')
    record['gnome']['file_identity'] = get("stat -f '%u %g %Lp' "+home+'/.gnome/Terminal').strip()
    assert record['gnome']['file_identity'] == '1234 1234 600'

    phase('Acrobat catalog launch')
    pdf = home+'/xiri-acrobat-test.pdf'
    cmd('install -m 644 -o xiritest -g xiritest /usr/adobe/Acrobat4.0/Reader/Acrobat.pdf '+pdf)
    record['pdf_sha256'] = get('sha256 -q '+pdf).strip()
    assert record['pdf_sha256'] == 'f1bc498f742ca8f72f22cf650a43584494b41e1b2eb24b7e2d8d626eab758c9a'
    tree = get('xwininfo -root -tree')
    match = re.search(r'(0x[0-9a-f]+) "Icon Catalog: [^"\n]*\(Page (\d+) of 18\)', tree)
    assert match, tree
    wid, page = match[1], int(match[2])
    cmd('xset r off')
    for _ in range(abs(3-page)):
        cmd(shlex.join([base+'/catalog-input', '127.0.0.1:0', wid, 'key',
                        'Next' if page < 3 else 'Prior'])+'; sleep 1')
    cmd('xset r on; '+base+'/place "Icon Catalog: Applications (Page 3 of 18)" 372 450 900 500; sleep 2')
    pdf_window = 'name='+b'xiri-acrobat-test.pdf'.hex()
    original_count = (repetitions+1)//2
    for index in range(1, repetitions+1):
        phase('PDF/capture/focus/exit '+str(index)+'/'+str(repetitions))
        entry = dict(iteration=index, helper='original' if index <= original_count else 'traced')
        record['replays'].append(entry)
        cmd(shlex.join([base+'/catalog-input', '127.0.0.1:0', wid, 'double', '1010', '526']))
        wait("pgrep -u 1234 -f '^/usr/adobe/Acrobat4.0/bin/acroread.dist( |$)' >acrobat.pid && "
             'test "$(wc -l <acrobat.pid)" -eq 1', 90)
        pid = int(get('cat acrobat.pid').strip()); entry['pid'] = pid
        wait(base+'/windows | grep class=4163726f52656164 >/dev/null', 90)
        if index == 1:
            wait(base+'/windows | grep instance=65756c61206469616c6f675f706f707570 >/dev/null', 60)
            capture('apps-acrobat-first-run')
            # Same original first-run dialog and acceptance as the prior image.
            click(335, 805)
        wait('xwininfo -name Acrobat >/dev/null', 60)
        # 4Dwm cascades successive launches. At the fifth natural position,
        # (300,300) hits Open on the toolbar instead of the document area.
        # Keep the original focus command/timing with a stable target.
        cmd(base+'/place Acrobat 50 50 800 600; sleep 1')
        click(300, 300); guest.monitor('key ctrl+o')
        wait('xwininfo -name Open >/dev/null', 30)
        if index == 1: capture('apps-acrobat-open-dialog')
        cmd('/tmp/click 830 420; /tmp/click 434 675; sleep 5')
        wait(base+'/windows | grep '+pdf_window+' >/dev/null', 60)
        wait('! '+base+'/windows | grep "name=4f70656e class=4163726f52656164" >/dev/null', 30)
        cmd(base+'/place xiri-acrobat-test.pdf 50 50 800 600; sleep 1')
        entry['pdf_geometry'] = get('xwininfo -name xiri-acrobat-test.pdf')
        for axis in ['X', 'Y']:
            coordinate = int(re.search(r'Absolute upper-left '+axis+r':\s+(\d+)',
                                       entry['pdf_geometry'])[1])
            assert 0 <= coordinate <= 100, entry['pdf_geometry']
        entry['pdf_windows'] = get(base+'/windows')
        capture('apps-acrobat-pdf-'+str(index))
        # Keep the original failing command directly after the GL -> SW capture.
        # Do not insert X queries or extra guest commands before this focus call.
        if entry['helper'] == 'original':
            entry['focus_command'] = cmd('/tmp/click 300 300')
        else:
            entry['focus_log'] = 'acrobat-focus-'+str(index)+'.log'
            cmd(base+'/click-trace 300 300 >'+entry['focus_log']+' 2>&1')
        entry['focus_status'] = 0
        guest.monitor('key ctrl+q')
        wait('! kill -0 '+str(pid)+' 2>/dev/null', 120)
        entry['windows_after'] = get(base+'/windows')
        assert pdf_window not in entry['windows_after']
        entry['gui_exit'] = True
        if entry['helper'] == 'traced':
            entry['focus_trace'] = get('cat '+entry['focus_log'])
            assert 'CLICK END stage=close ' in entry['focus_trace']
        cmd('/usr/local/libexec/xiri/x11-check ready')
    record['pdf_identity'] = get("stat -f '%u %g %Lp' "+pdf).strip()
    assert record['pdf_identity'] == '1234 1234 644'
    record['status'] = 'passed'
    phase('all application and focus replay checks passed')
