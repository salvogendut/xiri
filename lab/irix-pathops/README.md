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

## Filesystem statistics and removal

The `statvfs.c` observer exercises `statvfs`, `fstatvfs`, `statvfs64` and
`fstatvfs64`: 384 records across both ABIs, dispatch forms and identities.
It checks structure sizes, output guards, unaligned buffers, permission and
lookup errors. The qualifier compares status with IRIX, checks native fields
for consistency and retains the actual FFS geometry; XFS capacities and IDs
are not expected to match.

```sh
python3 scripts/build-irix-pathops.py --suite statvfs
python3 scripts/prepare-irix-statvfs-fixtures.py
```

In a fresh disposable guest, extract `.work/irix-statvfs/inputs.tgz` under
`/tmp/statvfs`, make that directory and its four executables mode 755, and
create these fixtures with umask 022:

```sh
cd /tmp/statvfs
mkdir results denied
chmod 777 results
echo payload >file
echo denied >denied/file
chmod 000 denied
ln -s file link
sh run.sh root
su PROBE_ACCOUNT -c 'sh /tmp/statvfs/run.sh user'
```

Use an account with UID/GID 1234. Archive `results` as `reference.tar` or
`native.tar`, then use `qualify-irix-statvfs.py --reference reference.tar
--native native.tar --native-run HALTED_NATIVE --reference-run HALTED_IRIX
--output RESULT.json`.

The `remove.c` observer checks `unlink` and `rmdir` in 42 filesystem cases,
again across both identities/ABIs/dispatch forms: 336 records. It records
surviving metadata and link relationships as well as return values. This
includes final symlinks and trailing slashes, denied and sticky parents,
nonempty directories, malformed paths and invalid pointers.

```sh
python3 scripts/build-irix-pathops.py --suite remove
python3 scripts/prepare-irix-remove-fixtures.py
```

Extract `.work/irix-remove/inputs.tgz` into `/tmp/irix-remove` on each fresh
guest, make the directory and executables mode 755, and run
`sh run.sh PROBE_ACCOUNT` there as root. The script creates each case once
and invokes its observer as root or UID 1234. Archive `results` and compare:

```sh
python3 scripts/qualify-irix-remove.py --native NATIVE_RESULTS.tar \
  --native-run HALTED_NATIVE --reference-run HALTED_IRIX --output RESULT.json
```

The retained `remove-reference.json` comes from original IRIX 6.5.22m.
Both qualifiers reject recovered diagnostic owners for final qualification
and require an observed clean halt. `--diagnostic` can inspect a live run
without making a qualification claim. See the
[File Manager guide](../../docs/IRIX-FILEMANAGER.md) for the GUI workflow.
