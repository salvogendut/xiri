# Original installer after time support

Original `inst` now receives successful `time(1013)` and `gettimeofday(1128)`
returns on NetBSD `xiri` source `76de548ab644cb471f4c5b97ec89671c1d385c5b`.
The unchanged distribution dry run still reaches its 30-second watchdog.
This removes the previously observed time ENOSYS errors but does not establish
distribution reading or installation. The separate [xclock qualification](2026-11-01-irix-time.md)
checks actual visible time progression.

The [machine-readable report](2026-11-01-irix-installer-time.json) qualifies
`.work/irix-installer-time/runs/ci-q529e133`, a disposable clone of the stopped
desktop-pipe seed. Vendor files, distribution inputs, environment and commands
are unchanged from the [F_DUPFD retry](2026-11-01-irix-installer-dupfd.md):

```sh
inst -H
inst -n -M -r /emul/irix -f /cdrom/dist -c /cdrom/commands
```

The distribution trace pairs entry/return records by PID and LWP. Parent 486
creates child 555 with the same sproc flags. The child arms parent release,
duplicates pipe writers to descriptors 1 and 2, and executes native `/bin/sh`.
The native loader and libc name records confirm the ABI transition; A3 after
successful exec belongs to the replacement register image, not an errno flag.

The parent makes **54 successful gettimeofday calls** and **three successful
time calls**, with no ENOSYS from either. Twenty select calls remain, ending
with EINTR during watchdog cleanup. The actual result is still signal 9,
`killed=1`, empty stdout and the same 107-byte signal-handler warnings on
stderr. There is no observed `/cdrom/dist` name lookup. Hardware reporting
still prints an incomplete CPU profile, and its machfile mapping succeeds.

The shell still searches IRIX-style paths for `ls` and `mkdir`, omitting
NetBSD's `/bin`. The retained trace does not show either utility successfully
executing. The next investigation should capture helper arguments/output and
qualify the runtime path arrangement, then follow the parent's output/child
completion handling. Missing paths are an observation, not proof that they
alone explain the timeout. Signal registration, hardware/system information,
umask and creat also remain unsupported in this trace.

Four native execution controls pass before/after the attempts. The ordinary
account helper remains idempotent, with `/usr/people/xiritest` owned by UID1234
and mode0700. Native shell writes and foreign asa reads the same file; foreign
root retains `HOME=/`. Both test groups are absent afterward and the guest
halts cleanly. No new vendor resource was imported. Package installation,
Freeware registration and graphical-login persistence remain unqualified.

Reproduce with `scripts/probe-irix-installer-time.py`, then pass its run
directory to `scripts/qualify-irix-installer-time.py --output <report.json>`.
The report retains source/input hashes, actual exit records, syscall pairs,
helper searches and cleanup evidence. Large traces and vendor files stay in
`.work`; only the observations and hashes are committed.
