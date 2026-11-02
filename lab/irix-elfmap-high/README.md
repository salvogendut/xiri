# High preferred library addresses

This lab extends the original relocation fixtures with the address ranges
used by imported freeware libraries. Vendor binaries remain private inputs;
the generated mapping fixtures and assembly probe are original Xiri code.

Build `XIRI_IRIX_ELFMAP_HIGH` and `XIRI_IRIX_ELFMAP_HIGH_O32` using
`scripts/build-netbsd-kernel.sh`, the NetBSD `xiri` checkout and separate
`.work/netbsd-irix-elfmap-high{,-o32}-build` directories. Use architecture
`mips64eb`/`mipseb` respectively and at most two build jobs; build sequentially.
The baseline JSON files pin clean source and exact binaries. Keep earlier
builds and images for reproduction.

```
python3 scripts/build-irix-elfmap-high.py
python3 scripts/probe-irix-reference-elfmap-relocation.py --checkpoint elfmap-high
python3 scripts/probe-irix-elfmap-high.py
python3 scripts/probe-irix-elfmap-high.py --mode ordinary
python3 scripts/probe-irix-elfmap-high.py --kernel-abi o32
python3 scripts/qualify-irix-elfmap-high.py LP64_CI LP64_ORDINARY O32_CI \
  --reference IRIX_RUN --output RESULT.json
```

The native harness uses the immutable icons seed, verifies its raw digest,
copies it before booting, validates fixture hashes and runs native/vendor
controls before and after the matrix. At most four emulator guests may run
together. Each harness shuts down only its own guest.

See the [qualification and application follow-up](../../docs/results/2026-11-02-irix-elfmap-high.md)
for the explicit original-IRIX differences, GIMP's next signal boundary,
catalog shell failure and shell starting-directory correction.
