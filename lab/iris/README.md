# IRIS build baseline

The managed source checkout, Rust toolchain, Cargo cache, build outputs, and
full build log live under the ignored `.work/` directory. The checked-in
[Cargo.lock](Cargo.lock) fixes the dependency resolution because upstream does
not commit one. The source revision and toolchain date are fixed in
[`scripts/build-iris.sh`](../../scripts/build-iris.sh).

On Fedora 44 Silverblue, run these commands from the Xiri repository root to
prepare the same Toolbox environment:

```sh
toolbox -y create --release 44 xiri-iris
toolbox run -c xiri-iris sudo dnf install -y rustup pkgconf-pkg-config alsa-lib-devel gcc gcc-c++ make clang
toolbox run -c xiri-iris env RUSTUP_HOME="$PWD/.work/rustup" CARGO_HOME="$PWD/.work/cargo" rustup-init -y --no-modify-path --profile minimal --default-toolchain nightly-2026-10-28
./scripts/build-iris.sh
```

Emulator changes live in the [IRIS fork](https://github.com/salvogendut/iris/tree/xiri/netbsd-snapshots),
on branch `xiri/netbsd-snapshots`. It starts at the previously tested upstream revision
`b188bb9a82842948ddf2534f07d718df8473942c`; commit
`d6420795a00f139cd0f638a623c55a071b46e9e9` adds NFS MOUNT authentication
negotiation for NetBSD. Commit
`b6d6f5c295aaccdb0bb614ee140447625a476498` additionally republishes the saved
RAM bank map during snapshot restore; see the [snapshot record](../../docs/results/2026-10-30-netbsd-snapshots.md).
Keep emulator implementation and regression tests in
that repository, and guest configurations and qualification evidence here.
Upgrading the branch to newer upstream changes requires another qualification run.

The build script clones the fork if needed, checks out the fixed revision, copies
the lockfile into the checkout, and builds `iris` and `iris-ci` with Cargo's
default features. It deliberately leaves `lightning`, `opcodefusion`, and
`jitv2` disabled for the initial debugging baseline. Its binaries are written
to `.work/target/release/`.

To build from the sibling development checkout at the pinned commit instead:

```sh
IRIS_SOURCE_DIR=../iris ./scripts/build-iris.sh
```

The override checks the revision and leaves the checkout on its current branch.
It still installs Xiri's dependency lockfile and writes binaries under Xiri's
`.work/target/release/`. Record and test any uncommitted emulator changes before
updating the pinned revision.

The first build's observed versions and output hashes are in the
[2026-10-29 build record](../../docs/results/2026-10-29-iris-build.md). A
successful CLI build does not qualify NetBSD boot or emulator device behavior.
