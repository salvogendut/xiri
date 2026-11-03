# Newport display correctness and performance

The user reports that the NetBSD/Xiri display feels less responsive than
original IRIX. The [framed-console/XAA cycle](results/2026-11-02-newport-framed-acceleration.md)
now fixes the measured RGB24 color/mask mismatch in IRIS. Native XAA and
software controls pass the same expanded drawing/input checks and produce
identical screenshots. The [xmahjongg follow-up](results/2026-11-03-newport-xmahjongg.md)
also repairs clipped/repeated Render textures in the Xorg Newport driver.
The accelerated game now matches the software-rendered game across all
617,684 pixels of its window, with Composite enabled and a 32-bit visual.
The earlier software-rendered image is preserved as a control.

On 2026-11-03 the user manually tested the accelerated CHD and found it
noticeably snappier and more usable than software rendering, despite the
remaining glitches. It is the accepted development baseline for the
xmahjongg follow-up. This is user-observed responsiveness, not a controlled
benchmark. Preserve its manual overlay/NVRAM and the earlier software image;
run diagnostics on disposable copies of the frozen prepared disk.

## Components to investigate

| Component | Responsibility and current evidence |
| --- | --- |
| NetBSD kernel `sys/arch/sgimips/gio/newport.c`, `newportreg.h`, `newportvar.h` | wsdisplay console, device access/mapping, display state and console drawing. The driver uses bus_space accessors and REX3/DCB FIFO waits. |
| Xorg `xf86-video-newport` in NetBSD xsrc | X rendering, shadow uploads and optional XAA acceleration. Separate from the kernel console driver. The new candidate replaces the release-set module with the pinned [texture correction](../lab/newport-xaa/README.md). |
| IRIS Newport emulation | Executes the emulated REX3 operations and produces framebuffer pixels. Its interpretation must match the register and plane formats expected by both operating systems. |
| Xiri compatibility and application behavior | Adds syscall/runtime work for original IRIX clients. Compare a native X client against the same workload in an IRIX client before assigning rendering delays to compatibility. |
| Host frontend and emulator build | Rendering mode, JIT/interpreter selection and CPU scheduling can change perceived speed. Use matching machine profiles and record the exact builds for comparisons. |

