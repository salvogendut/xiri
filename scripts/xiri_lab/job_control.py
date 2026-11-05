"""Job-control checks through winterm and the original IRIX shell in GNOME Terminal.

The caller supplies an authenticated xiritest desktop, $job, DISPLAY and
XAUTHORITY. All jobs belong to that desktop's descendant supervisor. Workers
also have their own lifetime limit. The caller must check after_logout().
"""
import re
import shlex
from . import sha256

SOURCES = {
    'lab/irix-job-control/job-worker.c': 'job-worker.c',
    'lab/irix-catalog/app.sh': 'job-app.sh',
}


def check(guest, directory, record, *, tools='/tmp/xiri-job-ui'):
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    entry = dict(status='running', shells={})
    record['job_control'] = entry
    job = get('printf %s "$job"').strip()
    entry['session'] = job
    base = job+'/job-control'
    worker = tools+'/job-worker'

    def type(text, window='winterm'):
        return cmd(shlex.join([tools+'/type', '127.0.0.1:0', window, text]), 90)

    def ready(path):
        wait('grep -q "^READY " '+shlex.quote(path), 30)
        text = get('cat '+shlex.quote(path))
        match = re.search(r'READY pid=(\d+) pgid=(\d+) sid=(\d+) tpgid=(-?\d+) uid=(\d+) foreground=(\d+)', text)
        assert match, text
        result = dict(zip(['pid', 'pgid', 'sid', 'tpgid', 'uid', 'foreground'], map(int, match.groups())))
        assert result['uid'] == 1234, result
        return result

    def absent(pid):
        wait('! kill -0 '+str(pid)+' 2>/dev/null', 30)

    def foreground(pid):
        # The first query must still identify a live process: two empty ps
        # outputs must never pass as an equality check.
        wait('kill -0 '+str(pid)+' && test "$(ps -p '+str(pid)+' -o pgid= | tr -d " ")" = '
             '"$(ps -p '+str(pid)+' -o tpgid= | tr -d " ")"', 30)

    def capture(label):
        path = directory/('jobs-'+label+'.png')
        guest.capture(path)
        entry.setdefault('screenshots', {})[path.name] = sha256(path)

    def shell(window, label):
        location = base+'/'+label
        type('jc='+shlex.quote(location)+'; mkdir "$jc"; '
             '(id -un; echo "$HOME"; pwd; echo $$; echo "$-"; echo "$0") >"$jc/proof"\n', window)
        wait('test -s '+location+'/proof', 30)
        proof = get('cat '+location+'/proof').splitlines()
        assert proof[:3] == ['xiritest', '/usr/people/xiritest', '/usr/people/xiritest'], proof
        assert 'i' in proof[4], proof
        assert 'm' in proof[4], proof
        result = dict(proof=proof, monitor_enabled_at_start='m' in proof[4])
        entry['shells'][label] = result
        # Explicit monitor mode is supported by the original IRIX /bin/sh.
        type('set -m\n', window)
        type(worker+' "$jc/foreground"\n', window)
        process = ready(location+'/foreground')
        assert process['foreground'] == 1, process
        assert process['pgid'] == process['pid'] and process['pgid'] != int(proof[3]), process
        guest.monitor('key ctrl+z')
        wait('ps -p '+str(process['pid'])+' -o stat= | grep -q T', 30)
        type('jobs >"$jc/stopped"; echo READY >"$jc/stop-ready"\n', window)
        wait('test -s '+location+'/stop-ready', 30)
        stopped = get('cat '+location+'/stopped')
        assert re.search(r'Stopped|Suspended', stopped, re.I), stopped
        type('bg %1; jobs >"$jc/background"\n', window)
        wait('grep -q "^CONT$" '+location+'/foreground', 30)
        background = get('cat '+location+'/background')
        assert re.search(r'Running', background, re.I), background
        type('fg %1; echo $? >"$jc/foreground-status"\n', window)
        foreground(process['pid'])
        guest.monitor('key ctrl+c')
        wait('test -s '+location+'/foreground-status', 30)
        assert get('cat '+location+'/foreground-status').strip() == '42'
        absent(process['pid'])
        events = get('cat '+location+'/foreground')
        assert '\nCONT\n' in events and events.endswith('INT\n'), events
        result['stop_resume'] = dict(worker=process, stopped=stopped, background=background, events=events, exit=42)

        type(worker+' "$jc/read" read & echo $! >"$jc/read.pid"\n', window)
        process = ready(location+'/read')
        assert process['foreground'] == 0, process
        wait('ps -p '+str(process['pid'])+' -o stat= | grep -q T', 30)
        # The original IRIX sh requests SA_NOCLDSTOP and polls child state
        # between input lines. Its first jobs command can still say Running;
        # the next prompt reflects the stop. Exercise separate prompt
        # interactions and require a confirmed stopped job before fg.
        type('jobs >"$jc/read-first"\n', window)
        wait('test -s '+location+'/read-first', 30)
        first_jobs = get('cat '+location+'/read-first')
        type('jobs >"$jc/read-stopped"\n', window)
        wait('test -s '+location+'/read-stopped', 30)
        stopped_jobs = get('cat '+location+'/read-stopped')
        assert re.search(r'Stopped|Suspended', stopped_jobs, re.I), stopped_jobs
        type('fg %1; echo $? >"$jc/read-status"\n', window)
        foreground(process['pid'])
        type('x\n', window)
        wait('test -s '+location+'/read-status', 30)
        assert get('cat '+location+'/read-status').strip() == '0'
        absent(process['pid'])
        events = get('cat '+location+'/read')
        assert events.endswith('READ\n'), events
        result['background_read'] = dict(worker=process, first_jobs=first_jobs,
                                         jobs=stopped_jobs, events=events, exit=0)

        type(worker+' "$jc/reaped" exit & child=$!; wait "$child"; echo $? >"$jc/reaped-status"\n', window)
        wait('test -s '+location+'/reaped-status', 30)
        assert get('cat '+location+'/reaped-status').strip() == '37'
        process = ready(location+'/reaped')
        absent(process['pid'])
        result['background_wait'] = dict(worker=process, exit=37)
        type('echo Ctrl-Z, bg, fg, Ctrl-C and background wait passed\n', window)
        capture(label)
        print(label+': foreground groups, stop/resume, background read and wait passed', flush=True)
        return result

    cmd('xset r off; '+tools+'/place winterm 10 180 983 504')
    type('mkdir "$XIRI_SESSION_DIR/job-control"\n')
    wait('test -d '+base, 30)
    native = shell('winterm', 'native')
    type('jc='+shlex.quote(base)+'; mkdir "$jc/terminal"; '
         'XIRI_SESSION_STOP_FILE="$jc/terminal/stop" /usr/local/libexec/xiri/session-guard 600000 '
         '/bin/sh '+tools+'/job-app.sh "$jc/terminal" /usr/freeware/bin/gnome-terminal '
         '>"$jc/terminal/guard" 2>"$jc/terminal/guard.err" & echo $! >"$jc/terminal/guard.pid"\n')
    wait('xwininfo -name Terminal >/dev/null', 90)
    original = shell('Terminal', 'irix')
    type('exit\n', 'Terminal')
    wait('test -s '+base+'/terminal/guard', 30)
    guard = get('cat '+base+'/terminal/guard')
    assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ', guard), guard
    original['terminal_guard'] = guard
    type('wait "$(cat '+shlex.quote(base+'/terminal/guard.pid')+')"; echo $? >'+shlex.quote(base+'/terminal/wait-status')+'\n')
    wait('test -s '+base+'/terminal/wait-status', 30)
    assert get('cat '+base+'/terminal/wait-status').strip() == '0'
    absent(int(original['proof'][3]))
    cmd('! xwininfo -name Terminal >/dev/null 2>&1')

    # The existing real menu logout must clean up both kinds of job.
    type('jc='+shlex.quote(base)+'; '+worker+' "$jc/logout-running" & '
         +worker+' "$jc/logout-stopped"\n')
    running = ready(base+'/logout-running')
    stopped = ready(base+'/logout-stopped')
    guest.monitor('key ctrl+z')
    wait('ps -p '+str(stopped['pid'])+' -o stat= | grep -q T', 30)
    type('jobs >"$jc/logout-jobs"; echo Logout with running and stopped jobs\n')
    entry['logout_jobs'] = dict(running=running, stopped=stopped,
                               shell_pid=int(native['proof'][3]), jobs=get('cat '+base+'/logout-jobs'))
    capture('before-logout')
    entry['status'] = 'awaiting-logout'
    return entry


def after_logout(guest, directory, record):
    entry = record.get('job_control')
    if not entry or entry['status'] != 'awaiting-logout':
        return
    jobs = entry['logout_jobs']
    for pid in [jobs['running']['pid'], jobs['stopped']['pid'], jobs['shell_pid']]:
        guest.wait_for('! kill -0 '+str(pid)+' 2>/dev/null', 30)
    guard = guest.read_text('cat '+shlex.quote(entry['session']+'/guard.log'))
    assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ', guard), guard
    entry['logout_guard'] = guard
    archive = directory/'job-control.tgz'
    archive.write_bytes(guest.read('tar czf - -C '+shlex.quote(entry['session'])+' job-control identity handoff guard.log'))
    entry['archive'] = dict(path=archive.name, sha256=sha256(archive))
    entry['status'] = 'passed'
    print('Logout reaped the shell and its running/stopped jobs', flush=True)
