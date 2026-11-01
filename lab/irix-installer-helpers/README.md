# Installer helper and child-completion lab

This lab captures the original installer's embedded shell bootstrap, native
utility arguments, output pipes, exit status and process snapshots on the
[time kernel](../irix-time/baseline.json). Vendor files and package inputs use
the [installer manifests](../irix-installer/README.md). No foreign binary is
modified. All filesystem changes occur in disposable seed clones.

Run from the repository root on the host with the existing `xiri-iris`
toolbox available. The host supplies `genisoimage`; the harness launches IRIS
through the shared lab infrastructure. At most three runs need to overlap:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-helpers.py --mode ci
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-helpers.py --mode ci --native-paths
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-helpers.py --mode ordinary --native-paths
```

The baseline retains NetBSD's normal utility layout. `--native-paths` runs
[setup-native-paths.sh](setup-native-paths.sh) twice to check idempotence. It
creates explicit `/usr/bin/{ls,mkdir,mv,ln}` links to their native `/bin`
counterparts and refuses to replace other files. Controls exercise directory
creation, listing with stdout/stderr closed, rename and relative symlink
creation before the installer starts. This is a limited lab arrangement;
it does not establish general IRIX utility compatibility. In particular,
native `stat` does not implement the script's `-qd` arguments.

The original command remains:

```sh
inst -n -M -r /emul/irix -f /cdrom/dist -c /cdrom/commands
```

The command file requests `list fw_xmahjongg*` followed by `quit`. Foreign
root has `HOME=/`; UID1234 controls share `/usr/people/xiritest`. The 30-second
supervisor bounds the unresolved installer wait. `ktrace` starts inside that
supervisor, so it records the installer and its descendants rather than the
supervisor's polling loop. Each run retains:

- Full argv/environment, name, syscall, I/O and processed-signal records;
  raw `distribution.ktrace.gz` and full `distribution.kdump`.
- A process snapshot four seconds after launch, plus verification that every
  traced PID is absent after supervision. The helper creates a new session,
  so the original launch group's absence alone is insufficient.
- Native controls before/after, shared-home access, helper executable hashes,
  before/after target layout, source hashes and whole-guest shutdown.

The guest's o32 `kdump` misrenders LP64 register slots and does not recognize
`irix_o32` syscall names. [The focused decoder](../../scripts/irix-lp64-ktrace.py)
uses the pinned kernel's big-endian version-2 layout and explicit foreign
entry/return records. The qualifier cross-checks those pairs against the
independent text decoder and rejects truncated raw traces.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer-helpers.py \
  .work/irix-installer-helpers/runs/ci-baseline-2u_ono9g \
  .work/irix-installer-helpers/runs/ci-native-6aojd6p5 \
  .work/irix-installer-helpers/runs/ordinary-native-be2zjp_7 \
  --output docs/results/2026-11-01-irix-installer-helpers.json
```

Read the [result](../../docs/results/2026-11-01-irix-installer-helpers.md) for
the observed boundary and the separately identified future wait interface.
Large traces, embedded vendor script and disassemblies stay under `.work`;
only hashes and derived interface observations are committed.
