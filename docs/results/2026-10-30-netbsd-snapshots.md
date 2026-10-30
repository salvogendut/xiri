# NetBSD snapshot qualification — 2026-10-30

Snapshot restore passed in CI and ordinary execution after fixing a missing
RAM-map update in IRIS. The checks cover guest memory and files, pending timers,
fresh network transfers, a fresh emulator process, and a final cold boot of the
restored disk. NFS qualification is limited to 1024-byte requests; a fragmented
upload failed an integrity check during the investigation.

## Fresh-process restore failure

The original fork build `d642079` resumed saved state in the original process,
but fresh-process restore did not service serial input. The monitor showed
the saved MC `MEMCFG0` value `0x7f207f40`, while `phys map` still reported
physical `0x08000000`–`0x17ffffff` as unmapped RAM. The CPU ran into exceptions
instead of continuing the saved shell.

`MemoryController::load_state` restored register bytes without invoking the
callback that updates the board's physical RAM map. An emulator that had
already booted retained the PROM-established map, hiding the omission.
Rewriting the saved MEMCFG values through the monitor and restoring the same
snapshot recovered the shell (`XIRI_MANUAL_REMAP_OK`).

The fix republishes the decoded bank map after loading MC state and releasing
the MC and DMA locks. Its regression test loads a saved memory configuration
into a fresh controller, requires publication of both RAM banks, and checks
that the callback can inspect MC state without the MC lock being held.
The change lives in the user's IRIS fork on `xiri/netbsd-snapshots`.

Commit `b6d6f5c295aaccdb0bb614ee140447625a476498` contains the fix. All 11
`dev::mc::tests` passed, including the new callback regression and the existing
state round-trip. The locked release build succeeded with the pre-existing
REX3 deprecation warning.

| Input | SHA-256 |
| --- | --- |
| Fixed emulator | `c7018f090b643dafb9c58140558cc9d5dd1c8c3522a18591d1a40b4340fdfb58` |
| `iris-ci` | `c0492793d79caeb488c93b2e74f9ba0d5877e7935d3526f6794f3d4d58029159` |
| Original emulator retained in `.work/iris-nfs/iris` | `3b5951f0902c7787d348f396675437e1fa4b83f78ee8edd94878af1305f941b3` |
| Source checkpoint disk | `269038c7b77660c83d3835208fc0b2702c93110c14b3c55a42416f51672cee2a` |
| Source checkpoint NVRAM | `ee883474d52f09278287b2044f7aeca61d2e7bc39c0bb8fd85c983ab64063d15` |
| Kernel | `2428f60fbf6f830dcddd031b8540d0d52cbb458ee6a0166b257b0bae9941ed6c` |

## NFS integrity finding

An initial CI run produced a corrupted NFS upload after its second restore,
even though the guest command returned zero. The host-side SHA-256 check caught
the mismatch. The expected 4 MiB payload hash was
`3e5ddb0b40affcf368b2f37bfc13b991afd6a958b2d25c63e08dfe666b7d112d`;
the uploaded hash was
`51635389f02c1603c61ad2afe3236062e271df083aa7124fa6762367245f2627`.
Six 512-byte sectors differed, in two regions. Sample mismatched bytes matched
the source at an offset 1480 bytes later, the IPv4 fragment payload size.
That suggests a fragment or DMA-buffer issue; it does not establish its cause
or that snapshots are required to trigger it.

Other runs using the default 8192-byte NFS requests passed those transfers.
The corruption remains open. The snapshot harness therefore exposes
`--nfs-size 8192` for reproduction and defaults to 1024-byte reads and writes,
which fit within an Ethernet frame. The earlier larger-I/O pass remains a
historical observation, not evidence that fragmented NFS is reliable.

## Test design and retained artifacts