The [original accelerated-color finding](results/2026-10-30-netbsd-x11.md#accelerated-color-finding)
was reproduced with the current integration build: red `0xfe` became
`0x092492` in fills and copies, while uploads were correct. IRIS `xiri`
`819c682` corrects COLORVRAM and WRMASK interpretation for RGB24. NetBSD's
Xorg driver follows the documented physical plane layout; the later userspace
texture correction addresses a separate defect.
The generic, generated LLVM and Cranelift paths share the corrected semantics;
other depths/planes and physical hardware remain separate validation work.

## Supplied SGI manual

The additional hardware collection at `../sgi` supplies a more specific
reference: its `sources.json` entries `asic-rex3` and `asic-rb2`. REX3
section 3.9, table 22, describes RGB24 physical planes; the
[RB2 specification](https://erikarn.github.io/sgi/indy/datasheets/sgi_indy_rb2.pdf)
section 4.2 describes direct write-mask delivery and bypass of the normal
formatter during fast clear. Table 4.4 repeats the physical layout. These
support NetBSD Xorg's `NewportColor2Planes24` encoding: physical bits 23..0
are B0, R0, G0 through B7, R7, G7, while IRIS stores packed BGR pixels.
Decode COLORVRAM and WRMASK at the rendering boundary; retain raw register
readback and the existing COLORI/HOSTRW formats. The
[source manifest](../lab/newport-accel/hardware-sources.json) records local
copies, hashes and sections. This establishes a documented emulator
correction; it is not a physical-Indy validation.

The local reference is *IRIX Device Driver Programmer's Guide*, document
007-0911-110, 882 PDF pages:

`/var/home/salvogendut/Downloads/RUNIRIX/007-0911-110.pdf`

SHA256: `ba2ed883084de76e99ce3cbf00d8811966bff543e94db59ca73623fe9c97cac9`.
The PDF and extracted text remain outside Git. The
[IRIX7 technical-publications index](https://irix7.com/techpubs.html) also lists
this document and other revisions; the broader [IRIX information sources](IRIX-RESOURCES.md#irix-information-sources)
are tracked with the resource checklist. These are useful sections:

| Printed pages | PDF pages | Relevance |
| --- | --- | --- |
| 9 and Chapter 1's address/cache discussion | 53 onward | Uncached device register access and the difference between device addresses and cached memory. Translate the concepts to NetBSD bus_space and its sgimips implementation. |
| 169–177 | 213–221 | Device memory mappings and user/kernel responsibilities; useful when reviewing wsdisplay mappings and Xorg access. |
| 219–220 | 263–264 | DMA cache maintenance and flushing buffered PIO writes before dependent reads or deliberate device delays. Avoid adding indiscriminate flushes to every graphics access. |
| 673–681 | 717–725 | GIO address spaces, attachment, interrupts and PIO. The PIO example also illustrates avoiding a completion interrupt/sleep race. |
| 682 onward | 726 onward | Generic GIO DMA and cache considerations. This does not establish a Newport DMA capability or prescribe one for Xiri. |

Chapter 19 primarily describes Indigo2 GIO64 and distinguishes the older
32-bit GIO used by Indy. Its platform-specific details need to be checked
against the actual board. The text contains no Newport, REX3, VC2 or XMAP
register reference. It supplies useful bus/driver background, but cannot
by itself resolve COLORVRAM/WRMASK plane encoding or justify enabling XAA.
IRIX APIs in the examples must be translated into NetBSD equivalents.

## Next performance cycle

The native xdm integration exposed another text case on 2026-11-03: the
standard Xft greeter painted its frame and logo but no greeting, prompts or
typed username. Installed fonts resolve correctly (`Sans` selects Luxi Sans),
and disabling antialiasing alone did not restore the labels. `Xft.render:
false` restores them using software text, with XAA still enabled. The
opt-in xdm resource overlay contains this workaround. Isolate the native
Render glyph path with a focused client and accelerated/software server
controls before assigning the underlying fault to the driver or emulator.
The earlier texture/pixel checks do not cover this glyph workload.

Xdm explicitly uses the same `1280x1024` mode and `Virtual 1280 1024` as the
qualified manual launcher. The pinned IRIS scanout captures are 1282×1024
(two additional columns); the active X desktop is 1280×1024. A smaller X
root such as 1024×768 must fail xdm qualification. Do not rely on bare
`startx` selecting this configuration automatically.

1. Completed for RGB24: solid-fill, copy, upload and composed-framebuffer checks with
   acceleration disabled and enabled on the same image and emulator build.
   Extend the existing `scripts/qualify-netbsd-x11.py --accelerated` workload
   rather than accepting an attractive screenshot as a correctness test.
2. Completed for RGB24: resolve the measured fast-clear/plane-mask mismatch against documented
   register definitions and original IRIX observations. Preserve the other
   depth/plane combinations when changing IRIS or the Xorg driver.
3. Completed for the reproduced xmahjongg corruption: correct XAA texture
   coordinates and A8 solid-color byte order in the Xorg driver. A focused
   8,536-pixel regression fails before the patch and passes afterward, as does
   software rendering. Keep broader Render/operator/depth qualification separate.
4. Measure native Xorg fill/copy/upload/text and window movement with host
   elapsed time and explicit X synchronization. Record CPU use and display
   configuration; use equivalent hardware/frontend settings for IRIX.
5. Extend accelerated coverage to other Render operators and the remaining
   depth-32 plane-mask failure. Investigate winterm's startup font metrics,
   then profile remaining compatibility or frontend costs. Do not assume
   every delay originates in the kernel driver.

Continue desktop behavior work alongside measured graphics performance. Icon
Catalog artwork was repaired separately through the filetype database locks
and native FAM resource mapping.
