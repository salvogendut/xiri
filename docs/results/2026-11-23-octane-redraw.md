# Octane 4Dwm redraw latency

The Octane launchers now select a release build of IRIS with the R10000 CPU
JIT. The two NetBSD disks keep their original kernels, IRIX installations,
firmware and writable user overlays. Both tests used the CPU rasterizer for
IMPACT and the existing NetBSD HQ4 framebuffer driver.

From the Xiri checkout, run the launcher for your desktop.

```sh
.work/native/xiri-ip30-xdm-6.5.22-20261123/run-iris.sh
.work/native/xiri-ip30-xdm-6.5.30-20261123/run-iris.sh
```

At xdm, log in as `xiritest` with password `xiritest`. For comparison, this
command selects the previously qualified interpreter for the same 6.5.30 disk.

```sh
XIRI_IRIS="$PWD/.work/octane-fill/emulator/iris" .work/native/xiri-ip30-xdm-6.5.30-20261123/run-iris.sh
```

## Visible window redraws

The test logs in through xdm and alternately clicks the exposed title bars of
File Manager and winterm. Timing starts at mouse button-down and ends when
at least 99% of a 304×40 rectangle in the overlap shows the newly raised
window's colour. It checks the previous window is still visible before each
click. Each median uses seven raises after a warm-up. Times include guest
scheduling, 4Dwm, Xorg, HQ4 updates and host scanout polling.

| IRIX desktop | Window raised | Interpreter median | JIT median |
| --- | --- | ---: | ---: |
| 6.5.22 | File Manager | 441 ms | 289 ms |
| 6.5.22 | winterm | 571 ms | 213 ms |
| 6.5.30 | File Manager | 407 ms | 212 ms |
| 6.5.30 | winterm | 574 ms | 273 ms |

The 6.5.30 windowed pair also reached the xdm greeter in about 198 seconds
with the interpreter and 87 seconds with the JIT, measured from the creation
of the emulator serial log to the first greeter capture on each cold boot.

The 6.5.22 comparison used emulated scanout in headless mode. The 6.5.30
comparison used ordinary IRIS windows on Xvfb. The figures describe warm
window raises on this host. Several test guests ran concurrently.
On each release the windowed
guest logged in to 4Dwm and native ctwm, returned to xdm after logout,
and shut down to PROM. The native account retained wheel access.

[6.5.22 desktop](2026-11-23-octane-redraw-6.5.22.png) ·
[6.5.30 desktop](2026-11-23-octane-redraw-6.5.30.png) ·
[Samples, input hashes and qualification records](2026-11-23-octane-redraw.json)

## Reproduction

Both executables use IRIS `xiri` revision `08e53ba7`. This cycle fetched
`upstream/main` at `a05289ef`, already integrated in that revision. To
rebuild the JIT executable from the Xiri checkout with the fork's Rust
toolchain and native build dependencies installed, use the following commands.

```sh
export CARGO_TARGET_DIR="$PWD/.work/ip30-jit-build"
export CARGO_PROFILE_RELEASE_LTO=false CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 CARGO_PROFILE_RELEASE_DEBUG=0
(cd ../iris && cargo +nightly-2026-10-28 build --locked --release -p iris --features jitv2 --bin iris --bin iris-ci)
install -d .work/emulators/iris-ip30-jit-08e53ba7
install -m 755 "$CARGO_TARGET_DIR/release/iris" "$CARGO_TARGET_DIR/release/iris-ci" .work/emulators/iris-ip30-jit-08e53ba7/
```

For the automated scanout measurement, use the original test disk with its
saved session layout. The harness creates a private disk copy and write
overlay. Set `emulator=.work/octane-fill/emulator` and choose a fresh output
directory to repeat with the interpreter.

```sh
bundle=.work/native/xiri-ip30-xdm-6.5.30-20261123
emulator=.work/emulators/iris-ip30-jit-08e53ba7
IRIS_NO_IDLE=1 python3 lab/ip30-impact/disk.py qualify --measure-redraw \
  --board highimpact --disk "$bundle/netbsd-xiri.chd" --firmware "$bundle" \
  --emulator "$emulator" --kernel .work/octane-desktop/qualified/netbsd \
  --module .work/octane-desktop/qualified/compat_irix_o32.kmod \
  --loader .work/octane-xdm/ip30boot --output .work/octane-redraw-check-30
```

Use the separate 6.5.22 bundle and `--board solidimpact` for that release.
