# Native sleep delays under memory pressure

The independent native probe reproduces the desktop pressure stall without
Xlib or IRIX system calls. Two original-kernel runs lose 13.5 and 13.7 seconds
in both a child requesting 200 ms and its independently sleeping observer.
A separate sampled run locates sustained software AES work in `pgdaemon`.
The cleanup postcheck also has a reproducible exit/reap race. The revised
kernel and fixture pass the full desktop pressure gate and the separate
encrypted-data readback control. A fresh packaged-image timing run then
crashes the kernel during desktop startup, blocking promotion. The selected
manual image is still the native-wait bundle.
The [packaged-image report](2026-11-05-native-paging-image.md) records the
subsequent passing cold desktop check and screenshots. Source changes and
evidence are checkpointed; the isolated crash remains deferred.

## Original-kernel evidence

`native-_qotjx9b` and `native-iqlyn9vr` both complete all unloaded-greeter
and greeter-pressure timing cases. The first desktop `usleep` case then
exceeds its unchanged ten-second watchdog; later `nanosleep` and `select`
cases complete. The requested interval is 200 ms throughout. Parent and
child are native NetBSD processes, and the child records no major faults.

The largest observer gaps are 13.513827515 and 13.712078454 seconds.
During them, swap use grows by 290 and 273 pages, device interrupts continue,
and nearly all CPU ticks are kernel time. The free count rises from 123/126
to 680 pages, four times the 170-page target. The native trace confirms that
both LWPs spend the interval inside nanosleep; this is not an erroneous
seconds/nanoseconds conversion by the IRIX personality.

Reordering the methods in `native-9uqmmdmy` makes the first desktop
`nanosleep` case time out after eight completed iterations, while subsequent
`usleep` and `select` cases pass. Monitor samples repeatedly locate software
AES in the page daemon, identified by its live LWP name `pgdaemon` and LID
99. The sampler pauses the emulator for each read, so this run establishes
where work occurs, not an unmodified timing result. Apparent code addresses
on its stack are not a complete unwound backtrace.

The page daemon has higher scheduling priority than user processes. Its
scan builds toward four times the free target, and software swap encryption
runs synchronously while constructing pageouts. MIPS kernel preemption is
disabled in this fork configuration. These observations support pageout CPU
monopolization as the cause of the captured native stalls; they do not prove
that every historical application or shutdown stall has this cause.

## Swap-control defect

The original `vm.swap_encrypt` handler gives a one-byte `CTLTYPE_BOOL`
operation an `int` temporary. On this big-endian kernel, reading enabled
state reports zero and writing zero can leave encryption enabled. A monitor
read of the actual kernel boolean returns `0x01` despite the reported zero.
The attempted plaintext comparison `native-rt8bq751` is therefore invalid
and is retained as an interrupted diagnostic, not a plaintext pass.

The handler now uses a `bool` temporary and an atomic load, retaining its
existing lock-protected write. A native control disables configured swap, performs
false/true/false/true requests with one-byte readback, and leaves the final
request enabled. The original kernel fails both true readbacks; the corrected
kernel passes all four. Encrypted swap remains the deployment default.

## Cleanup postcheck

`boot-osm2yg4q` traces the failed shell assertion after the guard reports
all 25 descendants tracked and zero remaining. `kill -0` succeeds, the
following `ps | grep '^Z'` fails, and a later diagnostic `ps` finds no process.
The first `ps` output is not retained, so that observation alone cannot prove
its state. The original two-query assertion can reject a process reaped
between the queries.

The fixture now makes one `KERN_PROC2` query, accepting absence or a terminal
state and rejecting live processes, query errors and malformed responses.
Its real-child control deliberately keeps a zombie with WNOWAIT, checks it,
reaps it between the old two queries, and requires the old assertion to fail
while the new one accepts absence. A live pipe-held child must still fail.
The 25-process live burst, 49-process completion burst, unrelated same-user
sentinel and installed guard's six-second cleanup grace remain unchanged.

## Candidate progression

The first candidate pauses for one tick after 100 ms of scan work once the
actual free target is met. It preserves encryption and the existing watermarks.
`boot-hyqc8uvm` still fails the first desktop input round: the nominal 200 ms
delay lasts 4.506 seconds, button synchronization another 5.195 seconds, and
the ten-second watchdog fires during connection close. Its greeter input and
eight supervisor scenarios pass, and it halts cleanly. This is not a full
pressure pass.

The same pageout change plus the boolean correction in `native-7oqpzrvn`
completes all 900 native sleeps. Its worst sleep is 1.893402757 seconds and
largest observer gap 2.999275939 seconds. The swap-control source and ELF
match the baseline control byte for byte. The separate memory readback
matches all 24,576 written bytes, but its major-fault count stays zero:
those pages remained resident. The run correctly remains `error` because
swap-in was not proved; it collected its archive and halted cleanly.
The first revised control deactivates that mapping and adds 32 MiB briefly.
`native-zsqysjp7` still reads resident data: all 900 timing cases pass, but
swap-in remains unproven and the whole run remains an error. Its worst sleep
is 3.281228818 seconds. The dedicated replacement control grows pressure in
bounded 8 MiB increments and uses `mincore` to require at least 128 genuinely
nonresident pages before readback. A temporary 128 MiB swap file on the
disposable disk prevents exhaustion while forcing this condition; encryption
remains enabled. This control is separate from the 96 MiB timing matrix.

