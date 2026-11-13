#!/bin/sh
# Run as root on a disposable NetBSD guest, with no graphical user logged in.
set -eu
test "$(id -u)" = 0
base=$(mktemp -d /var/tmp/xiri-shutdown.XXXXXX)
chmod 755 "$base"
guard=/usr/local/libexec/xiri/session-guard
stop=/usr/local/libexec/xiri/stop-sessions
children=
cleanup()
{
    for file in "$base"/*/*.pid; do
        test -s "$file" || continue
        kill -TERM "$(cat "$file")" 2>/dev/null || :
    done
    for child in $children; do wait "$child" 2>/dev/null || :; done
}
trap cleanup EXIT
wait_file()
{
    tries=0
    until test -s "$1"; do
        tries=$((tries+1)); test "$tries" -lt 30
        sleep 1
    done
}
"$stop" >"$base/empty.log"
grep 'selected=0 remaining=0 valid=1' "$base/empty.log"
if su -l xiritest -c "$stop"; then exit 1; fi
for user in xiritest xiritest2; do
    dir=$base/$user
    mkdir "$dir"
    cat >"$dir/client" <<'EOF'
#!/bin/sh
echo $$ >client.pid
while :; do sleep 1; done
EOF
    cat >"$dir/save" <<'EOF'
#!/bin/sh
set -eu
kill -0 "$(cat client.pid)"
id -un >saved
EOF
    cat >"$dir/start" <<EOF
#!/bin/sh
cd '$dir'
echo \$\$ >desktop.pid
XIRI_SESSION_SAVE='$dir/save' exec '$guard' --desktop 0 '$dir/client'
EOF
    chmod 555 "$dir/client" "$dir/save" "$dir/start"
    chown -R "$user" "$dir"
    su -l "$user" -c "$dir/start" >"$dir/guard.log" 2>&1 &
    children="$children $!"
    wait_file "$dir/client.pid"
done
# Generic guards and separate processes of the same user are not desktops.
dir=$base/xiritest
cat >"$dir/unrelated" <<EOF
#!/bin/sh
cd '$dir'
echo \$\$ >generic.pid
exec '$guard' 0 /bin/sleep 300
EOF
chmod 555 "$dir/unrelated"
su -l xiritest -c "$dir/unrelated" >"$dir/generic.log" 2>&1 &
children="$children $!"
wait_file "$dir/generic.pid"
"$stop" >"$base/stop.log"
cat "$base/stop.log"
grep 'selected=2 remaining=0 valid=1' "$base/stop.log"
for user in xiritest xiritest2; do
    test "$(cat "$base/$user/saved")" = "$user"
    grep 'SESSION_SAVE completed=1 exit=0 ' "$base/$user/guard.log"
    grep 'absent=1 valid=1' "$base/$user/guard.log"
done
kill -0 "$(cat "$dir/generic.pid")"
"$stop" >"$base/after.log"
grep 'selected=0 remaining=0 valid=1' "$base/after.log"
# A stalled save remains bounded by the guard, and leaves no live descendants.
rm "$dir/client.pid"
cat >"$dir/save" <<'EOF'
#!/bin/sh
trap '' TERM
while :; do sleep 1; done
EOF
su -l xiritest -c "$dir/start" >"$dir/stalled.log" 2>&1 &
children="$children $!"
wait_file "$dir/client.pid"
start=$(date +%s)
"$stop" >"$base/stalled.log"
elapsed=$(($(date +%s)-start))
test "$elapsed" -lt 30
grep 'selected=1 remaining=0 valid=1' "$base/stalled.log"
grep 'SESSION_SAVE completed=0 exit=-1 ' "$dir/stalled.log"
grep 'absent=1 valid=1' "$dir/stalled.log"
kill -0 "$(cat "$dir/generic.pid")"
echo "SHUTDOWN_TESTS_OK elapsed=$elapsed evidence=$base"
