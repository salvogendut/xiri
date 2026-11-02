#!/bin/sh
set -eu
ulimit -c 0
cd /tmp/xiri-filetypes
trap 'tar cf /tmp/xiri-filetypes-results.tar .' 0
tar xf /tmp/seek-probes.tar
printf abcdefghijklmnopqrstuvwxyz >seek-file
chmod 444 seek-file
: >seek-status.txt
for binary in *-lseek; do
 for uid in 0 1234; do
  extra=; test "$uid" = 0 || extra=user
  rc=0; ./$binary $extra >"$binary-$uid.out" 2>"$binary-$uid.err" || rc=$?
  echo "$binary-$uid $rc" >>seek-status.txt
 done
done
/usr/freeware/bin/gcc --version >compiler.txt 2>&1
/usr/freeware/bin/gcc -mabi=n32 -mips3 -O2 -Wall fixture.c -Wl,-rpath,/usr/lib32/internal -L/usr/lib32/internal -limdFtrDB -o probe-n32 >build.txt 2>&1
./probe-n32 /usr/freeware/bin/xmahjongg /usr/bin/X11/xclock /usr/people /etc/passwd /usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg >reference.out 2>reference.err
