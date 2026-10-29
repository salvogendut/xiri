# IRIS build baseline

The source checkout, Rust toolchain, Cargo cache, build outputs, and full build
log live under the ignored `.work/` directory. The checked-in
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

The build script clones IRIS if needed, checks out the fixed revision, copies
the lockfile into the checkout, and builds `iris` and `iris-ci` with Cargo's
default features. It deliberately leaves `lightning`, `opcodefusion`, and
`jitv2` disabled for the initial debugging baseline. Its binaries are written
to `.work/target/release/`.

The first build's observed versions and output hashes are in the
[2026-10-29 build record](../../docs/results/2026-10-29-iris-build.md). A
successful CLI build does not qualify NetBSD boot or emulator device behavior.
