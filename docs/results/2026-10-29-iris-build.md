# IRIS CLI build — 2026-10-29

## Inputs

| Item | Recorded value |
| --- | --- |
| Host | Fedora Linux 44 Silverblue, x86-64; see [host inventory](2026-10-29-host-inventory.md) |
| Build container | Fedora Toolbox 44, `xiri-iris`; local image ID `e5cc31b2430bb12d2c68e35cd5e4a77831927cef49252246648e4946059aea66` |
| IRIS source | `techomancer/iris` at `b188bb9a82842948ddf2534f07d718df8473942c` (2026-10-29) |
| Rust toolchain | `nightly-2026-10-28-x86_64-unknown-linux-gnu`; `rustc 1.101.0-nightly (41089d07a 2026-10-27)`, LLVM 23.1.4 |
| Dependency lock | [`lab/iris/Cargo.lock`](../../lab/iris/Cargo.lock), SHA-256 `869a1499143fb349390f388c7cacf7039e9034e782f5ed4199c3402181a3e54a` |
| Cargo command | `cargo +nightly-2026-10-28 build --release --locked --bin iris --bin iris-ci` |
| Cargo features | Upstream defaults; no extra features, especially no `lightning`, `opcodefusion`, or `jitv2` |
| Build jobs | 8 |

Native packages installed in the Toolbox: `rustup-1.29.0-8.fc44`,
`pkgconf-pkg-config-2.5.1-1.fc44`, `alsa-lib-devel-1.2.16.1-1.fc44`,
`gcc-16.2.1-2.fc44`, `gcc-c++-16.2.1-2.fc44`, `make-4.4.1-12.fc44`, and
`clang-22.1.8-4.fc44` (all x86-64).

The source checkout was clean after the build. Upstream has no committed
`Cargo.lock`; the generated lockfile is retained in Xiri. Build inputs and
outputs are kept under `.work/` and excluded from Git. The repeatable command
is [`scripts/build-iris.sh`](../../scripts/build-iris.sh).

## Result

The release build completed in 2 minutes 29 seconds. `iris --help` and
`iris-ci --help` both exited successfully inside the Toolbox.

| Output | Size | SHA-256 |
| --- | --- | --- |
| `.work/target/release/iris` | 73 MiB | `b68b40e471187eb0adb605c3560102abaf11e68633757804259f0d76cb6ffed0` |
| `.work/target/release/iris-ci` | 6.2 MiB | `123458f4df3c64206d4a089a7e2f2da84c3e82d73f7b7b7cf34d7f560af84312` |

One upstream warning appeared: `Atomic::<usize>::fetch_update` is deprecated
in this nightly toolchain. There were no build errors. No PROM, NetBSD guest,
disk image, or emulator device path was exercised. Boot and I/O qualification
remain pending.
