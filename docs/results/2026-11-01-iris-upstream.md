# IRIS upstream integration

The first upstream check under the recurring development workflow found 27 commits beyond the
previously integrated `4915ca833bee480f3a4b1009b7b691af3bd2541a`. The checked
upstream tip is `f17b4d3bc1663efd02f93a5e0e4811eebba510c8` from
[techomancer/iris](https://github.com/techomancer/iris/commit/f17b4d3bc1663efd02f93a5e0e4811eebba510c8).
The integration starts from our `43fdfaaf39457223aa7dc2df5cbd565bf3e42cbd`
and publishes merge `182efc8171f915be2152426819da8d05507c06c9` on `origin/xiri`.
Temporary branch `topic/upstream-2026-11-01` was removed after publication.

The changes include serial console sockets and shared serial wiring, Ethernet
descriptor completion and immediate gateway replies, RAD audio timing/output
fixes, complete stereo-pair drops on overflow, bounded PS/2 mouse packets,
GUI frame transfer and GL initialization, status-bar CPU accounting, and
JIT verifier controls with an equivalence regression.

## Merge review

Two files needed conflict resolution. `CHANGELOG.md` retains both the fork's
embedded-host entries and upstream's GUI GL entry. `src/host_audio.rs` retains
our frontend output factory alongside upstream's test-only detached output
constructor. Both use an optional CPAL stream; the frontend path still returns
before opening CPAL, including when its factory rejects an output.

The 40 fork-only files outside the upstream change set are unchanged. Review
of overlapping source changes confirms retention of the NetBSD keyboard
translation, diagnostic routing, bounded HAL2 loopback, firmware selection,
power-off state and frontend audio behavior. The full TLB-tag implementation
and its regression remain unchanged from the consolidated fork tip.

The [machine-readable record](2026-11-01-iris-upstream.json) binds the exact
merge, upstream commits, validation commands, results and local log hashes.
Builds use the existing Toolbox, locked offline dependencies,
Rust `nightly-2026-10-28`, two build jobs and two test threads. Outputs go to
the debug target cache, preserving the pinned release binaries.

## OpenGL runtime dependency

The new offscreen path loads EGL directly. The Fedora Toolbox had GL/GLX but
neither `libglvnd-egl` nor `mesa-libEGL`; the first workspace run therefore
finished with 2,017 passing core tests, one failed GL-context test and 26 ignored
tests. An isolated Xvfb run reproduced that failure before the packages were
installed. Both failed logs are retained and hashed in the JSON record.

Installing `libglvnd-egl-1.7.0-9.fc44` and `mesa-libEGL-26.2.5-1.fc44` in the
Toolbox resolves the missing runtime. With `LIBGL_ALWAYS_SOFTWARE=1` and an
isolated Xvfb display, the unchanged test creates an OpenGL 4.6 core context
using Mesa 26.2.5 llvmpipe (LLVM 22.1.8). The test remains enabled and actually
creates the context; it does not take its no-display early return. The
[setup instructions](../FORKS.md#iris-upstream-updates) include this dependency.

## Workspace validation

With EGL installed, the complete workspace run passes 2,116 tests with no
failures and 29 tests marked ignored by the suite. This includes 2,018 core
library tests, 91 GUI tests, three hostcall tests, one benchmark-driver test,
one monitor-readiness integration test and two documentation tests. Frontend
PCM behavior is covered within the core library suite.

```sh
LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a \
  cargo +nightly-2026-10-28 test --locked --offline --workspace -- --test-threads=2
```

The optional CPU JIT and idle-parking features also pass targeted checks with
`--features jitv2,idle-pause,gpujit`: one verifier-equivalence test across five
page shapes, and all 22 tests under `cpu::idle_park::`. The latter includes
wakeup behavior and the new retired-cycle accounting tests, which live in
separate submodules from the 15 basic state tests. The initial narrower
idle-parking run is also retained in the evidence.

## Concurrent worktree

During validation, another task created `/tmp/prismatic-step1/iris` on the
local `xiri` branch at `43fdfaaf39457223aa7dc2df5cbd565bf3e42cbd`. That
worktree was clean when inspected, and was left unchanged. The tested merge
was published with a normal fast-forward push from the topic to `origin/xiri`.
The main `../iris` checkout is clean and detached at `182efc8171f915be2152426819da8d05507c06c9`;
the topic was then deleted. The concurrent worktree's owner can advance its
local `xiri` with a fast-forward pull when ready. Inspect `git worktree list`
before selecting a checkout for the next cycle.

## Baselines and future checks

This synchronization does not change NetBSD sources or the qualified guest
kernel, emulator, disk or runtime pins. Host regression coverage does not
requalify the integrated tip for the full NetBSD/IRIX desktop workload.

The [fork workflow](../FORKS.md#iris-upstream-updates) and root `AGENTS.md` now
require upstream checks at the start of each development cycle and once per
active day during longer cycles. New upstream work is reviewed, integrated,
validated and pushed through the usual `xiri` workflow. Temporary topic
branches are removed after their merged history is published.
