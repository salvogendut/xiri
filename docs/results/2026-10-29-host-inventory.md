# Candidate build host inventory — 2026-10-29

This is the first Milestone 0 environment check. The machine was inspected from
the Xiri working tree; it has not yet been selected or qualified as the build
host. No emulator or guest was run.

## Environment

| Item | Observed value |
| --- | --- |
| Host | `minisforum.golgota.lan` |
| OS | Fedora Linux 44 Silverblue (`44.20261002.0`) |
| Kernel | `7.2.8-200.fc44.x86_64` |
| Architecture | x86-64 |
| Logical CPUs | 16 |
| RAM | 61 GiB total, about 43 GiB available at inspection |
| Swap | 8 GiB |
| Workspace storage | 1.9 TiB filesystem, about 536 GiB available |
| `/tmp` | 31 GiB tmpfs, about 31 GiB available |
| Repository | `main`, clean working tree before this record |

`git`, `curl`, `wget`, `cc`, `gcc`, `cmake`, `make`, `python3`, `toolbox`, and
`podman` were found on
`PATH`. `rustc`, `cargo`, `iris`, `mame`, and `qemu-system-mips64` were not found
on `PATH`. IRIS was also not present as a repository file.

## Procedure

Run from the repository root:

```sh
uname -a
cat /etc/os-release
nproc
free -h
df -h . /tmp
for x in git curl wget cc gcc clang cmake make python3 toolbox podman rustc cargo iris mame qemu-system-mips64; do command -v "$x" || true; done
git status --short --branch
```

## Interpretation

The measured storage and RAM exceed the planning allowance in
[the emulation plan](../EMULATION.md#inspected-session-environment). This does
not establish that the IRIS build dependencies are installed or that the host
can boot NetBSD in an emulator. The next check is to provision a pinned IRIS
source build and verify its build prerequisites on this Fedora host.
