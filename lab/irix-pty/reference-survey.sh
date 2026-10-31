#!/bin/sh
# Disposable original-IRIX guest only; no host device nodes are touched.
set -u
ulimit -c 0
mkdir -p /tmp/xiri-pty
cd /tmp/xiri-pty || exit 1
(uname -R; id; ls -l /dev/ptc /dev/ptmx /dev/ttyq0 /dev/ttyp0; command -v cc; command -v gcc; ls -l /usr/bin/script /usr/bsd/script /usr/sbin/par) >inventory.txt 2>&1
for exe in /usr/bin/script /usr/bsd/script; do
    if test -x "$exe"; then
        SHELL=/bin/sh /usr/sbin/par -s -SS -t 8 -o script.trace "$exe" script.typescript </dev/null >script.out 2>script.err & child=$!
        (sleep 12; kill -9 "$child" 2>/dev/null) & watchdog=$!
        wait "$child"; echo SCRIPT_RC=$? >status.txt
        kill "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null
        break
    fi
done
ls -l >files.txt
tar cf /tmp/xiri-pty-results.tar .
