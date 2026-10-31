# Toolchest's next boundary: SIOCNREAD

After the fxstat change, the supplied-resource Toolchest attempt examined here
exits 1 with XIO error 89 instead of the earlier allocator SIGSEGV. Its next
specific compatibility candidate is `ioctl(fd, 0x4004730a, int *)`, named
`IRIX_SIOCNREAD` in the licensed historical NetBSD implementation. It queries
the number of readable bytes and corresponds to native `FIONREAD`.

This is a read-only trace and original-binary investigation. It adds no kernel
behavior and launches no guest. The observed sequence and compiled error path
strongly support SIOCNREAD as the immediate XIO trigger; the trace alone does
not prove which userspace branch executed.

## Recorded evidence

- Private trace: `.work/irix-fxstat/runs/lp64-ci-ghuwxa6n/resources-0-0.kdump`.
- Trace SHA-256:
  `1a5cbef0df35caff90c2640b1726f5251ebb77360b17b107005cdccc05aacee2`.
- Original n32 `libX11.so.1` SHA-256:
  `2e3287c4842eb4149c9f839229093a28c180edf43dcf1f28b68102cdcf989642`.
- Kernel source: `ef34f8afe16d5cf80a743b208dccc3a4f355efe2`,
  `xiri/irix-fxstat`.

This capture comes from the initial diagnostic run, which is excluded from
final fxstat qualification because of the separate directory-permission and
asa-input fixture issues documented in the [fxstat report](2026-10-31-irix-fxstat.md).
Those issues do not invalidate the recorded Toolchest syscall sequence.

The decoded trace contains 1,041 foreign calls and 1,040 returns; final exit
has no return. Call/return order was checked, accounting for indirect syscall
1000. Descriptor 3 is created by the successful IPv4 stream socket call,
connects successfully, and is never closed before the final ioctl. It serves
169 intervening reads.

| Call index, zero based | Observation |
| --- | --- |
| 1019 | `write(3, ..., 84)` returns 84 |
| 1020 | syscall 1054 at `0x0fa50e44`, fd 3, request `0x4004730a`, output pointer `0x7fff7070`; returns v0 `0x59`, a3 1 |
| 1021–1024 | Error-reporting interval: syssgi request 92 returns ENOSYS, then three locale-message pathname probes return ENOENT |
| 1025 onward | Writes the XIO diagnostic to stderr, followed by exit 1 |

There are no further read/write/close operations on fd 3 after SIOCNREAD.
The report says 264 requests issued and 260 processed. That is application
diagnostic output, not an independently decoded X protocol count.

The same trace contains 51 earlier ioctl requests `0x5401`, the historical
SVR4 `TCGETA` selector. They also return ENOSYS, but execution continues with
successful file reads and X communication. They are distinct from the single
SIOCNREAD failure. Missing color names and XKeysymDB warnings likewise do not
by themselves establish the immediate exit cause.

## Licensed definition and compiled corroboration

The already audited NetBSD revision
`5aca2679d78276864d2980a08314887b2058fb2c` defines:

- `sys/compat/irix/irix_ioctl.h`: `IRIX_SIOCNREAD` is
  `SVR4_IOR('s', 10, int)`.
- `sys/compat/svr4/svr4_ioctl.h`: output direction `0x40000000`, four-byte
  length in bits 16–23, group `'s'` and request 10 produce `0x4004730a`.
- `sys/compat/irix/irix_ioctl.c`: translates that selector to `FIONREAD`.
- `sys/compat/svr4/svr4_termios.h`: `SVR4_TCGETA` is `('T' << 8) | 1`.

The original libX11's symbol/GOT metadata and compiled control flow corroborate
the intended use without publishing instruction bytes:

1. TCP, INET and UNIX transport tables all point their bytes-readable slot
   at `_X11TransSocketBytesReadable..MJ`, address `0x0f6f45a0`.
2. That routine extracts the connection's fd, passes the caller's integer
   output pointer to `ioctl` with `0x4004730a`, and returns its result unchanged.
3. `_XEventsQueued` calls that transport slot at `0x0f605b78`. A negative
   return branches at `0x0f605b80` to its I/O-error path. With no custom error
   handler, it calls `_XDefaultIOError` and then exits 1.
4. `_XDefaultIOError` obtains errno through `__oserror`, formats the diagnostic
   using `strerror`/`fprintf`, and exits 1.

A narrow breakpoint capture of the actual transport caller/error branch, or
a rerun after a separately qualified SIOCNREAD adapter, would establish
whether this is the path taken in the observed process. Other ioctl callers
and later application behavior remain unqualified.

## Paired probe scope

Use original libc-free fixtures on IRIX and NetBSD, covering o32/n32,
direct/indirect syscall dispatch and root/ordinary credentials. Reuse the
qualified TCP test transport to control queued data. Measure:

- Empty and populated connected stream sockets, partial reads and repeat
  queries: exact four-byte count, non-destructive behavior, return registers,
  guard bytes and preserved saved-register sentinels.
- Queued data followed by peer FIN, drained EOF, nonblocking sockets, and
  unconnected/listening sockets to establish the supported state boundary.
- Invalid/closed descriptors, valid non-socket descriptors, unknown ioctl
  selectors, and combined bad-descriptor/bad-pointer cases for validation order.
- Aligned and unaligned output, null/high/read-only pointers, and a four-byte
  result straddling an inaccessible page to measure copy extent and EFAULT.

The candidate implementation should translate this exact request to native
FIONREAD while retaining native descriptor ownership and a kernel integer
buffer with normal copyout. The historical branch passes its data argument
directly to file operations; it should not be transplanted as the modern
buffer-handling implementation. Do not infer a general ioctl passthrough
contract from this one selector. After qualification, rerun Toolchest with
native X controls and record the next observable boundary before claiming a
usable window or event loop.
