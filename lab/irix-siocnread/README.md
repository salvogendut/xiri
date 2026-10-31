# IRIX SIOCNREAD lab

This checkpoint measures syscall 1054, selector `0x4004730a`, which original
Toolchest calls while polling its X connection. The preceding
[diagnosis](../../docs/results/2026-10-31-irix-toolchest-siocnread.md) identifies
this as the next XIO boundary after the qualified fxstat adapter.

The synthetic probes cover o32/n32 and direct/indirect dispatch as root and
uid/gid 1234. A controlled peer supplies 17 bytes and FIN, or keeps an empty
stream open. A separate MSG_PEEK call establishes the complete payload before
the ioctl; ordinary reads afterward prove that the query did not consume it.
Cases include partial reads, drained EOF, repeated queries, nonblocking mode,
unaligned and inaccessible output, partial page-boundary copies, bad stacks,
invalid/closed descriptors, regular files, a FIFO, `/dev/null`, a directory,
and several unsupported command encodings. Each 160-byte record includes
return registers, primary identity, both output guards and drained payload.

Build and measure:

```sh
python3 scripts/build-irix-siocnread.py
python3 scripts/probe-irix-reference-siocnread.py
```

The reference harness copies the private original IRIX image, verifies fixture
uploads and peer receipts, and shuts the guest down. Proprietary media, raw
vendor traces and screenshots remain under ignored `.work`. No proprietary
source is used. Keep at most four IRIS guests running and stop them afterward.
Kernel builds run sequentially with at most two compiler jobs.

The reviewed [ABI contract](abi.json) and [original records](reference.json)
contain 42 variants × two ABIs × two dispatch forms × two identities = 336
records. A successful call returns zero and writes a big-endian 32-bit count:
17 queued bytes, 12 after a five-byte read, or zero on empty/unconnected streams.
After all data and FIN are consumed, it returns IRIX `ECONNRESET` (131), including
when the supplied output pointer is null. Bad descriptors return `EBADF` (9)
before pointer validation. Regular files/directories return `ENOTTY` (25);
FIFO and `/dev/null` return `EINVAL` (22). Unaligned output works. A page-crossing
copy writes the accessible prefix and then returns `EFAULT` (14).

The adapter accepts only `0x4004730a`. Other commands retain `ENOSYS` (89),
including the tested alternate `0x4004667f` encoding that IRIX accepts, unknown
commands with invalid descriptors, and TCGETA. The comparator explicitly checks
these bounded policy differences; it does not mask fields or count them as exact
IRIX matches. AF_UNIX, datagrams, listening sockets, resets, urgent data, local
shutdown, concurrent changes and large queues remain outside qualification.

Build the two kernels sequentially:

```sh
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-siocnread-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-siocnread-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-siocnread/XIRI_IRIX_SIOCNREAD" \
XIRI_NETBSD_ARCH=mips64eb scripts/build-netbsd-kernel.sh kernel
```

For o32 use `netbsd-irix-siocnread-o32-build`, `XIRI_IRIX_SIOCNREAD_O32` and
`mipseb`. The baseline JSON files pin clean source and kernel/config hashes.
Focused tests clone the stopped, qualified recvmsg X11 seed:

```sh
python3 scripts/probe-irix-siocnread.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-siocnread.py --mode ordinary \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-siocnread.py --kernel-abi o32 \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
```

Native/asa/echo controls bracket each run. Both LP64 modes repeat Toolchest
three times per identity, first with libraries alone and then with supplied
resources, recording syscall traces, window trees and framebuffer hashes.
Each client has a five-second parent timeout. An observed launch is not by
itself a claim of usable X behavior. Select and transport regressions accept
`--kernel-checkpoint siocnread`; the transport run reuses the reviewed
`lab/irix-fxstat/desktop.json` expectations on the controlled unused display.

The initial mode-0644 reference fixture could not open write modes as uid 1234.
That diagnostic run is excluded and its guest was stopped after cleanup timed
out. The final mode-0666 fixture removes this setup error and the final reference
shuts down cleanly. Supplementary groups are not normalized on IRIX; the fixture
permissions make them irrelevant to these descriptor opens.


## Sustained windows and fresh xclock checks

The [qualification](../../docs/results/2026-10-31-irix-siocnread.md) records
840 focused checks, 2,477 regressions, 24 staged Toolchest launches, and the
longer window/Expose checks. Resource-enabled Toolchest is viewable and repaints
as both identities during 60-second runs. Native controls bracket those checks.
The same-kernel xclock recheck still stops at libXmu mapping in all four
analog/digital and root/user combinations; native xclock is viewable.

```sh
python3 scripts/probe-irix-toolchest-window.py \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow
python3 scripts/probe-irix-xclock.py --kernel-checkpoint siocnread \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow
```

The longer observer installs the already-downloaded NetBSD 11.0 X development
set after checking its pinned SHA-512. It inspects map state, clears viewable
windows while holding its test server, and compares root-pixel checksums before,
during and after repaint. The native static control verifies this mechanism
before and after the vendor runs. The initial attempt without X headers is
excluded; it halted cleanly. Final screenshots remain private under `.work`;
the user-requested PNG is `screenshots/toolchest-netbsd-xorg.png` beneath this
lab's work directory.

Recheck the final records and both X follow-ups:

```sh
python3 scripts/qualify-irix-siocnread.py \
  .work/irix-siocnread/runs/lp64-ci-d2asxkow \
  .work/irix-siocnread/runs/lp64-ordinary-c8pl3x_q \
  .work/irix-siocnread/runs/o32-ci-9hyzkead \
  --select-run .work/irix-select/runs/lp64-ci-e7q40lth \
  --transport-runs .work/irix-recvmsg/runs/lp64-ci-6vc2okkn \
    .work/irix-recvmsg/runs/o32-ci-r699v4j_ \
  --window-run .work/irix-siocnread/window-runs/ci-8rh92g63 \
  --xclock-run .work/irix-xclock/runs/ci-0xaicapn \
  --output docs/results/2026-10-31-irix-siocnread.json
```
