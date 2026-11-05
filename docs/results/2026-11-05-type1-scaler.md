# Type1 collapse traced to native MIPS signal return

The scalable IBM Courier failure is caused by native NetBSD floating-point
state loss on signal return. The MIPS `fpu_discard()` wrapper clears the PCU
valid bit immediately before its callers install replacement registers. On
the next floating-point instruction, the lazy FPU loader treats that saved
state as first use and zeros it. This affects native programs, including Xorg
and Xvfb; it is not an IRIX font-resource or Newport drawing defect.

NetBSD `xiri` commit `3b25e6cf2251f180c89027d00b33ee1c29933517` changes
`pcu_discard(&mips_fpu_ops, l, false)` to `true` in
`sys/arch/mips/mips/mips_fpu.c`. All three MIPS callers replace saved state:
`cpu_setmcontext`, `process_write_fpregs` and the legacy signal-return path.
The IRIX signal adapter already preserves validity explicitly after
`cpu_setmcontext`; that code remains unchanged. The rebuilt IRIX module is
byte-identical to the selected image's module.

## Observed failure

The preserved 2026-11-03 failure snapshot was restored in a private copy,
using its pinned emulator. Native Xlib reproduces ascent/descent `1/1` for
the bold 20-pixel IBM Courier request, while horizontal advance remains 12.
Drawing `MMggCourier` into an X pixmap produces only seven ink pixels on one
row. Healthy output has ascent/descent `17/4`, 643 ink pixels and bounds
`10,31,140,47`. Direct FreeType rendering in the same guest is healthy;
a new 21-pixel instance and the regular 20-pixel face also work.

Read-only inspection of the captured Xorg core finds a cached 14.5-point
transform and normal 12-pixel advance, but the associated FreeType size has
`x_ppem=y_ppem=1` and `x_scale=y_scale=5833`. The latter is FreeType's minimum
one-point size at 100 dpi. The installed libXfont disassembly converts the
scale using a live floating-point register before calling `FT_Set_Char_Size`.

A fresh native Xvfb in that diagnostic guest reproduces the chain during
font churn: iteration 55 opens a collapsed 32-pixel italic Courier, and the
trace records `FT_Set_Char_Size` call 75 with `request=0,0`. FreeType accepts
the request and clamps it to its minimum. Independently, a native arithmetic
probe under SIGALRM turns `(int)(14.5 * 64 + .5)` from 928 into zero after its
first signal. Neither reproduction depends on an IRIX client or Newport
window rendering.

The failing snapshot is evidence for this state, not a claim of whole-disk
snapshot consistency: its copied disk overlay was from a later point. The
original snapshot, prior qualified CHD and manual overlays are preserved.
Native GDB crashed while inspecting the core. Host cross-GDB could inspect
the typed heap objects but did not produce a valid backtrace; no stack-based
claim relies on its incorrectly decoded PC.

## Fresh baseline and candidate checks

The [native fixtures](../../lab/type1-scaler/README.md) use the guest's compiler
and installed libXfont 1.5.4 / FreeType 2.10.4. The comparison cold-boots a
private clone of the qualified fonts image, runs the baseline, installs only
the candidate core and boot wrapper, cleanly halts and cold-boots again.
The emulator, Xorg, libraries, font files, Newport driver and IRIX module are
the same across those two phases.

The native register fixture checks all 32 o32 FPR words and FCSR, ordinary
and `SA_SIGINFO` handlers, handlers that deliberately overwrite FPU state,
all four rounding modes and a sticky exception flag. On the baseline all
eight no-signal controls pass, while all sixteen signal cases lose all 33
checked words. On the candidate all 24 cases pass. The arithmetic baseline
fails at iteration 3768 after its first signal; the candidate completes
200,000 conversions with 38 signals and no mismatch.

The fresh baseline's 560-operation font churn passes. That does not contradict
the separately captured failure: a signal must arrive while the size operand
is live. The deterministic register comparison establishes the correction;
the font trace connects that fault to the observed glyph collapse.

The candidate completes all 560 font operations. Its 588 FreeType size
requests have the expected positive values, ppem and scale at all seven
sizes. All twenty bold-20 pixmap checks contain the same 643 ink pixels.
Direct FreeType's six load/render cycles match the baseline exactly.

