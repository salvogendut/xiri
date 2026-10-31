# Original IRIX xclock on NetBSD

Follow-up: see the [next checkpoint](2026-10-31-irix-elfmap-relocation.md). This report preserves the earlier observed boundary.

The original n32 xclock is a smaller test than Toolchest, but currently stops
earlier: rld cannot map `/usr/lib32/libXmu.so`. SGI_ELFMAP returns ENOMEM and the
program exits 1 before any socket/connect call. Native NetBSD xclock displays
correctly on the same X.org server. This does not qualify an IRIX clock window
or event loop.

The [inventory](../../lab/irix-xclock/manifest.json) pins the unmodified binary,
its bounded library closure and original application defaults. xclock and its
libraries have suitable 8 KiB load boundaries. Static ELF ranges show overlaps
between libXaw, libXmu and libXt; libX11/libXext also have overlapping linked
ranges. The loader's actual ENOMEM plus those overlaps make mapping/relocation
the next investigation for this client. This is not evidence that the host ran
out of RAM, nor a proof of every requested runtime mapping address.

The [lab](../../lab/irix-xclock/README.md) records commands and controls. Analog
and digital modes are tried under root and uid 1234 with an explicit HOME.
Window-tree/map-state samples and two framebuffer captures accompany each
bounded launch. The loader error goes to `/dev/console`, so empty captured
stderr must not be mistaken for a silent successful launch.

This experiment separates two current routes: Toolchest reaches resource input
and an allocator fault associated with unsupported fxstat; xclock supplies a
smaller reproducer for the library-mapping boundary. Neither result establishes
a working original desktop.

## Completed runs

The [machine-readable report](2026-10-31-irix-xclock.json) records eight vendor
attempts: analog/digital × root/uid 1234 × CI/ordinary. All exit 1 at the same
libXmu loader boundary; none issues an X socket/connect call. Window trees have
zero children and paired frame hashes are identical. The native clock is
viewable in both runs, and native/asa/echo controls pass before and after.
Both guests halt cleanly.

The same runs complete four root Toolchest fault captures, all at
`0x0fa56b6c` with bad address `0x740a0a5c`, after native exec/fault controls.
Their raw instruction/stack captures remain private. This reproduces the
[xstat resource diagnosis](2026-10-31-irix-xstat.md) independently of the earlier
partial non-root-tracer attempt.

The ordinary harness additionally saves each case's console slice; the CI run
retains the same loader diagnostic in its complete serial log. The qualifier
re-decodes both modes' traces, verifies frame and raw-capture hashes, checks the
native window and all expected boundaries, and pins each run's actual harness
sources. No kernel or emulator change was made for xclock.

## Loader follow-up

The [live ELF-map capture](2026-10-31-irix-xclock-elfmap.md) now confirms that
rld submits libXmu’s linked headers unchanged and both requested load starts
already contain libXaw text. The fixed-address mapper returns ENOMEM. Native
breakpoint controls pass before and after analog/digital captures; the guest
halts cleanly. This establishes the collision cause and a bounded relocation
work item, without claiming a working clock or a new mapper.
