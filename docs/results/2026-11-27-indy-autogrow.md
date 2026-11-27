# IRIX shared-file growth on the Indy

SGI CD Player and Sound Editor both use a shared file to back an allocator
arena. The earlier Xiri kernel rejected their 64 KiB, read/write mapping with
`EINVAL`. The new Indy kernel and matching `compat_irix_o32` module accept
`MAP_SHARED | MAP_AUTOGROW` on a regular file opened read/write.

## What extends the file

Creating the mapping leaves the original size in place. When a user load or
store faults on a page wholly beyond EOF, the file grows through the end of
that page. The untouched gap reads as zeroes. The test reads the backing file
independently after the child has exited and checks every byte.

| Operation on a 17-byte file | Original IRIX 6.5.22f and 6.5.30f | Xiri Indy |
| --- | --- | --- |
| Create a shared autogrow mapping | 17 bytes | 17 bytes |
| Read offset 8,192 | 12,288 bytes, byte reads as zero | 16,384 bytes, byte reads as zero |
| Store at offset 8,192 | 12,288 bytes, stored byte persists | 16,384 bytes, stored byte persists |
| Read or store there through an ordinary shared map | Child receives SIGBUS, file stays at 17 bytes | Child receives SIGBUS, file stays at 17 bytes |

Original IRIX uses 4 KiB pages on both reference machines. The tested NetBSD
Indy kernels use 8 KiB pages. Private file-backed AUTOGROW has separate IRIX
semantics and remains unsupported. The implementation handles a direct user
load or store. A kernel copy into an untouched page past EOF does not extend
the file. A new module requires its matching kernel and boot kernel.

The 24 fixtures per operating system cover both IRIX ABIs (o32 and n32),
an initially empty file, an existing in-file mapping, inherited and aliased
pages, and protection failures. A separate unprivileged native NetBSD control
checks fork sharing, private mappings, descriptor close, two mappings of the
same file, and SIGBUS past EOF. The NetBSD implementation is on `xiri` at
`2223c5f0b4b`. The four runs used IRIS `65039d90`.
[Per-release measurements](2026-11-27-indy-autogrow.json)

## Desktop applications

Both release-matched copies of SGI Sound Editor now open their 700×500
`SoundEditor: Untitled` editing window under the ordinary `xiritest` login.
[6.5.22f screenshot](2026-11-27-soundeditor-xiri-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-27-soundeditor-xiri-6.5.30f.png)

On the shared-file-growth build, pressing Record displayed “Cannot create record thread.”
The 6.5.30f playback attempt produced zero frames at the emulated DAC.
The subsequent Sound Editor check traced this to the recording child's
`sproc(PR_SALL)` call. [Recording, saving and playback](2026-11-27-indy-soundeditor.md)
[Record dialog](2026-11-27-soundeditor-record-error.png) ·
[Original IRIX recording and Xiri command-line tests](2026-11-27-indy-microphone.md)

SGI CD Player now reaches its drive check on both releases. With the two-track disc at SCSI
ID 6, native `cdplay` could read the audio TOC. The SGI command
`cdman -dev /dev/scsi/sc0d6l0` displayed “Could not find specified CDROM
drive.” Its next requirement is access to the drive through the IRIX device
interface. The desktop music icon continues to use the qualified native player.
[SGI CD Player dialog](2026-11-27-cdman-drive-error.png) ·
[Native desktop playback](2026-11-27-indy-cd-audio.md)

## Reproduction

The matched, tested local build is under
`.work/builds/indy-autogrow-20261127/{kernel,module}`. The existing installer
and manual-test CHDs were preserved.

Build the static IRIX fixtures with `python3 scripts/build-irix-mmap-shared.py`.
Build the kernel and module following the [Indy build steps](2026-11-27-indy-microphone.md#reproduce-on-the-lab-indys).
Use a private copy of each [prepared desktop](2026-11-27-indy-cdrom.md#ready-to-boot-prismatic-systems)
and the [two-track audio fixture](2026-11-27-indy-cd-audio.md#reproduce-the-desktop-check).

```sh
check=lab/irix-mmap-shared/check-autogrow.py
python3 "$check" test --bundle "$BUNDLE" --cpu "$CPU" --emulator "$IRIS_BIN_DIR" \
  --fixtures .work/irix-mmap-shared/probes --disc "$AUDIO_CD" \
  --kernel "$BUILD_DIR/kernel/netbsd" --boot-kernel "$BUILD_DIR/kernel/netbsd.elf32" \
  --module "$BUILD_DIR/module/compat_irix_o32.kmod" --output "$RESULT_DIR"
```

For an original donor, create the probe tar with the same fixtures. Supply
it to `scripts/probe-irix-donor.py` with `--mmap-fixtures` and the normal
donor arguments. Use `--start-system-after 8` for a PROM that stops at the
maintenance menu. The checker uses a scratch disk on SCSI ID 2 to transfer
the result. The original 6.5.22f reference was an Indy R4400 and the 6.5.30f
reference was an O2 R5000.

```sh
python3 "$check" pack-reference .work/irix-mmap-shared/probes fixtures.tar
python3 "$check" read-reference "$DONOR_RESULT_DIR/records.tar"
```
