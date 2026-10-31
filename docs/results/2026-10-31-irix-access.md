# Bounded IRIX access checks

The NetBSD personality now implements the standard `access` modes 0–7 for
both supported IRIX ABIs. It uses native real user/group credentials and
vnode permissions, follows the emulation-root lookup policy, and preserves
process credentials. Original xwsh can now read its locale and app-defaults;
the [application follow-up](2026-10-31-irix-winterm-access.md) clears its
previous null-font crash and reaches PTY setup.

This is a bounded interface. IRIX-specific mode extensions remain rejected,
and NetBSD's stricter root execute check remains authoritative. The
[qualification report](2026-10-31-irix-access.json) records those differences
explicitly rather than describing every return as identical to IRIX.

## Contract and reference

The original assembly probes run on the supplied IRIX 6.5.22m installation.
There are 97 variants, four ABI/dispatch combinations, and six selected
real/effective identity combinations: 1,608 original executions. The probes
capture all four IDs before and after, return registers, two record guards
and an n32 64-bit saved-register canary.

The reference clears supplementary groups using original `syssgi` operation
40 (`SETGROUPS`) before changing IDs, then checks operation 41 (`GETGROUPS`)
returns an empty list. The native parent performs the corresponding native
setup before exec. The personality gains no foreign credential setters.

| Behavior | Bounded contract |
| --- | --- |
| Standard modes | F_OK, R_OK, W_OK, X_OK and combinations; lookup and leaf permission checks use real IDs |
| Paths | Follow symlinks; preserve the 1,024-byte pathname limit before removing trailing slashes, including slashes on a regular file |
| Errors | Missing path ENOENT, search/permission denial EACCES, bad pointers EFAULT, long names IRIX ENAMETOOLONG 78, loops IRIX ELOOP 90 |
| Argument delivery | o32/n32 direct and indirect calls; two register arguments require no user-stack read |
| Namespace | A present emulation shadow remains authoritative even when it denies access; an absent shadow can fall back to the native path |
| Ownership | Duplicate credentials for the lookup, retain the caller's supplementary groups, free the copy and vnode/path references on every completion |

Three policy boundaries are explicit:

- Modes outside 0–7 return EINVAL before pathname access. The reference
  accepts additional bits, including 8 and 16; their complete semantics are
  outside this first implementation. The fixture names `mode-*` describe
  measurements, not an assumption that every such mode is invalid on IRIX.
- Native root X_OK requires at least one executable file-mode bit. The
  supplied IRIX accepts the tested root checks without one. The adapter does
  not bypass native vnode authorization to reproduce that behavior.
- The unreadable `/emul/irix` shadow deliberately differs from the readable
  native/reference file. Its EACCES result verifies native namespace policy.

The empty supplementary-group matrix does not qualify general group lists,
ACLs, capability behavior or every filesystem type. Native write checks are
retained; no mount-policy or authorization bypass is introduced.

## Qualification

| Kernel and execution | Access records | Identical to oracle | Explicit policy differences | Native/vendor controls |
| --- | ---: | ---: | ---: | ---: |
| LP64, CI | 1,608 | 1,468 | 140 | 12 |
| LP64, ordinary | 1,608 | 1,468 | 140 | 12 |
| o32 kernel, CI | 804 | 734 | 70 | 8 |
| Total | 4,020 | 3,670 | 350 | 32 |

All 4,020 records pass the bounded contract, including unchanged credentials,
guards and return registers. The 350 differences comprise 180 extension-mode
returns, 160 native root-execute denials and 10 emulation-shadow denials.
The full 360 extension-mode cases are retained in the report; half already
return the same EINVAL as the oracle. All 32 controls pass, and the original
reference plus all three NetBSD guests halt cleanly.

The [lab](../../lab/irix-access/README.md) supplies original probes, setup,
pinned builds, reference records, the guest observer and a separate
qualifier. Observation can run concurrently with the oracle using
`--observe-only`; such captures remain explicitly uncompared until the
qualifier checks every complete record against the reference and the bounded
contract. Accepted captures and reference export are reproducible with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-access.py \
  .work/irix-access/runs/lp64-ci-_cj_1eb3 \
  .work/irix-access/runs/lp64-ordinary-siuj24se \
  .work/irix-access/runs/o32-ci-5z5c3h0o \
  --reference .work/irix-reference/access-runs/ci-1pqgklta \
  --export-reference lab/irix-access/reference.json \
  --output docs/results/2026-10-31-irix-access.json
```

Source branch: `xiri/irix-access` in the authorized NetBSD fork, based on the
qualified ELF-map relocation branch, at `0d031580e42d0cd2f1e1851254326366569dc178`.
Exact source revisions, configurations,
emulator hashes and boot/native/debug kernel hashes are in
[LP64](../../lab/irix-access/baseline.json) and
[o32](../../lab/irix-access/o32-baseline.json) pins. Builds were sequential,
with two compiler jobs each.

## Diagnostic attempts retained

The first reference batch completed its probes but exceeded IRIX's argument
limit when archiving all records with a glob. An interactive `exit` then
logged out the console, causing the host to wait for a missing completion
marker. The corrected harness uses small tar argument lists inside a script.
Reference disks use in-memory overlays: the stopped raw file cannot recover
those guest writes. That attempt and an abandoned raw-disk recovery are not
qualification evidence.

The first successfully transferred oracle exposed a supplementary-group
setup mismatch: the original process retained the root account's group,
whereas the native runner cleared its list. The finalized probes clear and
verify the reference list, and the complete comparison is repeated with
matching artifacts. Earlier unnormalized captures remain private diagnostics.

The initial kernel candidate also omitted the dispatcher allowlist entry;
that was fixed before the accepted kernel captures. The application report
retains its excluded startup and native-font control attempts separately.

Original media, runtime bytes, guest disks, raw logs and screenshots stay in
ignored `.work`. Public files contain original test sources, records and
metadata. No leaked IRIX source was used.
