# Native Xorg input scheduling

The reproduced Acrobat focus timeout is a native Xorg scheduling stall.
At the ten-second alarm, the fake button release is ready in the server,
while Acrobat has a higher scheduling priority and is issuing pointer queries.
The runtime now selects Xorg 1.10.6's existing `-dumbSched` option in both
xdm and `xiri-desktop`, enabling round-robin dispatch. Newport XAA remains
enabled. Both cold-image acceptance runs pass and halt cleanly. The new CHD
is selected by `./xiri run`; the previous manual image and its state remain
unchanged.

## Evidence at the alarm

The [diagnostic record](2026-11-04-xorg-scheduling-diagnostics.json) retains
the exact configurations, source/result hashes and excluded setup failures.
Both the [initial raw snapshot](2026-11-04-xorg-scheduling-initial.log) and
the [expanded raw snapshot](2026-11-04-xorg-scheduling-expanded.log) are
preserved without rewriting their observations.

The diagnostic guest is `.work/system-stability/boot-xt37m0co`, booted from
the unpromoted native-CD9660 candidate with its unchanged kernel, IRIX module
and pinned IRIS backend. The reduced workload retains the original
GL → software capture, followed immediately by the native click at `300 300`.
The PDF window is placed consistently before the loop. The helper retains
the original X calls: motion synchronization, 200 ms pause, button press,
100 ms delayed release and `XSync`, with a ten-second alarm.

Two instrumented reproductions time out at `button-sync`: repetition 8 with
the initial reader and repetition 30 with the expanded state reader. The
expanded diagnostic is retained as
[`click-state.c`](../../lab/system-stability/click-state.c). Its alarm handler
stops Xorg, reads the already-open procfs descriptors, resumes Xorg and exits
124. It neither grants grab immunity nor extends the input deadline.

Both observations show no active server grab and no pending XTest sleep
node. In the expanded snapshot, the click client is index 13, server fd 19,
with `ignoreCount=0`. Its bit is set in `ClientsWithInput` and `AllClients`.
The buffered request is XTest FakeInput ButtonRelease with its delay already
cleared, followed by the GetInputFocus request used by `XSync`. The sleep has
ended; the ready request has not been dispatched. Its smart priority is zero.
Acrobat is client 12, server fd 18, with priority 20 and a current QueryPointer
request. `SmartLastClient` points to Acrobat. These private layouts are
checked against the exact server's symbol table and disassembly.

The client signal context locates the helper in native libc's `poll`
system-call wrapper, with an infinite poll timeout. Xlib has issued request
15 and last read reply 12; its outgoing buffer is empty. The attempted
`/proc/PID/regs` read for Xorg returns -1, so there is no server register
capture or backtrace. The earlier failed GDB attempt is not used as evidence.

Server SHA-256:
`48a4a07110209f604e75bd03f82494be838a80d51d12492769b323f3a1595ee4`.
The PIE load base is `0x10000`. The expanded diagnostic's source SHA-256 is
`98e4ae60accb8826d0d4dc81f2d137efd9d6688f0c5d6d44f4bb35fdaca0fa46`.

## Source and native control

