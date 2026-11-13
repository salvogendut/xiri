# File Manager and Dumpster

Xiri uses the original IRIX 6.5.22 File Manager (`fm`), desktop icons and
Toolchest menus. Files live in the authenticated NetBSD user's home. The
Dumpster is `$HOME/dumpster`, with a `.dumpster` marker; the desktop icon is
`$HOME/Desktop/dumpster -> ../dumpster`.

## Host configuration

The machine's own hostname must resolve to an IPv4 address from IRIX libc.
File Manager builds a local-host cache using `gethostname()` and
`gethostbyname()`. A failed lookup can make Rename and Make Copy report
that an existing local file does not exist.

For the standalone test image, `/etc/hosts` contains:

```text
127.0.0.1 xiri-indy
```

For another NetBSD host, use its actual hostname and an appropriate local
IPv4 address. Check `hostname` and `getent hosts "$(hostname)"`. An imported
`/emul/irix/etc/hosts` can shadow the native file, so keep it consistent if
one exists. Xiri's general runtime installer does not replace the
administrator's network configuration. Log out and back in after correcting
it, since the vendor client caches its local host during startup.

## Original actions

- **Actions → Add New Directory** (`Ctrl+N`) creates `empty.dir`.
- Select an icon, then click its label to edit its name. Type the new name
  and press Return.
- **Selected → Make Copy** (`Ctrl+C`) creates `copy_of_<name>` in the same
  directory.
- Drag an icon with the middle mouse button between File Manager windows
  to move it on the same filesystem.
- Drag onto the desktop Dumpster icon to discard a file. Double-click
  Dumpster to see its contents, then drag the file out to recover it.
- **Toolchest → Desktop → Empty Dumpster** invokes the original
  `/usr/lib/desktop/telldesktop 'empty dumpster'` helper. Emptying is permanent.

The resource import adds only that original helper at
`/emul/irix/usr/lib/desktop/telldesktop`. The existing native
`/usr/lib/desktop` link also makes it reachable by native shell commands.
Toolchest checks helper availability when it starts; restart the session
following an import.

The [resource ledger](../lab/irix-filemanager/resources.json) records its
source, hash, dependencies, destination and mode. To prepare it from the
read-only reference disk, run `python3 scripts/stage-irix-filemanager.py`.
Pass `--filemanager-resources .work/irix-filemanager-resources` to
`prepare-xiri-xdm-image.py`. No original user's files or Dumpster contents
are imported.

## Manual check

Log in through xdm as a normal IRIX desktop user. In winterm, create a new
test directory and a small file, then open that directory with `fm`. Use the
original actions above to create a folder, rename the file, make a copy,
move the copy to another directory, discard it and recover it. Discard the
copy again and use Empty Dumpster. Repeat with a folder containing a test
file to exercise recursive deletion. Keep the original file outside Dumpster.

Log out, repeat under another user, then reboot normally with
`shutdown -r now`. Check both users' surviving files, contents and ownership.
Each user's Dumpster should retain its hidden `.dumpster` marker and no
discarded test content. Do not empty a Dumpster containing files you intend
to keep.

The [November 13 result](results/2026-11-13-file-manager.md) records the
measured ABI, two-user GUI observations, their limits, screenshots and the
qualified manual CHD.

## Compatibility boundary

Filesystem statistics, deletion, directory removal and rename use native
NetBSD filesystem ownership and permissions. They do not make one user's
home or Dumpster accessible to another user. IRIX's trailing-slash handling
is retained without following a final symlink during removal.

The bounded checks cover local files and directories. Cross-filesystem moves,
remote filesystems, collisions, immutable flags, and concurrent pathname
changes need separate qualification.

Original behavior references:
[IRIX file management guide](https://irix7.com/techpubs/007-1342-180.pdf) and
[`telldesktop`](https://techpubs.jurassic.nl/manpages_0530/cat1/telldesktop.html).