All 24 original IRIX FPU signal records pass the established byte-level
validator: o32/n32, direct/indirect calls, legacy/siginfo/child paths, root
and UID 1234. Native signal and time controls also pass under both identities.
Native and original IRIX Xlib agree on healthy metrics over six fontset
create/free cycles. The first desktop checker incorrectly expected one font
per set from both libraries; original IRIX returns two matching fonts. Its
failure is retained, and the corrected checker validates every font and set.

An xiritest winterm explicitly selecting the affected Type1 face starts at
983×504 with 12×21 cell increments and a 24×80 terminal. Typed commands work;
the foreground witness receives SIGWINCH and observes 21×66 after resizing.
Typing `exit` gives status zero and removes the process/window, with empty
stderr. The guest then cleanly unmounts and halts.

The [qualification record](2026-11-05-type1-scaler.json) is checked by
`scripts/qualify-type1-scaler.py`, including register words, all FreeType size
requests, rendered pixel counts, IRIX records and actual compiled-source
hashes. The [PNG](images/2026-11-05-type1-courier.png) is an unchanged ordinary
IRIS GL scanout capture.

## Build and reproduction

The [build ledger](../../lab/type1-scaler/build.json) retains its actual
parent revision `0cd56e7a286` and dirty source status. The
[source-equivalence check](../../lab/type1-scaler/source-equivalence.json)
verifies the exact patch and source hashes against the later clean commit;
it does not relabel an old binary as a new build. The
[image pin](../../lab/type1-scaler/baseline.json) selects those artifacts.

| Artifact | SHA256 |
| --- | --- |
| Native kernel | `e61215790f6d8e0e37329329b2fabf36a3b5557a0d61bee71f26b1a691e1fe3a` |
| Boot wrapper | `097bad8184b51ff5686174b0fdca8ceab2ce29905590668753a0ca07198faa64` |
| Unchanged IRIX module | `37c8a5114483ad834d0dbef551175e506a1874599aa8caf70366481be7559b2f` |

Primary evidence remains under `.work/type1/qualification-knnth2vm`, with
baseline/candidate logs, frozen harnesses and media hashes. The assembly
fixture was corrected before the first guest compilation to take the native
signal number from C instead of including a C-only header; the actual CD
replacement and compiled source hashes are recorded. The failing diagnostic
is `.work/type1/restore-q16fc42g`; the core archive is
`.work/type1/restored-core.tgz`, SHA256
`5f5175ef84b9d19e304025a2caae094f4a657e0fd6f06df21e83fadc27bb14cc`.
The healthy reference is `.work/type1/ordinary-q_kl88sc`. All three guests
halted cleanly and their input CHDs remained unchanged.

The independent [system regression](2026-11-05-type1-system.json) cold-boots
the same replacement kernel and unchanged module in another clone. It passes
158 CD9660 checks, 120 native input round trips over Unix/TCP at the greeter,
4Dwm and ctwm, twenty detached-child launches and both adversarial cleanup
suites. Both users return to the greeter; services survive logout. A final
active 4Dwm session shuts down with clean unmount and halt markers. The
input-timeout negative control fires as intended and is separate from those
successful input checks. The run is `.work/system-stability/boot-5vpdoys8`.

The [replacement CHD](2026-11-05-type1-image.md) passes its separate cold
disk/desktop qualification and is selected for manual testing. It preserves
the inherited fonts, resources, module and account layout.

## Scope

The desktop retains the bitmap Adobe Courier default selected for its closer
IRIX appearance. No additional fonts or replacement FreeType/libXfont build
are required. Xorg retains `-dumbSched` for the independently reproduced XTest
dispatch starvation; this FPU fix does not qualify removing that setting.

The register execution controls cover native o32 userland on the mips64eb
R4400 kernel. Native n64, ptrace, legacy NetBSD signal trampolines, other MIPS
machines and physical SGI hardware are not execution-qualified here. The
earlier native child-control stalls and catalog-batch halt remain distinct
open observations; this finding alone does not establish their cause.
