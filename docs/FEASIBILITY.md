# Xiri feasibility and platform choice

Research dates: 2026-10-14; emulator development assessment updated 2026-10-15.

The agreed Xiri target is NetBSD plus an IRIX personality and the existing IRIX desktop, running on real SGI machines. Recreating the whole IRIX kernel would add substantial work without removing the need for hardware drivers, application ports, or graphics compatibility.

Preserving the original desktop makes this a systems compatibility project as well as an OS distribution project. Its feasibility must be tested early.

## Comparison of approaches

| Approach | Main benefit | Main limitation for Xiri | Proposed role |
| --- | --- | --- | --- |
| Extend original IRIX with new packages | Retains the original desktop, applications, and graphics drivers | Leaves the kernel and platform interfaces unchanged; software ports still need maintenance | Reference environment and possible interim use |
| Emulate a complete SGI workstation | Runs original IRIX for reference and NetBSD/Xiri for development on a modern host | Emulating original IRIX alone does not modernize it; hardware still needs qualification | Initial implementation and regression environment, plus reference testing |
| Reimplement IRIX as a complete OS | Potential control over every interface | Requires kernel, drivers, userland, desktop, and continuing maintenance | Outside the initial scope |
| Maintained kernel with IRIX compatibility | Reuses networking, VM, storage, and native software infrastructure | Requires SGI drivers and precise compatibility for chosen programs | Preferred direction |

Emulation and compatibility operate at different boundaries. A hardware emulator implements the machine that IRIX expects. A personality implements the OS interfaces that an IRIX program expects. On a compatible SGI CPU, that program's ordinary instructions can execute directly; its system calls and other OS interactions still need translation.

Hardware reverse engineering remains necessary where drivers are missing. The advantage is that Xiri can target the interfaces needed by its own drivers instead of reproducing every device behavior exercised by the original IRIX kernel.

## Existing work