In the public [Xorg 1.10.6 source release](https://www.x.org/releases/individual/xserver/xorg-server-1.10.6.tar.bz2),
`TryClientEvents` raises a client's smart priority for input events, up to 20.
`SmartScheduleClient` chooses the highest-priority ready client. Dispatch
penalizes a client only when its service consumes a scheduling tick; the
timer is stopped and restarted around waits. Repeated short QueryPointer
round trips can therefore retain the input boost while another ready client
waits. The captured request and priority state identifies that starvation
path. The supported `-dumbSched` option bypasses priority selection and uses
the existing round-robin dispatch path.

The independent [`xtest-fairness.c`](../../lab/system-stability/xtest-fairness.c)
control uses only native NetBSD Xlib clients under ctwm. A receiver processes
normal synthetic input events, then queries the pointer while an independent
unchanged click helper sends the delayed release. No IRIX application or
compatibility-module request is involved.

Across the two live diagnostic comparisons, all 16 default-scheduler cases
complete within the ten-second deadline, but total receiver times range from
0.397 to 6.360 seconds. All 16 round-robin cases complete in 0.393–0.543 seconds.
After a real Xorg restart with `-dumbSched`, 20 more native cases complete in
0.402–0.420 seconds. These totals include process startup, opening the X
connection and the helper's 200 ms pause, in addition to the 100 ms release.
The live comparisons do **not** reproduce a native-only ten-second timeout;
their result records explicitly retain that limitation. Fresh startup is
tested separately from the diagnostic live flag changes.

With that freshly started server, a reduced Reader replay completes all
60 GL → software capture → focus cycles: 30 with the byte-identical original
click helper and 30 with the unchanged traced helper. Each retains the
ten-second deadline and 100 ms release. The [last capture](images/2026-11-04-xorg-scheduling-acrobat.png)
shows the original PDF on the accelerated 1280×1024 desktop.

The reduced script's final `kill -0` predicate fails after Ctrl-Q because
Reader is a zombie child of the interactive winterm shell. Its window is
already gone. The separate exit control records that state, types `wait` in
the owning shell, observes status zero and verifies the PID is reaped and
the desktop remains ready. The original script result remains an error;
the click results and normal-exit follow-up are recorded separately. This
diagnostic continuation is not a cold-image acceptance run.

## Runtime and image handling

The general runtime installer still preserves administrator configuration.
Adopt the updated `/etc/xiri/xdm/Xservers.example` command on an existing
installation and restart xdm only after logging out. For disposable image
preparation, `--refresh-xservers` explicitly adopts the maintained command
after checking the old image's complete support inventory, and records the
before/after hashes. The IRIX module, native Xorg binary, emulator and imported
application resources are unchanged in this cycle.

The selected bundle is
`.work/images/xiri-netbsd-desktop-20261104-scheduler/`. Its 8 GiB disk compresses
to 496,124,430 bytes. CHD SHA-256:
`b6e5c89ef897f441e0c8cfbb5f174a23f082383414c8fb64105500c971992d36`.
The complete extracted raw disk matches the prepared disk at
`a92779efc0a336d8ab6b17d5872ee08d58f66065b0463eade83892309c8c9268`.
It includes the previously qualified native CD9660 core correction from
NetBSD `xiri` commit `0cd56e7a286c4cd3d67ab7cc971b233a83ac1655` and retains
the pinned IRIS `819c682` backend.

Preparation run `.work/xdm-image/prepare/ordinary-yo7lyhvg` passes inherited
payload verification, graphical disk reboot to the 1280×1024 greeter and
clean shutdown. Its installed-file inventory changes only
`/etc/xiri/xdm/Xservers` and `/usr/local/bin/xiri-desktop` relative to the
unpromoted CD9660 image. Both native account/password databases and all GIMP,
GNOME, terminal-helper and Acrobat resource ledgers remain identical. No
diagnostic guest profiles or live memory changes enter the prepared disk.

The preparation command, after materializing the candidate's verified raw
seed in a separate directory, is:

```sh
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261104-scheduler \
  --kernel-build .work/netbsd-stability-build \
  --keep-accounts --refresh-xservers
```

## Cold-image acceptance

The [stability/application record](2026-11-04-xorg-scheduling-stability.json)
comes from `.work/system-stability/boot-ngwyswbu`. It verifies the unchanged
Xorg binary and actual startup `-dumbSched` argument, all 158 CD9660 checks,
60 native input round trips / 120 button events, and 60 native pointer-query
controls. Both transports run at the greeter, under xiritest/4Dwm and under
netbsdtest/ctwm, with the expected UIDs recorded. Twenty detached-child launch
cases and sixteen adversarial cases also pass. GNOME Terminal runs the
interactive original shell in the correct home, saves/reopens its preferences
and exits normally twice. All six catalog-launched Acrobat PDF/capture/focus/
exit sequences pass: three original helpers and three traced helpers. The
guest logs into 4Dwm again and cleanly unmounts/halts with the desktop active.

The independent [disk/session record](2026-11-04-xorg-scheduling-image.json)
comes from `.work/irix-xdm/runs/ordinary-7h4n2cb6`. It verifies graphical
disk autoboot, filesystem module loading at securelevel 1, rejected credentials,
three IRIX sessions, both logout menus, failed-startup recovery, netbsdtest's
standard ctwm/home/wheel membership, catalog xmahjongg launching and FAM
execution notification. All three rendering controls compare 8,536 pixels
with zero mismatches. Three untouched winterm starts retain the bitmap-font
geometry, and foreground resize delivery and a normal terminal exit pass.
Services and an independent login survive session transitions, no new rpcbind
bind warnings appear, and the guest cleanly unmounts/halts.

Both source CHDs remain unchanged. The earlier diagnostic guest also halts
cleanly; its original failed setup result remains an error. All owned test
emulators are stopped. The 38 host tests pass, guest helpers compile with
warnings treated as errors, and the previous manual CHD, overlay and recorded
NVRAM profiles retain their hashes. This cycle does not repeat the preceding
96 MiB paging qualification or establish a universal absence of stalls.

PNGs: [4Dwm/catalog](images/2026-11-04-xorg-scheduling-image.png),
[native ctwm](images/2026-11-04-xorg-scheduling-image-native.png),
[xdm](images/2026-11-04-xorg-scheduling-image-greeter.png),
[untouched winterm](images/2026-11-04-xorg-scheduling-image-winterm.png),
[Reader](images/2026-11-04-xorg-scheduling-image-acrobat.png), and
[reopened GNOME preferences](images/2026-11-04-xorg-scheduling-image-gnome.png).

The new-cycle and active-day IRIS upstream checks are recorded in
[FORKS.md](../FORKS.md). Upstream is unchanged and already integrated; neither
fork needs a new source change for this correction. No vendor bytes are
changed or added.

The earlier native child-control stalls and catalog-batch halt remain separate
open observations. This scheduling finding does not establish their cause.
Type1 metrics, Xft/Render text and application-specific limitations also remain
separate work. Reassess the scheduler option when replacing the old X server.
