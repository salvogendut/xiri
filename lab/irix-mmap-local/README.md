# Private fixed/local mappings for original GL

Original n32 `libGL.so`, loaded by 4Dwm, asks for
`mmap(0, 4096, 3, 0x92, 3, 0)` on the 8 KiB-page LP64 kernel. The descriptor is
`/dev/zero`. IRIX flags 0x92 mean PRIVATE | FIXED | LOCAL. GL then writes its
dispatch data at 0x1050, within the native rounded page. This is an actual
original-library call captured through the native tracer in the
[4Dwm lab](../irix-4dwm/README.md), not a guessed request.

The adapter accepts PRIVATE with optional FIXED and LOCAL, explicitly converts
the fixed flag, checks the foreign address range and delegates mapping,
permissions, protection and replacement to native mmap. LOCAL is valid only
with one LWP and an unshared vmspace; share-group creation remains unsupported.
Foreign 0x1000 is ANYADDR, not native MAP_ANON. Other flags are rejected.

The IRIX ELF probe gives validated foreign executables a zero minimum virtual
address. This permits GL's dispatch page while keeping native exec's usual
page-zero guard and the global `vm.user_va0_disable` setting. Native controls
check that guard directly and after replacing an o32/n32 IRIX image with a
native executable. No original executable or library is patched.

## Inputs and checks

The 33 original fixtures run through direct and indirect syscall dispatch in
o32 and n32, under root and UID1234. The original IRIX reference supplies 264
records. Native runs cover both ABIs on LP64 and o32 on the 32-bit kernel.
Records contain all request fields, returns, effective/real identities, active
payload checks and protection-fault evidence. All returned bytes are compared.

Successful cases read the entire rounded mapping, test writes, and unmap it.
Replacement tests verify a neighboring mapping survives and an invalid file
descriptor preserves the original bytes. A private regular-file write must
leave the backing file unchanged. A read-only mapping rejects a deliberate
store. Other cases test file modes, descriptor lifetime, length/range errors,
page alignment, file offsets and unsupported flags.

Native policy differences are explicit: 8 KiB alignment on LP64, EINVAL for
unsupported flags/bad protection/empty mappings, and ENOMEM for a wrapping
fixed range. Native o32 and original IRIX use 4 KiB pages. Non-fixed placement
is normalized only after checking actual alignment and payload results.
Native /dev/zero also permits a write-only descriptor: its vnode mapper supplies
anonymous memory before the regular-file read-mode check; original IRIX returns
EACCES. This native special case is retained and recorded separately.
Only signed 32-bit file offsets and unshared address spaces are covered.

## Reproduce

Build kernels sequentially with at most two jobs, using the matching config,
architecture and isolated output paths in the pin files. Build fixtures with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-mmap-local.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-mmap-exec.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-mmap-local.py
```

Run `scripts/probe-irix-mmap-local.py --seed-directory
.work/irix-x11-fonts/runs/ci-_6m3l41w` in CI mode, with `--mode ordinary`, and
with `--kernel-abi o32`. The seed must be the stopped, qualified font/locale
guest. Each probe clones it, verifies inputs, brackets the fixture matrix with
native/vendor and cleanup controls, and shuts down its own guest.

`qualify-irix-mmap-local.py --reference REFERENCE RUN... --output REPORT`
independently compares every record and checks pins, control results and clean
shutdowns. `--export-reference` writes the decoded original observations for
the initial qualification. Raw media, binaries, guest traces and disassembly
stay in ignored `.work`.

The first flag-only implementation was insufficient: native exec's default
minimum address rejected page zero. Its diagnostic runs are retained privately
and excluded from the final matrix. The corrected kernels also adjust the
validated IRIX process layout and verify native exec restores its normal guard.

The [accepted report](../../docs/results/2026-11-01-irix-mmap-local.md) records
660 mapping cases, 30 controls and 32 native page-zero controls. The separate
`probe-irix-mmap-shell.py` / `qualify-irix-mmap-shell.py` pair reruns the original
three-application shell acceptance checks on this kernel without changing the
previous checkpoint's harness or pins.
