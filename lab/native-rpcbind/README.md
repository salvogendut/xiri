# Native RPC discovery for the desktop

The development launcher runs NetBSD `rpcbind -d -h 127.0.0.1` and native
FAM v1. This rpcbind version automatically appends loopback when `-h` is
specified, including when that exact address is already in the explicit
list. Its second TCP and UDP binds then report `Address already in use`.
The first bindings and FAM registration still succeed.

The NetBSD `xiri` change avoids appending a loopback literal already present
in the explicit list. It preserves automatic loopback insertion for other
addresses and the no-`-h` wildcard behavior. It does not change the launcher
to listen on every interface or suppress binding errors generally. Resolving
hostname aliases and duplicate user-supplied `-h` arguments is outside this
small change.

Build with the existing pinned native FAM sysroot and cross compiler:

```sh
python3 scripts/build-native-fam.py
python3 scripts/build-native-rpcbind.py
```

The second command writes `.work/native-rpcbind/rpcbind`, its compiler and
source hashes, command line, build log and `result.json`. The desktop
usability probe installs this native binary at `/usr/sbin/rpcbind`, verifies
loopback-only IPv4 listeners, discovers FAM program 391002 version 1, checks
startup logs and confirms service cleanup after logout. No kernel rebuild
is required for this utility change.