Its first run, `native-42m0jeju`, reaches 214 nonresident primary pages with
72 MiB of extra pressure, then ends without a final readback marker. The
launcher reports zero, but the missing marker correctly fails the run.
Its complete archive and clean halt are retained. The original control did
not record the terminating signal; it is not a successful integrity check
or evidence of data corruption. The revised control releases the extra
pressure before verification, checks primary residency again, and records
phase times, a timeout marker, native traces and the inner child's status.
The inspected PAM `su` source can mask signal termination through an unchecked
`WEXITSTATUS`; acceptance requires both statuses and the final data marker.

The revised candidate also counts submitted pageouts toward the pause
threshold, as the existing scan termination does. Pending I/O completion
may need CPU time before those pages become free. The pause occurs without
page-owner or page-queue locks held, and scanning remains uninterrupted
while free plus submitted pages are below the minimum target.

Both the earlier boolean-corrected candidate (`boot-wbz2fp4t`) and the final
candidate (`boot-wtpd08jl`) pass the full gate: 800 native input round trips,
120 native child launches, 24 existing adversarial supervisor scenarios,
three new process-postcheck controls and 158 CD ABI checks. Each completes
two IRIX sessions, the native ctwm login, both IRIX logouts and shutdown with
an active IRIX desktop. The 96 MiB allocation, ten-second input watchdog,
25/49 descendant counts and six-second cleanup grace are unchanged. Both
archives are complete and both guests halt cleanly.

The final kernel's `native-nhofgfl6` and `native-zsqysjp7` runs each complete
all 900 sleeps and all four swap-setting transitions. Their largest completed
sleep intervals are 4.634752242 and 3.281228818 seconds. These are improvements
over the captured watchdog failures, not a hard latency guarantee. Both
whole runs remain errors because the earlier readback fixtures failed to
prove nonresident data; the separate forced swap-in check must close that
gap before image promotion.

`native-esih3j6l` closes the data-integrity gap on the packaged kernel. It
releases 80 MiB of extra pressure after eviction, confirms 752 primary pages
remain nonresident, and checks all 24,576 bytes written in its 96 MiB primary
mapping. Major faults increase from 4 to 756 and the final marker is valid.
Both child and launcher statuses are zero, the archive digest matches, the
temporary swap file is removed, and shutdown is clean. The readback takes
107.846 guest-monotonic seconds including pressure setup. It does not qualify
readback while the extra pressure remains held.

## Packaged-image kernel crash

`native-0enmhxsy` passes the four swap-setting controls and all 600 greeter
sleeps, then fails while starting the IRIX desktop under the held 96 MiB.
The kernel ring records native PID 712 (`sh`) taking an instruction-address
error at invalid PC/RA `0xdef962fbba636ebe`, followed by a fault in the debugger.
The original trap frame contains invalid saved callee registers. Nearby
stack words resolve to the vnode/page-array fault path, but this is not a
complete backtrace or a proven corruption source.

The guest cannot halt cleanly. Its CPU, MMU, stack and display were captured;
the complete emulator snapshot, RAM chunk store and a separate reflink of
the crash disk overlay are retained under that run. The failed controller
was paused only for capture, resumed afterward, and the unusable owned IRIS
process was stopped. Earlier stress passes do not override this failure.
The bounded encrypted (`native-2ilns0iv`) and plaintext (`native-651yeudy`)
comparisons each complete all 900 sleeps and all four swap-control cases,
collect verified archives and halt cleanly. Both carry a narrow conditional
trap-entry breakpoint to preserve evidence before debugger recursion. These
are instrumented diagnostics, not unmodified timing qualifications. Neither
reproduces or explains the crash; plaintext is confined to the disposable
comparison guest and is not a deployment change.

Further investigation is deferred at the user's request to keep this cycle
bounded. The cache hypothesis remains unproven and no speculative cache
change is included. The existing manual CHD stays selected. The source fixes
are committed on NetBSD `xiri` as `0febc6eb24ad889d12a3b2afaa12558c9781859d`;
the [source-equivalence record](../../lab/native-paging/source-equivalence.json)
checks every recorded source hash against that commit without rewriting the
actual pre-commit build provenance.

## Evidence handling

Early native archives exceeded the serial collector's 300-second deadline.
Their complete gzip archives were recovered through the local NAT gateway
with matching guest/host SHA256. The failed controller results remain failed.
`native-_qotjx9b` did not verify a clean halt and retains a timecounter warning
during recovery; `native-iqlyn9vr` subsequently halted cleanly. The reordered
sampled run collected normally and halted cleanly. An earlier observer version
mistook an exit-query ESRCH for an observer failure; the revised observer treats
it as a missing sample and lets waitpid alone decide completion. A WNOWAIT
exit-37 control checks this case.
Final native timing acceptance also requires the probe's own successful
completion record; the launcher's zero alone cannot mask signal termination.
The retained passing cases satisfy that stricter check.

The maintained archive transfer binds host loopback, has bounded timeouts,
and publishes a file only after successful producer completion and digest
comparison. Host tests reject truncated/corrupt transfers and producer errors.
The final host suite passes all 52 tests, including rejection of missing,
failed or mismatched native sleep completion records despite launcher zero.
The pinned LP64 big-endian trace reader checks its 56-byte header against the
kernel's DWARF and rejects six malformed controls; guest o32 kdump misreads
the timestamp layout. No diagnostic interposer is installed in a test image.

The reduced traced run also shows a stale capture: its original failure PNG
is byte-identical to the earlier greeter PNG, while an explicit frame wait
then captures the actual 4Dwm desktop. Both are retained. The desktop PNG is
visually readable with winterm, xmahjongg, catalog and background icons.
This identifies a stale-frame case in the diagnostic capture path; it does
not establish the cause of every earlier entirely black capture. Cold-image
visual qualification still uses the independent frame-wait checks.