NetBSD previously implemented `COMPAT_IRIX`, but retired it in NetBSD 6.0. Historical source includes probes for both o32 and n32 executables. This is useful reference code, not an available modern compatibility feature or proof that the desktop will work. [NetBSD 6.0 release notes](https://www.netbsd.org/releases/formal-6/NetBSD-6.0.html), [historical ELF loader](https://github.com/NetBSD/src/blob/netbsd-5/sys/compat/irix/irix_exec_elf32.c).

The current NetBSD SGI port page lists Indy, some Indigo2 configurations, and O2 among its supported machines. It lists Octane and R10000 Power Indigo2 as unsupported; Fuel is absent from its supported model list. Its old explanation mentioning a required mips64 toolchain should not be read as a current diagnosis: NetBSD 6.0 already introduced broader 64-bit MIPS support. Board support requires a fresh source and boot audit. [NetBSD SGI port](https://wiki.netbsd.org/ports/sgimips/), [NetBSD 6.0 MIPS changes](https://www.netbsd.org/releases/formal-6/NetBSD-6.0.html).

OpenBSD historically supported Octane and Fuel, but discontinued its SGI port after 6.9. That code provides a significant hardware reference. The published `impact` and `odyssey` manuals establish console support, not an IRIX-equivalent accelerated desktop. [OpenBSD SGI port](https://www.openbsd.org/sgi.html), [Impact driver](https://man.openbsd.org/OpenBSD-6.9/sgi/impact.4), [VPro driver](https://man.openbsd.org/OpenBSD-6.9/sgi/odyssey.4).

Linux currently has an upstream `SGI_IP30` configuration for Octane and Octane2. Its implementation is a hardware reference for the NetBSD port; a kernel configuration entry does not establish complete graphics support or a ready-to-install distribution. [Linux MIPS configuration](https://github.com/torvalds/linux/blob/master/arch/mips/Kconfig).

MAME contains an Indy/Indigo2 implementation with IRIX boot instructions. Its Octane implementation is explicitly a nonworking skeleton, including a placeholder CPU. Octane emulation is therefore unfinished in that implementation, rather than fundamentally impossible. This finding does not establish the status of every emulator. [Indy and Indigo2 implementation](https://github.com/mamedev/mame/blob/master/src/mame/sgi/indy_indigo2.cpp), [Octane implementation](https://github.com/mamedev/mame/blob/master/src/mame/sgi/octane.cpp).

SGUG RSE already provides a package environment and development tools for IRIX. Its work is relevant to toolchain bootstrapping and application ports, though it does not supply a replacement kernel. [SGUG RSE](https://github.com/sgidevnet/sgug-rse).

### IRIS emulator

[techomancer/iris](https://github.com/techomancer/iris) is an additional hardware and testing reference. Its README reports IRIX 5.3 and 6.5 operation, an Indy IP24 desktop, and Indigo2 IP22/IP28 emulation, including an R10000/IP28 desktop. These are upstream results; Xiri has not yet reproduced them. Reference revision: [21c0ecb024b3](https://github.com/techomancer/iris/tree/21c0ecb024b3a7dc9e11514fa1b5302363071bf6), inspected on 2026-10-14. [IRIS README at that revision](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/README.md).

Useful starting points for Xiri:

- [REX3 graphics notes](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/docs/rex3.md): register and drawing behavior to compare with drivers and physical hardware.
- [Testing guide](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/TESTING.md) and [CPU test suite](https://github.com/techomancer/iris/tree/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/cpu-tests): candidate methods for repeatable execution and hardware comparison.
- [Hardware documentation index](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/README.md#documentation): machine profiles, interrupts, SCSI, and audio references.

Initial implementation and testing will use Indy emulation. IRIS is the preferred development harness because its documented control socket, serial capture, network services, overlays and snapshots fit repeated kernel and ABI experiments. MAME supplies an independent implementation and fallback. This is a workflow recommendation, not a measured speed or correctness result. IRIS's README notes that NetBSD guests are not regularly tested, so current NetBSD boot and I/O must be qualified first. Hardware behavior inferred from emulation must later be checked on the available SGI machines.

The [emulation assessment](EMULATION.md) compares both tools, pins inspected sources, records the missing images and host prerequisites, and defines the initial acceptance tests. It also identifies two important IRIS configuration constraints: packaged `lightning` builds disable debugging, and explicit `--headless` disables Newport graphics. No emulator boot has been demonstrated by Xiri.

## Platform choice

NetBSD was selected as the underlying OS on 2026-10-14. Development starts on an emulated Indy, followed by physical qualification. The following hardware order is based on the available machines and published support, pending actual boot tests.

| Machine | Proposed investigation | Decision condition |
| --- | --- | --- |
| Indy | First NetBSD platform, preferably a configuration with supported Newport graphics | Confirm CPU, graphics board, stable networking, storage, and usable display |
| Indigo2 | Second platform if its CPU and graphics match existing support | R4x00, R8000, and R10000 machines must be treated separately |
| Octane | Port the required board and device support to NetBSD | Use historical OpenBSD and current Linux as references; validate I/O and display on the available machine |
| Fuel | Later research target | Requires access to hardware and a dedicated port assessment |

The target is one NetBSD foundation across the supported machines. Its advantages are a common compatibility implementation and one maintained OS base. The cost is additional board support, especially for Octane. Linux as a replacement foundation and revival of the retired OpenBSD SGI port were considered alternatives; they are outside the agreed implementation plan.

## Preserving the desktop

The preservation target includes window management, Toolchest, file and desktop icons, desks, application launching, and saved preferences. SGI's desktop guide documents these as interacting parts of the environment. The initial implementation strategy is to run the original programs through compatibility and adapt the services they depend on. [SGI Desktop User's Guide](https://tech-pubs.net/SGI_EndUser/books/Desktop_UG/sgi_html/ch13.html).

A working `4Dwm` window is only an early milestone. Required X extensions, shared libraries, file notification, session management, and system administration operations need individual investigation. SGI's package inventory separately identifies desktop libraries, file alteration monitoring, and desktop services. Dependencies must be established for the actual installed IRIX release. [SGI software subsystem inventory](https://tech-pubs.net/SGI_Admin/books/ChallS_OG/sgi_html/ch07.html).

If an original component proves impractical to retain, a compatible replacement can be proposed with an explicit account of the lost behavior. Such a replacement would change the preservation strategy; it should not silently redefine completion.

## Graphics and modern software

Graphics is the largest technical uncertainty. Console output, a usable X server, accelerated 2D, OpenGL, and older IRIS GL are distinct capabilities. Reusing an original desktop program does not make the original IRIX kernel graphics driver usable under a different kernel.

The proposed first target is a usable 2D desktop. Hardware 3D acceleration should follow a separately scoped investigation of one graphics family. Software rendering can establish correctness for selected programs, but its performance must be measured on the real machines.

A maintained OS improves the basis for modern software; it does not guarantee a current browser build. The exact CPU instruction set, endianness, compiler and runtime support, memory, and rendering costs still matter. For example, Rust's published NetBSD target list includes a little-endian MIPS target requiring MIPS32, which does not establish support for these older big-endian SGI CPUs. [Rust NetBSD platform documentation](https://doc.rust-lang.org/rustc/platform-support/netbsd.html).

Native maintained command-line tools and modest graphical applications are sensible early targets. A current full browser remains an independent feasibility item. A browser running on a modern companion machine and displayed on the SGI is a practical optional bridge; it would not count as native browser support.

## Scope and effort

A prototype on one machine with selected binaries is a bounded feasibility project. A reliable desktop across three machine families, with broad legacy compatibility and acceleration, is a much larger continuing effort. Calendar estimates should follow the first boot, desktop dependency, and ABI experiments.

First establish the emulated NetBSD development loop, then determine whether the original desktop can be separated from enough IRIX-specific kernel and display behavior to coexist with a maintained host. The desktop experiment needs an original IRIX installation, which is not yet available locally. Answer that feasibility question before investing in a full Octane or Fuel port; physical Indy inventory can proceed alongside the emulated work.
