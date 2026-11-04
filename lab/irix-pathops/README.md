# IRIX pathname operations

The independent `rename.c` observer records the return values and filesystem
changes for the same executable bytes on original IRIX 6.5.22m and NetBSD.
The 32 cases cover files, directories, symbolic links, hard links, replacement,
permissions, trailing slashes, invalid pointers and malformed paths. Each runs
under root and UID/GID 1234, for o32/n32 and direct/indirect traps: 256 records.

Build and package the fixtures:

```sh
python3 scripts/build-irix-pathops.py --suite rename
python3 scripts/prepare-irix-rename.py
```

Extract `.work/irix-rename/probes.tar` into `/tmp/xiri-pathops` on a disposable
guest. Make its `cases` directory writable by both test identities. Run
`setup.sh 0` as root, change the `cases` directory group to 1234, then run
`setup.sh 1234` as the test account. NetBSD inherits a new directory's group
from its parent; these fixtures require GID 1234 for the unprivileged cases. The native runner
requires each case's empty `input.txt`; the setup script creates it.

On IRIX, run `reference-run.sh` separately as each account. On NetBSD, compile
`runner.c` with the native compiler and run `native-run.sh 0` and
`native-run.sh 1234` as root; the runner drops credentials in its child. Setup
must be fresh for every run because successful cases change the filesystem.
Capture the four binaries and all `.log`/`.err` files in a tar archive, retain
the owning guest's result and cleanly halt it. Then compare against the
retained reference:

```sh
python3 scripts/qualify-irix-rename.py --native NATIVE_RESULTS.tgz \
  --native-run HALTED_RUN --output RESULT.json
```

`--diagnostic` allows inspection before shutdown and cannot produce a qualified
result. The reference records retain syscall status, modes, owners, links,
contents and inode-identity relationships without comparing unrelated disk
inode numbers or timestamps. This fixture does not claim power-loss atomicity,
cross-filesystem moves or concurrent directory modification coverage.
