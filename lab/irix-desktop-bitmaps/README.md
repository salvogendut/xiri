# SGI desktop toolbar resources

Fresh FileManager traces request seven missing bitmap names under
`/usr/include/X11/bitmaps/sgidesktop`: `iconFinderPrevious`, `iconicDirView.bm`,
`listDirView.bm`, `columnDirView.bm`, `galleryDirView.bm`, `shelf.bm` and
`contentView.bm`. Import the original resource directory once, preserving
the older installed-desktop payload:

```sh
python3 scripts/import-irix-desktop-bitmaps.py
```

The script opens the supplied IRIX reference disk read-only, mounts XFS with
`ro,norecovery`, and writes an ignored `.work/irix-desktop-bitmaps/payload.tgz`.
No original absolute symlink is created on the host. The public
[copy ledger](copy-ledger.json) records 48 regular files, six original
absolute aliases and one directory, with hashes and destination modes.
All destinations lie beneath `/emul/irix`. Files are read-only resources;
directories are searchable. The desktop image upgrade verifies the archive
hash and installed files.

These toolbar resources are distinct from filetype artwork. The existing
`/usr/lib/filetype` import already contains compiled tables and iconlib data;
the latest fm trace fails `F_SETBSDLKW` on the opened `desktop.otr` before
reading it. Importing additional bitmaps does not fix that syscall.
