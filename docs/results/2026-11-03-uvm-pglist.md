# Contiguous allocation below a RAM segment

The first graphical xdm CHD check stopped in the native NetBSD kernel while
creating a process during the first IRIX desktop login. The image was not
promoted. The [fault record](2026-11-03-xiri-xdm-kernel-fault.json) preserves
the input pins, kernel message ring, error and unclean shutdown status.
Its source CHD is unchanged; the faulted emulator was stopped after capture.

## Diagnosis

Run `.work/irix-xdm/runs/ordinary-47ikvfc8` booted the CHD through graphical
PROM AutoLoad, reached xdm, verified the installed payload and rejected an
incorrect password. During the first valid login, a native `sh` trapped at
`uvm_pglistalloc_contig_aggressive`, EPC `0xffffffff882c978c`, reading
`pg->flags` through a null page pointer (virtual address `0x14`).

The monitor captured the trapframe at `0x980000000943b970` and the physical
segment table at `0xffffffff8866f730`. The matching `netbsd.gdb` resolves the
saved caller to `cpu_uarea_alloc`, followed by pool allocation frames. It
requested two 8 KiB pages aligned to 16 KiB for a process's kernel area.
The selected segment begins at page `0x4609`, physical address `0x8c12000`.
Rounding its first page down produces `0x8c10000`, which has no `vm_page`.
The valid aligned lower bound is `0x8c14000`.

The allocator calculates this lower bound but previously checked it only
while searching backward. When the rounded-down candidate is already below
the bound, the backward search is skipped and the forward search dereferences
the missing page. The added check discards that candidate: no aligned run
containing the newly allocated page can satisfy the lower bound.

This is native UVM code, shared by native and IRIX processes. The failure
followed a full imported-file hash scan and desktop startup; memory pressure
is a plausible trigger for the aggressive allocator, but was not separately
measured. This result does not establish the cause of older intermittent
faults.

The upstream [PR 56074 fix](https://mail-index.netbsd.org/netbsd-bugs/2021/03/26/msg071106.html)
addresses the upper end of the same allocator's search and is already present
in this source. The observed fault requires the additional lower-bound check.

## Fix and verification

NetBSD `xiri` commit `9390bc04900a0d04796d494aca5b00651f12954d` adds the check
in `sys/uvm/uvm_pglist.c` and is pushed to `origin/xiri`. No personality ABI or IRIS changes are involved.
The previous detached module build and all selected image artifacts remain
preserved. The replacement kernel and module are built from the integration
checkout into `.work/netbsd-xdm-build`, using two build jobs.

The [regression record](2026-11-03-uvm-pglist-test.json) records source hashes
and both exit statuses. `scripts/test-uvm-pglist.py` extracts the actual allocator function from the
fork and compiles it with a synthetic physical-page provider. The first case
uses the captured segment boundary. The old source fails on the exact
`0x8c10000` lookup. The fixed source passes **195,841 cases** spanning segment
starts/ends, allocation lengths, alignment, lower/upper address limits and
DMA boundaries. The harness checks both returned ranges and impossible
requests. It does not simulate page-daemon concurrency.

```sh
python3 scripts/test-uvm-pglist.py
```

Fixed source SHA256:
`47f62159d99df61870b39a071af57a781493553f6a0c8415610cae0bc4489c39`.
The rebuilt module passed its [guest lifecycle checks](2026-11-03-xiri-xdm-module-lifecycle.json):
absence, load, busy-process unload refusal, idle unload, reload and automatic
boot loading, with native controls and a clean halt. A second
[guest replay](2026-11-03-xiri-xdm-module-regressions.json) passed 168 signal,
process-sharing and receive-message observations plus four native controls,
then halted cleanly. The
[xdm image record](2026-11-03-xiri-xdm-image.md) records subsequent guest
checks and whether the replacement was promoted.
