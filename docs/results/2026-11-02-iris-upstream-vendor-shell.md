# IRIS upstream check during original-shell support

Fetched `https://github.com/techomancer/iris.git` at the start of this cycle.
Nine commits advance upstream from `3cba53a` to
`4c1c87f5161c13b323d9b5d57a93779d355729b5`. They cover test synchronization,
SCSI SYNCHRONIZE CACHE(16), write-cache/FUA durability, periodic disk flushes,
storage logging/configuration and durable CHD writes.

Reviewed the storage, SCSI, configuration and CHD changes and their tests.
The merge had no conflicts. IRIS `xiri` now includes upstream through merge
`f38cfa1c5e62def9fbefa5244e07adf285f02d3b`, committed and pushed from
`.work/iris-upstream-sproc`. The shared performance checkout was preserved.

Validation uses the existing nightly 2026-10-28 toolchain, locked offline
dependencies, two Cargo jobs, an isolated Xvfb display and software GL:

| Suite | Passed | Ignored | Failed |
| --- | ---: | ---: | ---: |
| Workspace | 2,618 | 36 | 0 |
| JIT/idle library | 2,956 | 35 | 0 |

Nested subprocess test summaries are excluded from these totals. Raw logs
are `.work/irix-vendor-shell/iris-workspace.log` and `iris-jit-idle.log`.
Qualified guest emulator binaries remain at their recorded revisions; these
host regression checks do not promote a new runtime binary or disk image.