Run the [snapshot harness](../../scripts/qualify-netbsd-snapshot.py) using the
[lab instructions](../../lab/indy-netbsd/README.md#snapshot-qualification).
The R4400, 256 MiB RAM, Newport, custom kernel, stopped guest checkpoint,
toolchain, and default Cargo features match the preceding I/O experiment.
Every run has its own disk, NVRAM, ports, ISO, host services, and logs.

The capture occurs at a shell after completed transfers, with no active NFS
mount. It saves a shell variable and PID, a 4 MiB file, a second file to be
deleted, and a process sleeping for 12 seconds. After capture the harness
changes the variable, overwrites the payload with distinct bytes, deletes the
second file, creates another file, and waits for the timer to finish.

Restore must recover the variable and shell PID, original file hash, deleted
file, absent newly created file, and still-pending timer. The timer must fire
again, `sleep 2` must complete with an advancing guest clock, and 4 MiB HTTP
downloads plus NFS reads and writes must pass destination checksums. The
default CI run exercises two full restores and two in-memory rollbacks;
ordinary execution exercises two monitor loads with Newport enabled on Xvfb.

Both modes then exit the emulator, create a fresh process, and restore the
same saved state without booting NetBSD. After repeating the checks, the guest
writes a final marker and halts cleanly. Its overlay is committed only to a
separate disposable disk (`fresh/disk.raw`), which is cold-booted and checked
for a clean filesystem and persisted content. The snapshot base stays intact.

The saved format is schema 4, with postcard device state, chunked RAM and
framebuffer data under `saves/.cas/`, and the SCSI overlay plus `cow.toml`.
Keep the CAS directory and checkpoint together. IRIS's base checks include
size, not a content hash; reuse requires comparing Xiri's recorded SHA-256.
The snapshot contains the old kernel, so kernel changes still require a cold
boot. External NFS writes remain outside the snapshot.

## Initial failures retained

Paths are under `.work/netbsd-snapshots/`:

| Run | Outcome before the MC fix |
| --- | --- |
| `ci-xlm2a065` | Second-restore NFS upload checksum mismatch; clean guest halt |
| `ordinary-s0cd0wqv` | Two in-process restores passed; fresh-process restore timed out and required forced disposal |
| `ordinary-kxfs2e6k` | Repeated fresh-process failure; monitor confirmed exception state and queued serial input |
| `ci-loe6zdnr` | Two restores and two rollbacks passed; fresh-process failure recovered by manually republishing MEMCFG before another restore; excluded from automated acceptance |

All failures used disposable disks. Raw logs, monitor evidence, snapshots,
input hashes, and result files are retained alongside them.

## Passing runs with the fix

Both runs used the final harness and `b6d6f5c`, with `--nfs-size 1024` and two
rounds. Every guest check returned zero, all six guest sessions halted cleanly,
and both final cold boots reported a clean root filesystem. The original
custom-kernel checkpoint and each run's snapshot base retained their SHA-256
hashes. The committed cold-boot disks are separate files.

| Run directory | Mode and coverage | Host exit | Total |
| --- | --- | ---: | ---: |
| `ci-cvy17tht` | Three full restores (one in a fresh process), two in-memory rollbacks, timers, HTTP/NFS, final cold boot | 0 | 491.465 s |
| `ordinary-5xdxjcjl` | Three full restores (one in a fresh process), timers, HTTP/NFS, final cold boot | 0 | 412.078 s |

The ordinary full restores took 0.440, 0.740, and 0.501 seconds; CI full restores
took 3.211, 5.347, and 4.243 seconds, including rollback-checkpoint capture.
CI rollbacks took 3.410 and 3.370 seconds. These are host-command observations
from overlapping runs, not a controlled speed comparison. Guest clock checks
reported a two-second advance after `sleep 2`.

Each network check verifies a 4 MiB HTTP download and 4 MiB NFS transfers in
both directions. Including baseline transfers, the final runs checked 72 MiB
in CI and 48 MiB in ordinary mode. The default profile completed with matching
hashes throughout. Host-side NFS outputs from earlier restored states remain
present, as expected for external storage.

The final process check found no remaining emulator or Xvfb process. CI overlay
files were retained under each run's phase directories rather than left in the
container's `/tmp`. The saved snapshot, its CAS chunks, and unchanged base disk
remain available under each passing run for further inspection and restore.

## Scope

These checks cover idle-shell capture, state rewind, timers, new connections,
and clean-halt persistence on this exact profile. They do not qualify capture
during active I/O, existing TCP sessions, arbitrary NFS workloads, cross-build
or cross-architecture migration, power-loss recovery, guest X, MAME, or real
hardware. The installer HTTP stall and fragmented NFS integrity remain open.
