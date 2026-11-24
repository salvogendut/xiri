# IRIX CPU and memory meter checks

Build the syscall probes with the NetBSD sgimips cross tools. The executables
carry the Xiri static probe note and also run on original IRIX.

```sh
sh lab/irix-sysmp/build.sh /path/to/netbsd-tools /tmp/irix-meter
```

Run `meter-32` and `meter-n32` on each release. Each syscall row prints
the operation, selector, length, CPU number, return value and selected
32-bit words. `1431655765` is the untouched buffer sentinel. Activity
and real-memory records are 280 and 48 bytes. Page size and available
memory depend on the running machine. The last lines exercise hardware
inventory and report the main-memory record.

For a graphical run, start the SGI Freeware xosview binary as the xdm user.
In a writable directory on the authenticated NetBSD display, put the n32
probe next to the load generator and run the following. `exercise.sh`
samples an idle period, a process touching 24 MiB and using one CPU for
40 seconds, and the period following its exit. It saves the IRIX records,
NetBSD VM statistics and the xosview window pixels at each point.

```sh
cc -O2 /path/to/workload.c -o workload
window=$(xwininfo -name "xosview@$(hostname -s)" | awk '/Window id:/{print $4}')
sh /path/to/exercise.sh "$window"
```
