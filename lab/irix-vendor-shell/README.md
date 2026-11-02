# Original IRIX /bin/sh

This checkpoint admits the measured static n32 ELF layout used by the
unmodified IRIX 6.5.22m `/bin/sh`. The supplied installation's `/bin/sh`
links to `/sbin/sh`; the import stores its resolved bytes at
`/emul/irix/bin/sh`. SHA-256:
`ab6dd5b0585aec1f0fc7147d14fb68cd81986c9a5996315d9d5f16fd4e570c57`.

NetBSD `xiri` commit `849755450135c6734bb61c4973d687d0c8060739`
also supplies chdir, System V process-group operations and SGI_GETSID.
The ordinary interactive winterm default remains NetBSD sh via the existing
native terminal handoff. This checkpoint primarily qualifies original-shell
command execution and catalog launch, not complete interactive job control.

## Build and test

Use a clean checkout of the pinned commit. The qualification checkout is
`.work/netbsd-vendor-shell-src`; it isolates this cycle from concurrent
Newport work in the shared fork. Preserve the older qualified builds.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-vendor-shell.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-vendor-shell.py --prepare-reference
```

The builder creates 38 loader cases, 20 ABI/process probes, an original
reference exec helper and 18 shell commands. It never modifies vendor bytes.
Use the established original-IRIX reference guest and its CI client to upload
`.work/irix-vendor-shell/reference-inputs.tar`, extract it under
`/tmp/xiri-vendor-shell`, and run `sh reference.sh` there. Download
`/tmp/xiri-vendor-shell-results.tar` to
`.work/irix-vendor-shell/reference-results.tar`. The generated script and
archive contain the complete commands; `scripts/probe-irix-reference-filetypes.py
--serve` supplies a disposable reference guest and its request queue.
Send `{"command":"SHUTDOWN"}` to that queue when finished.

Build the two kernel configurations sequentially, with at most two jobs:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-vendor-shell-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-vendor-shell-clean-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-vendor-shell-clean-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-vendor-shell/XIRI_IRIX_VENDOR_SHELL" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 scripts/build-netbsd-kernel.sh kernel
```

For o32 use `mipseb`, configuration `XIRI_IRIX_VENDOR_SHELL_O32`, and
`.work/netbsd-irix-vendor-shell-o32-clean-build` for build/TFTP output.
As with previous labs, toolchains must already be prepared with the build
script's `tools` operation in the chosen isolated output directory.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-vendor-shell.py --mode ci
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-vendor-shell.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-vendor-shell.py --mode ci --kernel-abi o32
```

The harness checks kernel/emulator pins, hashes the immutable icons seed,
copies it, verifies media inside the guest, runs before/after native/vendor
controls and saves raw observations before halting. Dynamic-loader regression
inputs come from `.work/irix-exec-align/probes` on LP64 and
`.work/irix-o32-runtime` on o32; the latter has its own 4 KiB-page contract.
New reproducible builds have different kernel timestamps/hashes; qualify
and record new pins rather than replacing the existing artifacts silently.

`lab/irix-4dwm/setup-pty.sh` now also creates a native null-device node under
`/emul/irix/dev`. This is native session setup, not an imported IRIX device
number. It prevents O_CREAT redirection from creating a regular `null` file
inside the emulation tree. The harness exercises this with the vendor shell
as both identities. The published icons CHD is unchanged.

See the [result](../../docs/results/2026-11-02-irix-vendor-shell.md) for
scope, evidence and remaining desktop behavior.
