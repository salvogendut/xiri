# Native stability and CD mount translation

This cycle pauses individual application repairs to investigate native input,
process supervision, session teardown and shutdown. The starting failures are
the two native child-control stalls in the [catalog bootstrap exclusions](2026-11-03-irix-catalog-bootstrap.json),
the [failed catalog-batch halt](2026-11-03-irix-catalog-shutdown.json), and the
transient native XTest timeout in the [Acrobat image checks](2026-11-04-irix-acrobat-cold.json).
The original runs remain retained; none yet establishes a common cause.

## Reproduction and diagnostics

The [maintained probe](../../lab/system-stability/README.md) cold-boots disposable
copies of the qualified images with their exact IRIS emulator. It verifies
actual native mouse-event delivery over Unix and TCP X connections, with
per-stage monotonic timestamps and a ten-second watchdog. A deliberately
held X server checks timeout detection and subsequent recovery. Native detached
children, timed termination, double-fork/setsid, rapid child exit, failed exec,
signals and logout exercise the existing session guard. Both xiritest/4Dwm and
netbsdtest/ctwm run at 1280×1024; boot services must survive their logouts.
The memory-load option retains dirty native pages across these checks and
records VM counters. Active-desktop shutdown requires fresh kernel
clean-unmount and halt markers.

Failures retain CPU/register/stack diagnostics, the graphical console, the
kernel message ring and guest logs. A process merely having a PID is not
reported as working. Host phase durations include serial command/evidence
transfer; they are not desktop performance benchmarks.

## Native CD9660 defect

Test scripts copied from the probe CD had mode `000`, despite mode `0644` in
the ISO's Rock Ridge directory. This is a native NetBSD32 issue: our o32
`mount_cd9660` uses the modern 132-byte mount argument structure, but the N64
kernel translated only its 116-byte prefix. It then passed a full native
structure with zero UID/GID/mask fields to CD9660. File and directory masks
became zero, ownership overrides were ignored, and `MNT_GETARGS` returned only
the old prefix. Explicitly installing test helpers with readable/executable
modes bypasses the fixture symptom; it does not fix CD access.

NetBSD `xiri` commit `0cd56e7a286c4cd3d67ab7cc971b233a83ac1655`
extends `netbsd32_iso_args` and translates the
four missing fields in both directions. Legacy-sized and zero-length calls
retain their original buffer size and pass the old native layout through to
CD9660, which supplies default masks or preserves an existing mount's masks
on update. Truncated modern structures are rejected. The IRIX module remains
byte-identical; this correction belongs to the native core.

The real guest regression covers modern masks and ownership, ordinary-user
reads, zero masks, legacy and zero-length callers, legacy updates, guarded
input/output buffers, extra output capacity, truncated sizes and bad pointers.
The original kernel failed 92 of 158 checks. The initial corrected-kernel
fixture reported 12 expectation errors: UID/GID without override flags are
ignored by the native filesystem and correctly query as zero. The final
fixture follows that implementation. These prototype results are preserved
separately from qualification.
The corrected fixture passes all 158 checks on the candidate core. Its
[build ledger](../../lab/system-stability/build.json) records the exact native
kernel, boot wrapper, unchanged module and source hashes. Correcting the
unflagged-owner expectations does not change the original kernel's 92 failures:
its unreturned fields still contain the output-buffer sentinel.

## Harness corrections and retained exclusions

- `boot-fcgbpx09`: unreadable copied CD script; 80 native input cycles completed
  before the setup error. Clean halt, source image unchanged.
- `boot-x8dgu_72`: the probe incorrectly assumed xiritest's authority was in
  its home. xdm supplied `/tmp/.Xauth*`. The greeter's 200 input cycles,
  40 detached-child launches and adversarial cases had passed. An explicitly
  recorded manual continuation used the real authority, completed IRIX input
  and child tests, logged out, checked native ctwm input with its home authority,
  and halted with ctwm active. The original failed result remains a failure.
- `boot-xbrq_lu8`: the candidate core booted and restored CD access, but the
  fixture's 12 unflagged UID/GID expectations were wrong. Both preparation and
  candidate halt were clean. A new qualification clones this clean candidate
  state and verifies its exact artifacts; it does not promote the prototype.
