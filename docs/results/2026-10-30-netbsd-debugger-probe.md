# NetBSD debugger and automated probe — 2026-10-30

Cross-GDB attached to IRIS, stopped at two NetBSD kernel breakpoints, and
read the custom build identifier from memory. After detaching and resuming,
the guest completed boot and passed an unattended filesystem probe. The
same probe also passed in ordinary execution with Newport enabled.

## Inputs and host tools

The emulator, kernel, and guest configuration are unchanged from the
[kernel build record](2026-10-30-netbsd-kernel.md). Every automated run
copies the stopped custom-kernel disk and NVRAM into a new directory under
`.work/netbsd-probes/`; no RAM snapshot is used.
The checkpoint disk and NVRAM hashes were unchanged after the experiments.

| Input | SHA-256 |
| --- | --- |
| `.work/indy-netbsd-kernel/disk.raw` | `269038c7b77660c83d3835208fc0b2702c93110c14b3c55a42416f51672cee2a` |
| `.work/indy-netbsd-kernel/nvram.bin` | `ee883474d52f09278287b2044f7aeca61d2e7bc39c0bb8fd85c983ab64063d15` |
| TFTP kernel and guest `/netbsd` | `2428f60fbf6f830dcddd031b8540d0d52cbb458ee6a0166b257b0bae9941ed6c` |
| Debug kernel `netbsd.gdb` | `760b1f920541a8de6807e06a5e581745ad4116be6757fd3217fb6df080f15726` |
| 128 KiB probe payload, byte values 0–255 repeated 512 times | `59f410ae5e17962412e2aed4f815918f634932f2abf084f00bb638c4db017850` |

Fedora's `gdb-18.1-1.fc44` lacks MIPS support. The working debugger is
GDB 15.1, built from the verified NetBSD 11.0 source with `MKCROSSGDB=yes`,
target `mipseb--netbsd`, and Expat support. Use
`./scripts/build-netbsd-kernel.sh gdb`; its log is
`.work/netbsd-build/tools-gdb.log`.

Two build issues were resolved without changing source code: install host
`texinfo-7.2-9.fc44` for GDB documentation, and restore the executable bit
on `external/gpl3/gdb/dist/gdb/make-init-c`. The release set supplied that
helper as 0644. XML support uses `expat-devel-2.9.0-1.fc44`. Failed build
logs remain as `tools-gdb-missing-texinfo.log` and `tools-gdb-script-mode.log`.
If adding Texinfo after an initial failed configure, remove only the generated
`.work/netbsd-build/obj/tools/gdb/.configure_done` before rerunning.

The ordinary run uses `xorg-x11-server-Xvfb-21.1.25-2.fc44` and
`xorg-x11-xauth-1.1.5-1.fc44`. Additional runtime libraries installed:
`libXcursor-1.2.3-4.fc44`, `libXi-1.8.3-1.fc44`,
`libXrandr-1.5.4-7.fc44`, `libXinerama-1.1.5-10.fc44`, and
`libxkbcommon-x11-1.13.1-2.fc44`, plus their dependencies. The initial
ordinary attempt failed before guest boot because `libXcursor` was missing.

## Debugger evidence

The [GDB settings](../../lab/indy-netbsd/debugger.gdb) select `mips:isa64`,
big endian, `n64` register presentation, and disable address masking, matching
IRIS's remote register description. The NetBSD kernel remains 32-bit; these
settings do not establish correct C ABI decoding or stack unwinding.

The [breakpoint script](../../lab/indy-netbsd/check-boot.gdb) derives the
addresses from `netbsd.gdb`, asserts the stopped PC, and prints registers,
instructions, and the build identifier. Observed output:

```text
XIRI_GDB_MAIN pc=0xffffffff88442740
sp: 0xffffffff88061f48
=> 0xffffffff88442740 <main>: addiu sp,sp,-80
0xffffffff8846e520 <kernel_ident>: "XIRI_INDY_20261030"
XIRI_GDB_ROOTCONF pc=0xffffffff8806b94c
=> 0xffffffff8806b94c <cpu_rootconf>: lui v0,0x8855
```

