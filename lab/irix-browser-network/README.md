# IRIX socket error probe

Build on the host with the NetBSD MIPS64 tools. The script writes one
freestanding executable for each vendor ABI.

```sh
lab/irix-browser-network/build-probes.sh .work/netbsd-octane-build/tools .work/socket-error-probes
```

Copy `so-o32` and `so-n32` to an executable directory in the guest. Run each
under an ordinary account, with TCP port 40849 unused on the guest loopback
interface. Each executable writes sixteen big-endian 32-bit words. On IRIX
or NetBSD/sgimips, inspect them with the following command.

```sh
./so-o32 > o32.out && od -An -td4 o32.out
./so-n32 > n32.out && od -An -td4 n32.out
```

Both programs produced the following values on original IRIX 6.5.22f and
both updated Xiri Indys.

```text
0 0 4 0
-150 1 0 146
0 0 0 16777215
1 -14 -9 0
```

The first line checks a new socket and enables nonblocking mode. The second
records the connect, readiness and pending refusal. The third reads the error
again, then requests one byte in a four-byte word initialized to all ones. The
fourth records the one-byte length and the return values for a null length
pointer, invalid descriptor and null value pointer. A recorded negative
value represents an IRIX errno.

[Browser diagnosis and image qualification](../../docs/results/2026-11-25-mozilla-http.md).
