# Native NetBSD File Alteration Monitor

Icon Catalog and FileManager use SGI's FAM protocol. The development image
previously had no FAM service, and its original RPC client also lacked a working
`poll` syscall. This experiment builds the public FAM 2.7.0 source for native
NetBSD o32, with pinned NetBSD pkgsrc patches and local iterator, time-format and
optional imported-path corrections.

`source.json` pins the archive, pkgsrc revision, every patch/support file and
local patch hashes. Vendor IRIX binaries are unchanged. The public archive
contains the relevant GPL/LGPL license texts. Generated binaries and sysroots
remain under `.work/native-fam/`.

```sh
python3 scripts/build-native-fam.py
```

The builder verifies the NetBSD 11.0 base/comp sets, uses their headers and
libraries with the existing cross compiler, and records artifact hashes.
It runs an optimized host regression for the tree iterator and produces the
same regression as a native guest executable, `btree-native`. It also runs
15 namespace assertions on the host and builds `emul-path-native` for the
guest. The desktop probe executes both native regressions.

The unpatched daemon crashed in `BTree<Interest*, bool>::Node::find`, reached
from `Node::next` during the first polling pass. The old code calls `next`
through a null child and checks `this` inside the method. Modern optimization
removes that check. The local patch checks the child before calling it. A
regression iterates more than one tree node and removes each current key during
iteration. The unpatched optimized host test exits with SIGSEGV; the corrected
one passes. The patch also prints 64-bit `time_t` with the correct format.

The client recognizes legacy RPC version 1 and uses TCP directly. Version 2
negotiates a Unix-domain socket, which is outside Xiri's current socket subset.
The bounded development configuration uses `famd -p 391002.1`, local-only
connections, an explicit native xiritest account at UID/GID 1234, and
`untrusted_user = xiritest`. It does not enable `insecure_compatibility`.
This is a single-user development service, not multi-user authentication.

NetBSD rpcbind adds loopback to its bind list automatically. The original
explicit `-h 127.0.0.1` restriction caused duplicate bind warnings. The
[qualified native rpcbind fix](../native-rpcbind/README.md) removes those
duplicates while retaining loopback-only registration and traffic.
FAM readiness checks its portmapper registration, not an RPC NULL call: the
socket advertised there speaks FAM's own protocol.

Live service, namespace and file-change observations are recorded in the
[desktop repair result](../../docs/results/2026-11-02-desktop-services.md).
`xiri-desktop` owns FAM and any rpcbind it starts; cleanup also covers the
daemon when its effective identity is temporarily UID 1234. The imported
desktop tree needs a native `/usr/lib/desktop` alias before clients subscribe.

The session now sets `XIRI_FAM_ROOT=/emul/irix`. Without this mapping, FAM
reports `/usr/freeware/bin/xmahjongg` as deleted even though the foreign
client sees its imported executable; Icon Catalog changes its correctly
classified type to `DanglingReference`. The optional mapper selects imported
files, resolves intermediate absolute/relative links within the import root,
keeps final file links observable, and falls back to native home files.
Request credentials apply before lookup. Physical watch names and logical
event names are distinct, so original clients receive their requested names.
Relative directory-entry events remain unchanged. Native internal interests
are unaffected.

Selection happens when a watch is created; adding a new shadowing import
while a native watch is already active does not rebind that watch. Tests cover
disabled mapping, already-prefixed paths, missing entries, links, native
fallback and import/native collisions. Live checks observe original client
`Exists`/`EndExist` events, native-home Created/Deleted events and rendered
Freeware artwork without a `/usr/freeware` alias or injected observer library.
See the [icon result](../../docs/results/2026-11-02-desktop-icons.md). The prior
qualified FAM build is retained at `.work/native-fam-pre-icons-20261102`.
