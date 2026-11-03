"""Graphical winterm checks without hiding startup geometry by resizing first."""
import re
import shlex
import time
from . import sha256


def check(guest, directory, record, *, extra=False):
    cmd,get,wait=guest.command,guest.read_text,guest.wait_for
    sequence=len(record.setdefault('winterm',[]))+1
    entry={'initial_tree':get('xwininfo -root -tree'),
           'initial_hints':get('xprop -name winterm WM_NORMAL_HINTS'),
           'handoff':get('cat "$job/handoff"')}
    increments=re.search(r'resize increment: (\d+) by (\d+)',entry['initial_hints'])
    assert increments,entry['initial_hints']
    cell_x,cell_y=map(int,increments.groups())
    assert 5<=cell_x<=20 and 10<=cell_y<=32,('Collapsed font metrics',cell_x,cell_y)
    geometry=re.search(r'"winterm":.*? (\d+)x(\d+)\+',entry['initial_tree'])
    assert geometry,entry['initial_tree']
    width,height=map(int,geometry.groups())
    assert height==24*cell_y and width>=80*cell_x,(width,height,cell_x,cell_y)
    # xwsh may fork before its final ConfigureNotify: the observed initial
    # handoff is 24x78, followed by a tty update to the visible 24x80 grid.
    assert re.search(r'rows=24 cols=(78|80)\b',entry['handoff']),entry['handoff']
    shot=directory/f'winterm-untouched-{sequence}.png'
    cmd(shlex.join(['./type','127.0.0.1:0','winterm','']))
    guest.monitor('disp compositor gl');guest.monitor('screen wait 500 10000')
    guest.monitor('screen shot '+str(shot))
    entry['untouched_png']=shot.name
    entry['untouched_png_sha256']=sha256(shot)
    # The program must be a real foreground job and receive the tty's signal.
    proof='resize-proof-'+str(sequence)
    cmd(shlex.join(['./type','127.0.0.1:0','winterm',
        '/tmp/xiri-resize-watch "$XIRI_SESSION_DIR/'+proof+'"\n']))
    wait('grep -q "^READY " "$job/'+proof+'"',30)
    base_width=width-80*cell_x
    cmd('./place winterm 10 180 '+str(base_width+66*cell_x)+' '+str(21*cell_y))
    wait('grep -q "^RESIZED " "$job/'+proof+'"',30)
    entry['foreground_resize']=get('cat "$job/'+proof+'"').splitlines()
    assert entry['foreground_resize']==['READY rows=24 cols=80 foreground=1','RESIZED rows=21 cols=66 SIGWINCH=1']
    cmd('./place winterm 10 180 '+str(width)+' '+str(height))
    if extra:
        launch='/emul/irix/usr/sbin/xwsh -name winterm -title winterm-check -geometry 100x30+20+80 -e /usr/libexec/xiri-shell "$XIRI_SESSION_DIR/extra-handoff"'
        cmd(shlex.join(['./type','127.0.0.1:0','winterm',
            launch+' >"$XIRI_SESSION_DIR/extra.out" 2>"$XIRI_SESSION_DIR/extra.err" & echo $! >"$XIRI_SESSION_DIR/extra.pid"\n']))
        wait('test -s "$job/extra-handoff" && xwininfo -name winterm-check >/dev/null',60)
        entry['extra_handoff']=get('cat "$job/extra-handoff"')
        assert re.search(r'rows=30 cols=(98|100)\b',entry['extra_handoff']),entry['extra_handoff']
        cmd(shlex.join(['./type','127.0.0.1:0','winterm-check',
            'stty size >"$XIRI_SESSION_DIR/extra-size"\n']))
        wait('test -s "$job/extra-size"',30)
        assert get('cat "$job/extra-size"').strip()=='30 100'
        pid=int(get('cat "$job/extra.pid"').strip())
        started=time.monotonic()
        cmd(shlex.join(['./type','127.0.0.1:0','winterm-check','exit\n']))
        # The launching native interactive shell reaps background jobs when
        # it next processes input. Require a successful wait, then no PID.
        cmd(shlex.join(['./type','127.0.0.1:0','winterm',
            'wait "$(cat "$XIRI_SESSION_DIR/extra.pid")"; echo $? >"$XIRI_SESSION_DIR/extra-exit"\n']))
        wait('test -s "$job/extra-exit"',30)
        assert get('cat "$job/extra-exit"').strip()=='0'
        wait('! kill -0 '+str(pid)+' 2>/dev/null',30)
        cmd('! xwininfo -name winterm-check >/dev/null 2>&1')
        entry['normal_exit']=dict(pid=pid,process_gone=True,window_gone=True,seconds=round(time.monotonic()-started,2))
        entry['exit_stderr']=get('cat "$job/extra.err"')
        assert not entry['exit_stderr'],entry['exit_stderr']
    record['winterm'].append(entry)
    print('Winterm untouched geometry, foreground resize'+(' and normal exit' if extra else '')+' passed',flush=True)
    return entry
