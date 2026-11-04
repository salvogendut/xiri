# GNOME startup diagnosis

The [cycle report](../../docs/results/2026-11-04-irix-gnome.md) records the
bounded gedit document pass and the remaining resource/preferences work.
The [build](build.json) pins the Unix-stream module without changing the
qualified N64 kernel. The [resource ledger](resources.json) records all
50 imported paths and preserves its staging status separately from the
application observations.

The catalog survey found nine busy launch targets without windows, including
three routes to GNOME Terminal. This lab starts with the original gedit 0.9.7
binary on the qualified GIMP image, as UID/GID 1234 in a fresh xiritest home.
The initial trace identifies repeated `socket(1, 2, 0)` failures with IRIX
`EAFNOSUPPORT`, followed by `close(-1)`. Sampled library addresses place the
caller in ORBit's Unix listener initialization. This is evidence for gedit;
other programs require their own repeated observations.

`sample.c` is a bounded native NetBSD diagnostic, not an application launcher.
It captures 13 register/memory samples, then kills and reaps its child. It uses
the pinned N64 kernel's 38 64-bit ptrace register slots with an overflow guard.
Compile with `cc -O2 -Wall -Wextra -Werror`. Run a native `/bin/sleep 20`
control first. Arguments are `UID GID ENV_FILE EXECUTABLE [ARGS...]`; the
environment file contains one `NAME=value` per line. The child changes to
`/usr/people/xiritest`. Use only a process whose independent untraced run
established that no descendants escape this child-only sampler. The catalog
guard owns and checks the complete process tree in ordinary launch tests.

The maintained sampler also clears reaped child identities, validates IDs
before forking, and defers signal cleanup to normal control flow. To exercise
it in a writable native guest directory, compile it as `/tmp/gnome-sample`,
create an `env` file containing HOME and PATH, and run
`sh sampler-controls.sh` as root. The controls cover 13 sleep samples,
early normal exit, failed exec, invalid identity input and SIGTERM cleanup.
The earlier diagnosis's exact sampler bytes remain pinned in the baseline
record; the maintained helper has separate control evidence.

`unix.c` is independent, freestanding syscall code. Build o32/n32 direct and
indirect variants with `python3 scripts/build-irix-unix.py`. Each execution
writes a 2,048-byte big-endian record containing return registers, identities,
guarded socket-name buffers, and transferred stream bytes. Modes 0–4 exercise
bind/listen/connect/accept, named and unnamed sockets, output truncation and
negative capacities, ordinary read/write and legacy sendmsg/recvmsg. Other
modes inspect unsupported types/protocols and malformed input addresses.

Run each fixture in a separate writable directory using the bounded native
`lab/irix-process/runner.c`, as root and UID/GID 1234. A normal stream run
needs no child peer: connect queues one connection before accept. Original
IRIX observations use the same ELF bytes and raw record format. The qualifier
distinguishes original-IRIX parity from explicitly bounded subset policies;
successful startup is not a functional application pass.

The catalog harness accepts repeatable `--extra-file` inputs for its read-only
CD. `--module-build` installs a candidate module into the disposable CHD copy,
checks that its core kernel hashes match, halts cleanly, and cold-boots that
copy before the normal desktop and native controls. Its two boot logs are
retained separately. The qualified source CHD is checked again at shutdown.
Pass `--interactive` to use its request/response queue for additional checks.
`--seed` clones an earlier cleanly halted catalog guest's overlay; the base
CHD must still match the qualified bundle. A candidate already present on disk
is checked after cold boot, without an unnecessary second installation boot.

Keep original binaries, resources, traces, and disk overlays under ignored
`.work`. Shut down every owned IRIS guest after the cycle. Any successful
application check must include a PNG, a useful operation, persistence, normal
exit, catalog launching and process cleanup before claiming support.

For this build, copy the qualified `.work/netbsd-gimp-build` output into a
separate `.work/netbsd-gnome-build` directory and adjust its nbmake wrapper
to use the new object/destination paths before invoking:

```sh
python3 scripts/build-irix-module.py --build .work/netbsd-gnome-build
python3 scripts/build-irix-unix.py
python3 scripts/stage-irix-gnome.py
python3 scripts/probe-irix-catalog.py --partition 0 --interactive \
  --module-build .work/netbsd-gnome-build \
  --extra-file lab/irix-process/runner.c \
  --extra-file .work/irix-unix/probes/o32-direct \
  --extra-file .work/irix-unix/probes/o32-indirect \
  --extra-file .work/irix-unix/probes/n32-direct \
  --extra-file .work/irix-unix/probes/n32-indirect \
  --extra-file .work/irix-gnome-resources/payload.tgz
```

The printed guest directory provides the normal request/response queue.
Compile the native runner with warnings treated as errors, and run all
17 modes from the fixture manifest in separate writable directories as
root and UID/GID 1234. Retain each runner stdout/stderr and archive them as
`ABI-FORM-MODE-UID.log`/`.err`. These records include execution status,
exact 2,048-byte output and process-group cleanup. Verify the fixture bytes
against the original [reference manifest](reference.json) before comparing:

```sh
python3 scripts/qualify-irix-unix.py \
  --reference lab/irix-gnome/reference.json \
  --native NATIVE-RESULTS.tgz --native-run GUEST-DIRECTORY \
  --output RESULT.json
```

Original IRIX capture is a separate isolated reference guest using the same
ELF bytes. Its records retain the mode-28 filename-reuse limitation; those
cases test an explicit native path-length policy, not IRIX parity. The final
qualifier requires a clean halt and an unchanged source CHD. Use
`--diagnostic` only while the native guest is still running.

For gedit UI acceptance, install `/cdrom/payload.tgz` at the root of the
disposable guest and verify all manifest hashes, ownership and modes. Log in through
xdm as xiritest. Save two lines as `~/xiri-gedit-test.txt`, quit, reopen in a
fresh process and inspect the text. Quit again, double-click Freeware's
gedit entry, use its Open dialog to reopen the document, append a line and
save over it. Verify the exact bytes and UID/GID 1234, then use Exit and
check the PID/window disappearance and FAM Executing/Exited events. Preserve
before/running/after icon PNGs. The Applications alias remains a separate
catalog click to qualify. The later
[preference cycle](../../docs/results/2026-11-04-irix-preferences.md) adds
measured rename support and verifies gedit tab-width and GNOME Terminal
settings across normal exit/relaunch. Its expanded
[resource ledger](preferences-resources.json) adds the original terminal
preferences dialog. Help/image warnings remain separate limitations.
