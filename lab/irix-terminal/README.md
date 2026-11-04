# GNOME Terminal and original IRIX shell

The [cycle report](../../docs/results/2026-11-04-irix-terminal.md) records
the initial application observations. The subsequent
[termios report](../../docs/results/2026-11-04-irix-termios.md) qualifies the
original IRIX shell's prompt, foreground commands, Ctrl-C, resize and exit.
This cycle follows the GNOME/gedit Unix-socket work. The original terminal
first fails at IRIX `socketpair` (1155), before a child exists. After that
interface works, its child needs the original `gnome-pty-helper`, native PTY
ownership and the libc `ptsname` master check, then legacy descriptor passing.
The terminal's generic “unable to fork” message does not identify which of
these operations failed.

The independent fixtures in this directory use no vendor source. Build them
with `python3 scripts/build-irix-terminal.py`; `--suite` selects one suite.
Each produces a 1,024-byte big-endian record in o32/n32, direct/indirect forms.
Use `lab/irix-process/runner.c` in the guest to bound each execution, capture
return registers/output and verify that its process group is absent afterward.
Run as root and UID/GID 1234. The reference and native runs use identical ELF
bytes, verified by their manifests.

| Fixture | Coverage |
| --- | --- |
| `socketpair.c` | Stream exchange, EOF, names, allocation/copyout failures, repeated failure cleanup and unsupported families/types/protocols |
| `rights.c` | One complete legacy descriptor, invalid descriptor/input, unsupported capacities/counts/flags and receive-copyout cleanup |
| `ptm.c` | Measured I_STR 0x5064 request on `/dev/ptmx`, `/dev/ptc`, ordinary files and invalid descriptors/pointers; bounded unsupported fields |
| `rights-peer.c` + `native-peer.c` | Independent native SCM_RIGHTS sender: one descriptor, two rejected descriptors, rights-buffer fault and data-buffer fault; verify descriptor counts after every receive |
| `termios.c` | Four legacy/modern termio/termios families, get/set/drain/flush selectors, flags, controls, rates, descriptor errors and guarded pointer faults |
| `tty-session.c` | Automatic controlling-terminal acquisition, O_NOCTTY, non-leader open, session/group queries, group setting and descriptor/pointer errors |

`reference.json` retains 240 observations from original IRIX 6.5.22m and
its clean halt. A preceding broad malformed-rights experiment crashed the
original reference kernel; its precise failing mode was not captured. The
valid reference set deliberately excludes those malformed inputs. Original
truncated rights can leak descriptors and peeking can expose an internal
handle; these behaviors are not reproduced. Explicit subset policies are
checked separately from byte-for-byte reference parity.

Build the module in a separate output copied from the qualified GNOME build,
with its nbmake wrappers adjusted to the new object paths:

```sh
python3 scripts/build-irix-module.py --build .work/netbsd-terminal-build
python3 scripts/build-irix-terminal.py
python3 scripts/stage-irix-terminal.py
```

The stager mounts the supplied IRIX raw image read-only with `ro,norecovery`.
It copies only `/usr/freeware/sbin/gnome-pty-helper`, unchanged, into the same
path beneath `/emul/irix`. The resource ledger records its bytes, original
0755 mode, applied 0555 mode and root ownership. It imports no setuid mode,
user settings or accounting database. Keep the payload and vendor binaries
in ignored `.work`, not Git.

Use `scripts/probe-irix-catalog.py --partition 0 --interactive` with
`--module-build .work/netbsd-terminal-build`, the fixture archives as
`--extra-file`, and `--pty-setup runtime/libexec/setup-pty.sh`. The latter
installs and runs the candidate setup before graphical login. `--seed`
accepts only a cleanly halted earlier catalog guest whose base CHD matches.
The unchanged manual image, core kernel and pinned emulator remain separate
from this candidate. The guard owns every launched application and descendant.

Run each fixture separately under the bounded runner. For rights fixtures,
provide `input.txt` containing exactly `RIGHTS`. Preserve the native records
as `SUITE-native-v4.tgz`, with `ABI-FORM-MODE-UID.log` and `.err`, plus the four
ELFs under `bin/`. Compile `native-peer.c` natively with
`cc -O2 -Wall -Wextra -Werror`. Run the peer under the same runner, passing the
absolute foreign ELF path and mode after `--`; it forks the receiver on an
inherited Unix socket and sends native ancillary data. Archive its source
and native executable alongside the foreign ELFs.

```sh
python3 scripts/qualify-irix-terminal.py \
  --reference lab/irix-terminal/reference.json \
  --native-dir RESULTS-DIRECTORY --native-run GUEST-DIRECTORY \
  --peer-manifest .work/irix-rights-peer/probes/manifest.json \
  --output RESULT.json
```

`--archive-suffix` selects another recorded run. `--diagnostic` permits a
still-running guest; the final qualifier requires a clean halt and an unchanged
source CHD. Existing Unix-stream and IPv4 regressions are separate checks.
A raw ABI pass is not a terminal application pass: verify actual shell input,
window resizing, foreground process behavior, normal exit, catalog launching
and descendant cleanup, and retain a PNG before advancing its checklist entry.

