set -eu
/tmp/gnome-sample 1234 1234 env /bin/sleep 20 >native.log 2>native.err
test "$(grep -c '^SAMPLE index=' native.log)" = 13
grep -q 'END exit=-1 signal=9' native.log
test ! -s native.err
sampled=$(sed -n 's/^SAMPLE index=0 pid=\([0-9]*\).*/\1/p' native.log)
! kill -0 "$sampled" 2>/dev/null
/tmp/gnome-sample 1234 1234 env /bin/sleep 0 >early.log 2>early.err
grep -q 'END exit=0 signal=0' early.log
test ! -s early.err
set +e
/tmp/gnome-sample 1234 1234 env /no-such-xiri-test-executable >badexec.log 2>badexec.err
code=$?
set -e
test "$code" = 2
grep -q BAD_EXEC badexec.log
set +e
/tmp/gnome-sample no-user 1234 env /bin/sleep 0 >badid.log 2>badid.err
code=$?
set -e
test "$code" = 2
test ! -s badid.log
/tmp/gnome-sample 1234 1234 env /bin/sleep 20 >signal.log 2>signal.err & owner=$!
tries=0
until grep -q '^SAMPLE index=0' signal.log; do tries=$((tries+1)); test "$tries" -lt 20; sleep 1; done
sampled=$(sed -n 's/^SAMPLE index=0 pid=\([0-9]*\).*/\1/p' signal.log)
kill -TERM "$owner"
set +e
wait "$owner"
code=$?
set -e
test "$code" = 130
! kill -0 "$sampled" 2>/dev/null
printf 'SAMPLER_CONTROLS_OK\n'
