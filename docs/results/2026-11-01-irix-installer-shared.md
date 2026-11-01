# Original installer passes mmap and reaches sproc

The original IRIX installer no longer crashes while formatting its first
message. With [shared mappings](2026-11-01-irix-mmap-shared.md), its 1 MiB
`0x141` mapping succeeds, `inst -H` prints a hardware report, and the distribution
dry run reaches target-directory preparation. It has **not read the selected
distribution or installed xmahjongg**.

The [independent evidence check](2026-11-01-irix-installer-shared.json) binds the
unchanged original binaries, new kernel pin, native controls, home checks,
ordered syscall traces and the libc instruction at the failing trap.
The disposable guest `ci-g026joky` halts cleanly, with both owned process groups
absent after their commands.

## Results

`inst -H` exits zero and prints:

```text
CPUARCH=

CPUBOARD=
MODE=32bit
GFXBOARD=SERVER
SUBGR=SERVER
```

This is incomplete hardware identification, not a qualified hardware profile.
It also warns that the CPU hardware/architecture are unrecognized. The original
`/var/inst/machfile` is opened and successfully mapped read-only with SHARED,
length 5025. It is already staged input; no additional hardware database was
imported or invented to suppress warnings.

Both commands emit warnings that SIGBUS and SIGSEGV are not handled for mmap.
The traces show `sigaction` trap1162 for signals 10 and 11 returning ENOSYS;
these messages are not evidence that either signal was delivered. There is no
new SIGBUS/SIGSEGV termination.

The dry run is unchanged:

```sh
inst -n -M -r /emul/irix -f /cdrom/dist -c /cdrom/commands
```

It prints:

```text
FATAL ERROR: Unable to start inst: Failed to create target directories:
        Unable to fork sub command: Function not implemented
```

It nevertheless exits zero. Acceptance therefore checks its output and trace,
not just exit status. The selected xmahjongg/fw_common distribution bytes remain
staged but unread; package history, hooks and Icon Catalog registration are
still unqualified.

## Next measured boundary

After two successful pipe calls, original libc `_nsproc` executes trap1129
(`sproc`) at `0x0fa75038`, with child entry `0x0fa750a8` and flags `0x03000040`.
The return is ENOSYS (IRIX errno 89). The existing historical NetBSD headers
identify the flags as `PR_SADDR | PR_BLOCK | PR_NOLIBC`. The instruction in the
supplied libc is independently verified as `syscall`.

No ordinary `fork` call fails on this path. Adding an alias to fork would not
establish the requested shared-address-space and blocking behavior. The next
step is to measure this specific sproc lifecycle on original IRIX, including
child entry/stack, parent release, PRDA handling, descriptor ownership and
exec/exit/error cleanup, before implementing a bounded adapter. This also
requires revisiting the current LOCAL/shared-vmspace guard rather than silently
weakening it.

Other observed missing calls remain recorded: signal registration, hardware
queries, `time`, `creat`, and later prctl operations. They are follow-up work;
this trace does not prove all of them are immediate fatal blockers. No return
values or vendor instructions were patched to skip them.

## Native home and reproduction

Original installer sessions use `HOME=/`. Native account creation/repeated
setup still uses `/usr/people/xiritest`, owner UID1234, mode0700 and native ksh.
Native ksh writes the shared file and original asa reads it. Four native ABI
controls pass before/after. Prior cold-boot home persistence remains recorded
in the [earlier checkpoint](2026-11-01-irix-installer.md); graphical login,
Freeware launch, session persistence and removal are still open. No new GUI
success or PNG is claimed by this command-line step.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-shared.py
# For a new run, use its reported directory instead of this retained run.
toolbox run -c xiri-iris .work/netbsd-irix64-build/tools/bin/mips64--netbsd-objdump \
  -d --start-address=0x0fa74f80 --stop-address=0x0fa75100 \
  .work/irix-freeware/installed/usr/lib32/libc.so.1 \
  >.work/irix-installer-shared/runs/ci-g026joky/libc-subcommand-disassembly.txt
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer-shared.py \
  .work/irix-installer-shared/runs/ci-g026joky \
  --output docs/results/2026-11-01-irix-installer-shared.json
```

The observer clones the previous clean ordinary desktop disk, checks inherited
resources, installs the matching new `/netbsd`, and runs with the pinned shared
mapping kernel. Source remains NetBSD `xiri` `7af1404388b9f2db84f97a114c9f003b7c50b094`.
