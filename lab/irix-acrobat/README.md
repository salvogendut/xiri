# Original Acrobat Reader resources

`scripts/stage-irix-acrobat.py` reads the supplied IRIX 6.5.22m installation
without mounting it writable. It stages the complete `/usr/adobe/Acrobat4.0`
tree plus dependencies missing from the existing desktop/GIMP import.
The resulting archive stays under ignored `.work/irix-acrobat-resources/`;
original application binaries and fonts are not committed to this repository.

The ledger records each source and destination, hash, type and applied mode.
Files retain their original bytes. ELF files use the existing 0555 import
policy, data 0644 and directories 0755; the import adds no setuid mode.
Resource presence alone is not an application qualification.

`build-irix-acrobat-probes.py` extends the retained exec-alignment and ELF-map
fixtures with the measured MIPS-I/4 KiB layouts. It produces 87 executable
cases (174 root/UID 1234 executions) and 85 mapping cases (340 o32/n32,
root/UID 1234 executions). The archive includes two native runner sources and
`loaders.sh`/`mapping.sh`. The exec runner confines its child to a private
fixture root, so interpreter-negative cases never replace the guest's libc.

```sh
python3 scripts/build-irix-acrobat-probes.py
```

On a disposable native guest, extract `probes.tgz` into
`/tmp/xiri-acrobat-tests`, compile both runners with
`cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=10000`, and run the two
scripts there. Retain their completion markers and archive all `loader-*.log`
and `map-*.log` files. The scripts check that mapping leaves each backing file
unchanged. The [reference](reference.json) contains 44 original-IRIX results
for the eleven new library cases, using the same fixture bytes.

```sh
python3 scripts/qualify-irix-acrobat-probes.py --archive RESULTS.tgz \
  --run HALTED_GUEST --output REPORT.json
```

The qualifier requires exact captured output/status, process-group cleanup,
the old contracts and the new reference fields. Collision-placement addresses
follow the existing bounded native policy; all other new record fields match.
`--diagnostic` permits inspection before shutdown without claiming a final pass.
These fixtures qualify layout admission, executable text, initialized data,
zero/writable BSS, protection faults, repeat calls, collisions and unchanged
input bytes. They do not qualify every ELF feature or arbitrary Adobe plug-ins.

The [application report](../../docs/results/2026-11-04-irix-acrobat.md) records
the final matrix and original Reader's PDF/page/zoom/reopen/exit checks.
Applications / acroread also launches after xdm login. Its catalog icon does
not change while the wrapper's Reader process runs; this remains a separate
FAM feedback follow-up. The session exports the vendor-supported
`ACRO_CONFIG=mipsirix`, and native `/usr/adobe` points at the imported tree
only when that prefix is unused. No vendor launcher or ELF bytes are patched.
