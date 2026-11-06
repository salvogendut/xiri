"""Bounded multi-user FAM and per-home desktop checks in the disposable guest."""
import re
import shlex

USERS = {'xiritest': 1234, 'xiritest2': 1237}


def check_fam(guest):
    cmd, get = guest.command, guest.read_text
    cmd('cc -O2 -Wall -Wextra -Werror /cdrom/multiuser-test.c -o /tmp/xiri-fam-multiuser && '
        'chmod 755 /tmp/xiri-fam-multiuser && '
        'mkdir -p /var/tmp/xiri-fam-group /var/tmp/xiri-fam-root && '
        'chown root:xiritest-extra /var/tmp/xiri-fam-group && '
        'chmod 750 /var/tmp/xiri-fam-group && chmod 700 /var/tmp/xiri-fam-root && '
        'touch /var/tmp/xiri-fam-group/group-marker /var/tmp/xiri-fam-root/root-marker', 180)
    before = get('sha256 /etc/passwd /etc/master.passwd /etc/group')
    cmd('/usr/local/sbin/xiri-sync-users && /usr/local/sbin/xiri-sync-users')
    assert before == get('sha256 /etc/passwd /etc/master.passwd /etc/group')
    cmd("awk -F: '$2 != \"*\" {bad=1} END {exit bad}' /emul/irix/etc/passwd /emul/irix/etc/group")
    for user in USERS:
        cmd(shlex.join(['su', '-l', user, '-c',
            'umask 077; mkdir -p "$HOME/.xiri/fam-private"; touch "$HOME/.xiri/fam-private/private-marker"']))
    port = get("rpcinfo -p 127.0.0.1 | awk '$1==391002 && $2==1 && $3==\"tcp\" {print $4}'").strip()
    assert port.isdigit()
    starts = []
    for user, uid in USERS.items():
        other = next(name for name in USERS if name != user)
        command = shlex.join(['/tmp/xiri-fam-multiuser', port,
            f'/usr/people/{user}/.xiri/fam-private', f'/usr/people/{other}/.xiri/fam-private',
            '/var/tmp/xiri-fam-group', '/var/tmp/xiri-fam-root', str(USERS[other])])
        starts.append(shlex.join(['su', '-l', user, '-c', command]) + f' >fam-{user}.log 2>&1 & fam_test_{uid}=$!')
    cmd('; '.join(starts))
    # Both sockets stay active while each client creates and removes a file.
    # Guest.read_text pipes its command through gzip in a child shell. Wait
    # in the owning serial shell, then transfer its recorded statuses.
    cmd('{ wait "$fam_test_1234"; echo first=$?; wait "$fam_test_1237"; echo second=$?; } >fam-status', 90)
    status = get('cat fam-status')
    logs = {user: get(f'cat fam-{user}.log') for user in USERS}
    for user, uid in USERS.items():
        assert f'FAM_MULTIUSER_PASS uid={uid} ' in logs[user], logs[user]
    assert status.splitlines() == ['first=0', 'second=0'], status
    service = get("grep 'local/native uid' /var/log/xiri-fam.log")
    for uid in USERS.values():
        assert re.search(fr'local/native uid {uid} gid {uid}\.', service), service[-3000:]
    return dict(status='passed', concurrent_clients=logs, native_databases_unchanged=True,
                emulation_passwd=get('cat /emul/irix/etc/passwd'),
                emulation_groups=get('cat /emul/irix/etc/group'), service_log=service)


def check_home(guest, user):
    uid = USERS[user]
    other = next(name for name in USERS if name != user)
    command = ('set -eu; test "$HOME" = /usr/people/'+user+'; test "$PWD" = "$HOME"; '
        'test "$(readlink "$HOME/Desktop/UnixRoot")" = /; '
        'test "$(readlink "$HOME/Desktop/'+user+'")" = "$HOME"; '
        'test "$(readlink "$HOME/Desktop/dumpster")" = ../dumpster; '
        'test -f "$HOME/dumpster/.dumpster"; '
        'test ! -r /usr/people/'+other+'/.xiri/multiuser-note; '
        'test ! -e "$HOME/Desktop/'+other+'"; '
        'if test -e "$HOME/.xiri/multiuser-note"; then '
        'test "$(cat "$HOME/.xiri/multiuser-note")" = '+user+'; else '
        'echo '+user+' >"$HOME/.xiri/multiuser-note"; fi; '
        'find "$HOME/.xiri" "$HOME/Desktop" "$HOME/dumpster" ! -user '+str(uid)+' -print')
    # su supplies the same native identity and home independently of the UI.
    # The winterm proof in ready() verifies the actual graphical session too.
    guest.command(shlex.join(['su', '-l', user, '-c', command])+' >home-owner-check')
    unexpected = guest.read_text('cat home-owner-check').strip()
    assert not unexpected, unexpected
    guest.command('test "$(stat -f %u "$job")" = '+str(uid)+' && '
                  'test "$(stat -f %Lp "$job")" = 700')
    return dict(user=user, uid=uid, home='/usr/people/'+user, private_state=True,
                owner_verified=True, desktop_links=True,
                state_listing=guest.read_text('ls -la /usr/people/'+user))