Continuing from `main` reached `cpu_rootconf`. IRIS leaves the CPU stopped
when GDB detaches, so the harness then sends monitor `start`. The guest
reached multiuser, passed the probe, synced and unmounted its filesystems,
and returned to the PROM menu. The initial manual experiment's logs remain
in `.work/indy-netbsd-debugger/`; automated runs retain `gdb.log` beside
their serial and emulator logs.

## Probe and failure handling

Run the [host harness](../../scripts/probe-netbsd.py) from the repository
root; [setup and commands](../../lab/indy-netbsd/README.md#automated-probes)
are retained with the lab. It uses `iris-ci` in CI mode and the normal TCP
serial console in ordinary mode. Ordinary execution has `ci = false` and
Newport enabled, with only the host window placed on Xvfb.

The [guest script](../../lab/indy-netbsd/probe.sh) checks the kernel
identifier and installed kernel hash, baseline marker checksum, active
swap, and a 128 KiB CD-to-disk copy followed by `sync` and a separate
checksum read. Successful output includes:

```text
XIRI_PROBE_OK
kern.configname = XIRI_INDY_20261030
3540535338 33 /root/xiri-probe
/dev/sd0b       32736        0    32736     0%    0
```

The host captures complete, uniquely tagged exit-status lines, avoiding
false success from echoed commands. A deliberate `exit 23` returns host
status 23. A sleeping command with a three-second deadline returns host
status 124 and records no completed guest exit status. Both cases were
interrupted or completed as appropriate and then shut down cleanly.

Cleanup verification exposed a Toolbox process boundary: terminating its
host launcher did not terminate the ordinary emulator and Xvfb. The harness
now records a dedicated process group inside the container using
`setsid --wait` and stops that group after the guest halt. The earlier
leftover processes were stopped after confirming the guest was cleanly
halted; subsequent runs verify the corrected cleanup.

## Recorded runs

All paths below are beneath `.work/netbsd-probes/`. The final process check
found no remaining IRIS, GDB, or Xvfb process. Each listed run returned to
the PROM after syncing disks and unmounting filesystems.

| Run directory | Outcome | Guest / host exit | Start to shell | Total |
| --- | --- | --- | ---: | ---: |
| `ci-smoke-f66yfr92` | Initial CI smoke passed | 0 / 0 | 78.219 s | 112.551 s |
| `ci-smoke-m_y4j1c9` | Repeated CI smoke and both GDB breakpoints passed | 0 / 0 | 79.210 s | 113.042 s |
| `ordinary-smoke-lrlte0vg` | Ordinary smoke and corrected process cleanup passed | 0 / 0 | 78.415 s | 111.980 s |
| `ci-exit-b97weptg` | Deliberate guest failure propagated | 23 / 23 | 85.475 s | 105.938 s |
| `ci-timeout-vdw7e5cy` | Three-second command timeout; clean guest shutdown | no completed status / 124 | 73.314 s | 95.899 s |

Start-to-shell includes preparation and login; total includes guest shutdown
and emulator cleanup. The final CI/debugger and ordinary smoke probes took
13.618 and 13.571 seconds respectively, including the probe CD mount.

## Scope

The results establish the host build → cold boot → debugger → automated
probe loop for this kernel and R4400 profile, with smoke-test agreement
between CI and ordinary execution. Runs overlapped on the host, so their
elapsed times are operational observations, not an emulator speed benchmark.

The small file probe does not qualify sustained disk I/O or persistence
of newly written data across a guest reboot. Larger HTTP transfers and NFS
remain unresolved from the installation experiment. R5000 cache handling,
entropy provisioning, host device-probing diagnostics, snapshots, guest X,
MAME comparison, and physical hardware remain separate work.