- `boot-10_528cr`: CD checks, 200 input cycles and 40 detached-child launches
  passed with a 96 MiB native allocation. The live-burst fixture's 1.2-second
  deadline interrupted startup before all 25 intended processes existed:
  22 were tracked and 20 reached their ready-file writes. The guard reported
  `absent=1 valid=1 remaining=0`; its 10.423-second elapsed time includes the
  delayed creation/cleanup under paging. The VM snapshot recorded 191 pages
  swapped out and 24 pageout requests. This was a failed startup-count assertion,
  not evidence of leaked descendants. The revised fixture waits for 25 ready
  processes before requesting teardown, retains the exact 25-process check,
  and allows the separate 49-process exit burst a bounded minute to complete.
  Its replay passes with the same allocation still present. The fixture's exit
  trap also cleans up its owned supervisor if readiness fails.

`ps` can omit `XAUTHORITY` when the native user uses the home default. The probe
now follows the IRIX session's recorded authority and uses the native process's
authority or its home default. These fixture failures are distinct from the
earlier unexplained guest stalls.

## Qualification and limits

The [qualification record](2026-11-04-system-stability.json) retains two primary
cold boots, their exact harness/media hashes, guest archives, input-stage
timings, guard summaries, VM snapshots and fresh kernel halt messages.

| Run | Native input cycles / delivered button events | Native child-launch cases | Adversarial cases | CD checks | Halt |
| --- | --- | --- | --- | --- | --- |
| Original GIMP image, `boot-j7cao0am` | 600 / 1,200 | 80 | 16 | 158 checks, 92 known failures | Clean, active IRIX desktop |
| Corrected core on Acrobat image, `boot-_952x06p`, 96 MiB allocation | 600 / 1,200 | 80 | 16 | 158 checks, zero failures | Clean, active IRIX desktop and independent memory job |

The baseline's stability pass does not qualify its defective CD mount ABI.
The [baseline CD log](2026-11-04-system-cd9660-baseline.log) and
[corrected-core CD log](2026-11-04-system-cd9660-candidate.log) preserve those
separate results and the fixture revisions described above. The candidate
clones the cleanly halted installation from `boot-xbrq_lu8`, cold boots it and
verifies the installed core, boot wrapper and module hashes. Both source CHDs
and the candidate's seed overlay remain unchanged.

Each primary run checks the greeter, xiritest/4Dwm and netbsdtest/ctwm over both
Unix and TCP connections. That totals **1,200 input cycles and 2,400 delivered
button events, 160 child-launch cases and 32 adversarial cases**. Both users
return to the 1280×1024 greeter, with the same live xdm, FAM and rpcbind service
PIDs. A fresh IRIX login precedes shutdown. The separate server-grab controls
trigger the expected watchdog and recover after release. Neither normal run
has an input timeout; the largest measured individual blocking stage is
0.212 seconds on the baseline and 0.137 seconds on the candidate, including
the intentional 100 ms button-release delay. These are guest-clock diagnostic
measurements, not a comparative performance benchmark.

The candidate retains a 100,663,296-byte allocation with every page dirtied in
an independent UID 1234 process across both logouts. Its VM snapshot before
shutdown reports 2,360
pages swapped out, 299 pageout requests and 1,894 swap pages in use, with
8,192-byte pages. The revised live-burst cases track all 25 intended processes
and clean up all descendants, taking 11.566 and 16.527 seconds including
startup under paging. Both 49-process completion bursts also pass. This
demonstrates why a short fixed startup timer was an unreliable fixture.
Shutdown completes swap removal, filesystem unmount and halt with that memory
job and the IRIX desktop initially active.

Screenshots retain the full-size [IRIX desktop](images/2026-11-04-system-stability-irix-1.png),
[native ctwm desktop](images/2026-11-04-system-stability-native-ctwm.png) and
[IRIX session before shutdown](images/2026-11-04-system-stability-active-before-halt.png).
The build and module import/relocation audit pass; 38 existing host tests,
native helper compilation with warnings treated as errors, shell/Python syntax
checks and `./xiri doctor` also pass. Doctor verifies all 16 immutable image
artifacts. All owned IRIS instances are stopped.

The maintained runner has one reporting-only change after the tested snapshot:
its installed-artifact fields now contain only verified artifact/build hashes.
In the retained raw candidate result, `installed_kernel` copied the input pin's
source/debug fields while replacing its native/boot hashes. Use
`candidate_kernel` and the committed build ledger for the replacement core's
provenance. The raw result and tested harness are preserved unchanged.

These are two bounded runs, not an extended soak. They do not replay the exact
earlier Acrobat PDF/software-framebuffer transition. The original native child
stalls, failed catalog halt and transient XTest timeout remain unresolved; the
native CD bug does not establish their cause. Keep the new diagnostics in the
next reproductions rather than attributing every slow startup to an IRIX app.
Per-application repair remains deferred. The selected manual CHD remains the
previously qualified Acrobat image; packaging and qualifying the new core in
a replacement manual image is a separate step.
