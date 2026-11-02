# Newport display correctness and performance

The user reports that the NetBSD/Xiri display feels less responsive than
original IRIX. The current manual image uses native Xorg's Newport driver
with `Option "NoAccel" "true"`; this is a concrete performance constraint,
not yet a measured explanation of the entire difference.

## Components to investigate

| Component | Responsibility and current evidence |
| --- | --- |
| NetBSD kernel `sys/arch/sgimips/gio/newport.c`, `newportreg.h`, `newportvar.h` | wsdisplay console, device access/mapping, display state and console drawing. The driver uses bus_space accessors and REX3/DCB FIFO waits. |
| Xorg `xf86-video-newport` in NetBSD xsrc | X rendering, shadow uploads and optional XAA acceleration. This is separate from the kernel console driver. The installed binary comes from the NetBSD release sets. |
| IRIS Newport emulation | Executes the emulated REX3 operations and produces framebuffer pixels. Its interpretation must match the register and plane formats expected by both operating systems. |
| Xiri compatibility and application behavior | Adds syscall/runtime work for original IRIX clients. Compare a native X client against the same workload in an IRIX client before assigning rendering delays to compatibility. |
| Host frontend and emulator build | Rendering mode, JIT/interpreter selection and CPU scheduling can change perceived speed. Use matching machine profiles and record the exact builds for comparisons. |

The [accelerated-color finding](results/2026-10-30-netbsd-x11.md#accelerated-color-finding)
provides a specific starting point. A solid fill expected pixel `0xfe` but
returned `0x092492`; a screen copy preserved the incorrect color, while image
upload was correct. The release Xorg driver converts color bits to physical
plane order for fast clear. The inspected IRIS implementation consumed the
COLORVRAM value directly in its pixel representation. WRMASK uses the same
conversion. This identifies a mismatch; it does not establish that NetBSD is
the side to change. Recheck it with the current IRIS integration build before
making a new driver change. Keep the qualified software path as a comparison.

## Supplied SGI manual

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

1. Reproduce solid-fill, copy, upload and composed-framebuffer checks with
   acceleration disabled and enabled on the same image and emulator build.
   Extend the existing `scripts/qualify-netbsd-x11.py --accelerated` workload
   rather than accepting an attractive screenshot as a correctness test.
2. Resolve the measured fast-clear/plane-mask mismatch against documented
   register definitions and original IRIX observations. Preserve the other
   depth/plane combinations when changing IRIS or the Xorg driver.
3. Measure native Xorg fill/copy/upload/text and window movement with host
   elapsed time and explicit X synchronization. Record CPU use and display
   configuration; use equivalent hardware/frontend settings for IRIX.
4. Restore validated accelerated operations incrementally and repeat the
   desktop interaction tests. Then profile remaining compatibility or
   frontend costs. Do not assume every delay originates in the kernel driver.

The current desktop usability cycle still takes precedence. Missing Icon
Catalog artwork has a separate measured filetype-database locking dependency.
