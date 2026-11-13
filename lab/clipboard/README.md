# Native/IRIX text selection checks

This lab exercises real native xterm, original IRIX winterm and original
IRIX gedit on the same accelerated NetBSD/Xorg display. See the
[user guide](../../docs/IRIX-CLIPBOARD.md) and
[qualification record](../../docs/results/2026-11-13-clipboard.md).

`selection.c` is a native Xlib observer/control. It reports selection owners,
cut-buffer sizes and advertised targets, receives text with a bounded INCR
implementation, and can offer a file from a native selection owner. It is a
lab fixture, not a clipboard manager: the owner supports one incremental
requestor at a time, lives at most ten minutes and accepts at most 16 MiB.
The ordinary requestor deadline is 45 seconds. Refused targets return 5;
no owner returns 4; timeout returns 124.

`input.c` sends actual XTest drag, click and key gestures to a named window
or window ID. IDs allow gedit's modified-file title to change during tests.
The existing `type-ready.c` fixture types shell commands into real terminals.
The test payload is pasted into `cat`, not evaluated as shell commands.

The maintained runner clones the selected CHD, uses its pinned emulator,
boots graphically, compiles the native helpers and logs in through xdm:

```sh
python3 scripts/probe-xiri-clipboard.py \
  --bundle .work/images/xiri-netbsd-desktop-20261113-filemanager
```

Use the repository's provisioned `xiri-iris` Toolbox environment. When already
inside the provisioned Distrobox with the direct Toolbox adapter, add
`--local-processes`; this explicitly opts into terminating the recorded local
process groups. The selected CHD is read-only to the test: writes go to a
private clone/overlay. The runner verifies the original hash after clean halt.

The public image accounts are `xiritest`, `xiritest2` and `netbsdtest`, each
with the same name as its lab password. The third account uses native ctwm.
The runner does not enroll users or alter real home directories.

Checks include:

- PRIMARY mouse selection and middle paste in both terminal directions.
- Real gedit Copy/Paste and native xterm's documented CLIPBOARD mode.
- Independent PRIMARY and CLIPBOARD contents, owner replacement and source exit.
- Exact multiline/tab, Latin-1 and 113,664-byte transfers. Large transfers
  use INCR in both directions; the native producer deliberately uses 1 KiB chunks.
- Advertised targets and gedit's explicit refusal of `UTF8_STRING`.
- Empty selections/cut buffers after logout and across two IRIX users and
  a native ctwm user, followed by fresh selections under each identity.
- PNG evidence, clean halt and unchanged base CHD.

Each successful stage writes `checkpoint.json`. Final `result.json` is
qualified only after all checks, clean halt and the base hash pass. Retain
logs, source/fixture hashes, results and PNGs before removing completed private
disks, media and build output. Run an owning process that survives the tool
supervisor's timeout, monitor its checkpoints, and verify that its emulator
has stopped before cleanup.
