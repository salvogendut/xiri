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

With both fixture packages prepared, collect fresh native observations from
a disposable copy of a packaged image with:

```sh
python3 scripts/probe-irix-filemanager-abi.py --bundle IMAGE_BUNDLE
```

This checks that the uploaded executables match the IRIX reference, records
the loaded module, runs both suites and the native control, then halts. Use
its printed run directory as `HALTED_NATIVE` for the qualifiers above.

## Symlinks and nanosecond timestamps

`filemeta.c` observes `symlink` (1115) and `utimets` (1235), including the
indirect syscall form used by File Manager. Both supported ABIs pass two
32-bit seconds/nanoseconds pairs. The 41 cases run under both identities and
both dispatch forms: 328 records. They retain return registers, pathname
errors, ownership, modes, symlink target bytes and before/after timestamps.
Null timestamp pointers are checked against the surrounding guest clock.

```sh
python3 scripts/build-irix-pathops.py --suite filemeta
python3 scripts/prepare-irix-filemeta-fixtures.py
python3 scripts/probe-irix-filemanager-abi.py --bundle IMAGE_BUNDLE --suite filemeta
python3 scripts/qualify-irix-filemeta.py --native HALTED_NATIVE/filemeta.tar \
  --native-run HALTED_NATIVE --output RESULT.json
```

To repeat the reference measurement, extract `.work/irix-filemeta/inputs.tgz`
into a fresh `/tmp/irix-filemeta` on original IRIX 6.5.22m, make the directory
and four executables mode 755, and run `sh run.sh PROBE_ACCOUNT` as root. The
account must have UID/GID 1234. Archive `results` and retain the build manifest,
input hash, guest identity and clean shutdown. Fixture directories are
single-use. Version-3 stat timestamps start at word 17, after the padding
word; the retained reference uses that corrected observer.

The qualifier requires exact reference records except for 24 explicitly
listed timestamp cases. Noncanonical nanoseconds and seconds equal to -1
must return EINVAL with unchanged metadata. IRIX accepts these values, but
NetBSD uses negative nanosecond sentinels and reserves -1 seconds as VNOVAL
in vnode attributes. This bounded difference avoids accidental native
sentinel interpretation or a successful no-op. It is not full timestamp
parity. A native control separately checks file contents and epoch seconds.

The GUI companion is `scripts/probe-xiri-filemanager.py --bundle IMAGE_BUNDLE`.
It uses original menus and mouse drags under two xdm users, asserts different
filesystem device IDs, and checks exact contents, modes, owners and mtime.
Native create/rename/delete screenshots precede the Sort by Name action used
to stabilize drag coordinates. A renamed icon can occupy a new slot; a drag
at its old position is a fixture error, not a failed file operation.

`filemeta-build.json` preserves the actual build inputs. The later
`filemeta-source-equivalence.json` binds them to the committed module source
and identifies the unchanged native-wait core by matching artifact hashes.
Use `qualify-xiri-image.py --source-equivalence
lab/irix-pathops/filemeta-source-equivalence.json` when qualifying this image.
The older `source-equivalence.json` remains available for earlier bundles.
