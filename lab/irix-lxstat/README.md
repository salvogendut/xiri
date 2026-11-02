# Desktop filesystem and RPC interfaces

This checkpoint investigates the shared Icon Catalog/FileManager failures on
NetBSD/X.org. `lxstat` and `readlink` must inspect final symlinks; directory
enumeration must expose the installed catalog pages; `poll` lets the original
RPC client receive its port-mapper reply. `_SC_MAC` must return zero so 4Dwm
does not create a Trusted Path panel for a facility the host does not provide.

The original IRIX 6.5.22m reference runs use the user's installed image, with
independently written static fixtures. No proprietary source is required.
Each fixture runs through direct and indirect traps, o32 and n32, as root and
UID/GID 1234. Reference manifests bind the source and executable hashes to raw
observations and a cleanly halted reference run.

| Family | Original observations | Important boundary |
| --- | ---: | --- |
| lxstat | 672 | Final symlink, dangling link, trailing slash, stat versions, permissions and copyout faults |
| readlink / feature queries | 240 | Truncation without NUL, signed negative capacity, pointer faults, MAC/CAP/page queries |
| poll | 240 | Readiness, invalid descriptors, array bounds, timeouts and native pipe differences |
| directory enumeration | 800 | Four syscall numbers, both record layouts, short buffers, EOF pointer and cursor preservation |

The combined NetBSD harness also runs the existing xstat regression. It boots
a disposable copy of the qualified prepared disk, tests native/vendor controls
before and after, and halts the guest. Native metadata observers supply actual
filesystem inode numbers and directory order; IRIX/XFS inode numbers and
cookies are not transplanted into NetBSD.

```sh
python3 scripts/build-irix-lxstat.py
python3 scripts/build-irix-desktop-queries.py
python3 scripts/build-irix-poll.py
python3 scripts/build-irix-dirent.py
python3 scripts/probe-irix-desktop-fs.py --mode ci
python3 scripts/probe-irix-desktop-fs.py --mode ordinary
python3 scripts/probe-irix-desktop-fs.py --kernel-abi o32
```

The build scripts use the existing cross compiler in the `xiri-iris` Toolbox.
Kernel configurations and exact output hashes are in `baseline.json` and
`o32-baseline.json`. Build them with `scripts/build-netbsd-kernel.sh`, using
the desktop build directories named by the harness. The qualified signal
kernel and reusable CHD remain separate artifacts.

Known limits are deliberate and recorded by the checkers: native pipe poll
readiness differs for POLLOUT on the read end and unrequested POLLRDNORM at
hangup; directory padding is unspecified; invalid directory buffers are
rejected before the occasional partial-byte write seen on IRIX. Native
filesystem ordering/cookies and page size differ. General Unix-domain sockets,
union-mount directory traversal and full IRIX compatibility are not established.

An initial kernel omitted the explicit link-dispatch allowlist entries. Its
matrix runs were cancelled and do not qualify those adapters. The next matrix
found FFS fast-symlink reads discarding user-copy errors; the adapter now owns
the final copyout. One LP64 harness run also exposed missing explicit directory
permissions for UID 1234; subsequent runs set the umask and staging modes.