For the separate native-shell control, select the existing handoff using
`gnome-terminal --execute /usr/libexec/xiri-shell REPORT`, with a fresh,
user-writable report pathname. This supplied terminal's `-e` option does not
split a combined command/argument string. The normal catalog entry still
uses the original IRIX shell. The subsequent termios cycle now verifies that
shell's interactive behavior separately; the native handoff does not
implement foreign termios. The glynx and Midnight Commander launchers
also require the actual `lynx` and `mc` executables and package resources.

## Terminal attributes and session acquisition

Build the newer module in `.work/netbsd-termios-build`, preserving the
qualified core and earlier module outputs. `termios-build.json` records its
inputs and artifact hashes. This cycle adds no vendor payload and uses the
already installed original PTY helper and native-root slave symlink.

```sh
python3 scripts/build-irix-terminal.py --suite termios --suite tty-session
python3 scripts/build-irix-module.py --build .work/netbsd-termios-build
```

Unlike the older single-mode fixtures, `termios` takes four arguments:
`command fd-kind pointer-kind variant`. The 108 rows in
[`termios-cases.json`](termios-cases.json) are the exact tested arguments.
Run each row in all four ABI/trap forms as root and UID/GID 1234, for 864
observations. Provide a writable `input.txt` in the working directory.
The fixture allocates and unlocks its own PTY, opens the slave with O_NOCTTY,
and establishes explicit common settings before the operation under test.

Descriptor kinds are slave (0), master (1), regular file (2), null device
(3) and invalid descriptor (4). Pointer kinds are valid (0), null (1), high
address (2), a boundary crossing into an inaccessible page (3), read-only
(4) and unaligned (5). Variants select baseline settings (0), raw VMIN/VTIME
(1), alternate flags (2), disabled/changed controls (3), changed rates (4)
and an ignored legacy line byte (5). Some variants do not change fields in
every structure; the case list retains those observations explicitly.

Each 1,024-byte record stores the request and identities at words 0–6,
the target return-register triple at word 26, the target buffer/guard bytes
at byte 256 and the final modern termios buffer at byte 512. Setup and
cleanup have separate return triples. The qualifier checks actual outcomes,
flags, rates, controls, guard bytes and unchanged state after failed setters.

`tty-session` takes a single mode 0–7 and contributes 64 observations. Its
child attempts setsid and opens the PTY slave; modes exercise acquisition,
O_NOCTTY, a non-leader, master/bad/file descriptors, a null output pointer
and an absent foreground group. Native credentials and tty ownership decide
whether acquisition or group changes are permitted.

On original IRIX, run the ELF directly and save `NAME.out`, `NAME.err` and
`status-UID.txt` containing `NAME STATUS`. On NetBSD, use the existing
bounded runner and retain `NAME.log`/`.err`. Attribute names are
`ABI-FORM-CMDHEX-KIND-POINTER-VARIANT-UID`; session names are
`ABI-FORM-MODE-UID`. Both archives contain the four matching ELF files at
their root. Archive the directory itself to avoid IRIX's argument-list limit.
The compact reference JSON files preserve measured fields and raw-archive
hashes; the raw local archives remain required by the qualifier.

The disposable original-IRIX reference creates the test account with UID/GID
1234 and permits that account to open `/dev/ttyq[0-9]*` and `/dev/ttyr[0-9]*`
by setting those clone-local nodes to mode 0666. This is fixture preparation,
not a proposed runtime permission policy. The fixture still unlocks each
allocated master with I_STR/UNLKPT before opening its slave. Initial attempts
without that unlock returned EACCES and are excluded from the accepted matrix.
The supplied source image is not edited.

```sh
python3 scripts/qualify-irix-termios.py \
  --reference .work/termios-cycle/reference.tar \
  --native .work/termios-cycle/native-v2.tgz \
  --reference-run .work/termios-cycle/reference/ci-g28ef6hy \
  --native-run .work/catalog-cycle/survey-0-0pqvd7q7 \
  --output termios-result.json
python3 scripts/qualify-irix-termios.py --sessions \
  --reference .work/termios-cycle/session-reference.tar \
  --native .work/termios-cycle/session-native-v2.tgz \
  --manifest .work/irix-tty-session/probes/manifest.json \
  --reference-run .work/termios-cycle/reference/ci-g28ef6hy \
  --native-run .work/catalog-cycle/survey-0-0pqvd7q7 \
  --output tty-session-result.json
```

Final qualification requires both clean halts and an unchanged source CHD.
`--diagnostic` permits a still-running native guest and labels its output
accordingly. The explicit comparison policies omit only undefined termios
padding and retained legacy baud bits in modern flags, and allow native
EPERM where IRIX returns EINVAL for an absent foreground group. Full flags,
controls and explicit modern rates remain checked.

For the application test, launch the original GNOME Terminal without a shell
override. Use real X input to check `$-` includes `i`, HOME/cwd, a fresh command
proof, Ctrl-C, resize and typed `exit`. Compile `interrupt-watch.c` natively
and run it as a foreground child of the original shell; its report checks
foreground membership and actual SIGINT delivery. Use the existing
`lab/irix-winterm-reliability/resize-watch.c` for SIGWINCH. After Ctrl-C, type a
fresh command: an interactive shell can discard the rest of an interrupted
compound line. A missing marker from that discarded line is not evidence
that the shell hung. Keep failed test attempts as diagnostics.
