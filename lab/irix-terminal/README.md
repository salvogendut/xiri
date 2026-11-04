# GNOME Terminal child startup

The [cycle report](../../docs/results/2026-11-04-irix-terminal.md) records
the application observations and remaining interactive-terminal limits.
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
uses the original IRIX shell. Distinguish its command-input/exit checks from
a native prompt and foreground-job resize check; the native handoff does
not implement foreign termios. The glynx and Midnight Commander launchers
also require the actual `lynx` and `mc` executables and package resources.
