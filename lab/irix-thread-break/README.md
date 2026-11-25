# Heap resizing with an n32 pthread worker

This freestanding IRIX executable targets the 8 KiB page size of the two
qualified Indy kernels. It uses the real `nsproc` worker startup and an
ordinary private mapping of `/dev/zero`. No vendor SDK or library is needed
to build the fixture. From the project root, with the NetBSD cross tools on
`PATH`, run

```sh
for name in heap heaplimit; do
    opt=
    [ "$name" = heap ] || opt=-DLIMIT_ONLY
    mips64--netbsd-gcc -std=c11 -O2 -Wall -Wextra -Werror -EB \
        -march=mips3 -mabi=n32 -mno-abicalls -fno-pic -G0 \
        -ffreestanding -fno-stack-protector $opt \
        -c lab/irix-thread-break/probe.c -o "$name.o"
    mips64--netbsd-ld -EB -m elf32btsmipn32 --build-id=none \
        -z max-page-size=8192 -T lab/irix-prda/probe.ld \
        -o "$name" "$name.o"
done
```

Run `./heap` as an ordinary user in the guest. Before creating the worker,
the probe checks single-thread growth and shrink and reserves an occupied
page 8 MiB above the initial break. The parent and worker take turns resizing
the heap, including two byte-granularity requests. A rejected request must
preserve data on both sides. On shrink and regrowth, discarded pages must
read as zero and retained pages must keep their contents. The probe also
checks the lower bound for a threaded shrink and the user address ceiling.

The exit status identifies the failed check.

| Status | Check |
| --- | --- |
| 1–3 | Guard mapping, single-thread resize, worker creation |
| 4–5 | Parent and worker resize and exchange of data |
| 6 | The 5 MiB growth succeeded and its last word was writable |
| 7 | Growth into the occupied guard |
| 8–9 | Surviving markers, shrink and zero fill on regrowth |
| 10 | Lower bound, address ceiling and original markers |
| 11 | The limit case returned an error other than ENOMEM |

The limit variant requests 5 MiB of additional heap below the guard. Invoke
it in separate subshells with a data limit and an address-space limit. The
address-space limit must include the kernel's existing stack reservation and
leave room for small successful resizes before the measured rejection.

On both tested Indys these commands allow setup and enforce the requested
limit. Each invocation must exit zero.

```sh
(ulimit -d 4096 && ./heaplimit)
(ulimit -v 126976 && ./heaplimit)
```

The second command permits 124 MiB of total address space. As a positive
control, raising it to 128 MiB lets the 5 MiB request succeed, which the
limit fixture reports with exit status 6. An unrestricted `./heap` should
always exit zero.
