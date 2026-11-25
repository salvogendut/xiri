# Browsing public HTTP sites with IRIX Mozilla on the Indy

Both SGI browsers opened FrogFind and the World Wide Web project page at CERN as
`xiritest`. The addresses used plain HTTP. Each browser submitted a NetBSD search and displayed the results heading. The
6.5.30f browser also showed clickable NetBSD results. Modern HTTPS, certificate
validation and JavaScript-heavy sites were outside this check.
[6.5.22f screenshot](2026-11-25-mozilla-http-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-25-mozilla-http-6.5.30f.png).

## Try it

From the Xiri checkout, start the bundle for the release you want.

| Vendor release | Machine and browser | Launcher |
| --- | --- | --- |
| 6.5.22f | Indy R4400, Mozilla 1.0.1 | `.work/images/xiri-indy-6.5.22f-mozilla-http-20261125/run-iris.sh` |
| 6.5.30f | Indy R5000, Mozilla 1.7.12 | `.work/images/xiri-indy-6.5.30f-mozilla-http-20261125/run-iris.sh` |

Log in at xdm using `xiritest` for the username and password. Double-click
**Mozilla** in **Icon Catalog → Applications**. When the local welcome page
appears, press **Ctrl+L**, enter `http://frogfind.au/` and press **Return**.
To search, type `NetBSD` in **Leap to** and submit the form. If Mozilla asks
whether to send the query over an unencrypted connection, **Continue** sends it.
[Search results on 6.5.30f](2026-11-25-mozilla-frogfind-search-6.5.30f.png).
For a second site, try `http://info.cern.ch/hypertext/WWW/TheProject.html`.
The guest needs outbound IPv4 connectivity and a working NetBSD resolver.

## Update an existing November 25 Mozilla input disk

The same small ISO updates either release and preserves your user profile and
desktop settings. It checks the running system, installed kernel file and
previous module. Shut the guest down, then start the older bundle with the
extra CD attached. Substitute `6.5.30f` for the other guest.

```sh
.work/images/xiri-indy-6.5.22f-mozilla-input-20261125/run-iris.sh --cdrom5 "$PWD/.work/modules/irix-browser-network-20261125/browser-network.iso"
```

Run the following in a NetBSD root shell. With the Freeware CD at SCSI ID 4,
the update CD at ID 5 appears as `cd1a`.

```sh
mkdir -p /mnt/browser-net &&
mount -r -t cd9660 /dev/cd1a /mnt/browser-net &&
sh /mnt/browser-net/install.sh &&
umount /mnt/browser-net &&
shutdown -r now
```

The installer enables `xiri_hosts` in `/etc/rc.conf.d/xiri_hosts` on a fresh
install. It preserves an existing setting. After reboot, these commands check
the service and the record available to an IRIX client.

```sh
/etc/rc.d/xiri_hosts status
cat /emul/irix/ns/.local/hosts.byname/frogfind.au
```

To roll back an updated Mozilla input disk, stop the resolver, disable it,
restore the saved module and reboot.

```sh
mod=/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod
/etc/rc.d/xiri_hosts onestop &&
printf 'xiri_hosts=NO\n' > /etc/rc.conf.d/xiri_hosts &&
cp -p "$mod.pre-browser-network" "$mod" &&
shutdown -r now
```

## Where the request stopped

1. On both original Xiri input disks, NetBSD resolved `frogfind.au` and its
   native FTP client fetched the public HTTP homepage, including its
   `FrogFind!` title. NeverSSL also responded over HTTP.
2. The vendor libc tried the IRIX name-service path
   `/ns/.local/hosts.byname/<hostname>`. The Xiri disk lacked that service.
   A temporary host record let Mozilla reach a nonblocking TCP connection.
3. IRIX syscall 1095, `getsockopt(SOL_SOCKET, SO_ERROR)`, returned `ENOSYS`
   when Mozilla checked whether the connection had completed. After that was
   fixed, the first HTTP request hit `ENOSYS` at syscall 1101, `send`.
   Working traces show a successful send, received HTTP bytes via syscall
   1097 and a one-byte `MSG_PEEK` on the connection.

NetBSD fork commit `5f6d833d936` implements these connected-socket operations
and translates the pending error into IRIX errno numbering. Nonblocking
`EINPROGRESS` is 150. A refused loopback connection yields `ECONNREFUSED`
(146) once, then zero. Both o32 and n32 test programs matched all 16 words
measured on original IRIX 6.5.22f, on each Xiri release. The controls include a
one-byte output buffer, null pointers and an invalid descriptor.
[Probe source and build script](../../lab/irix-browser-network/).

## Where names come from

The `xiri_hosts` rc.d service mounts a read-only directory under the IRIX
emulation root. Opening a hostname returns an IPv4 hosts-file record obtained
with NetBSD `getaddrinfo`. The helper uses an ephemeral loopback UDP port,
accepts requests from the local NFS client on a reserved port, and serves
requests as `nobody`. It implements the `hosts.byname` lookup used here.
Reverse lookup, IPv6 and other IRIX name-service maps remain open. On both
guests, the ordinary user resolved localhost, FrogFind and CERN, and a lookup
under `.invalid` failed. No per-site entries or browser proxy are required.
[SGI's name service](https://techpubs.jurassic.nl/library/manuals/2000/007-2860-012/sgi_html/ch07.html).

NetBSD's 32-bit mount interface on the 64-bit Indy kernel handles the NFS
mount argument layout. An initial PUFFS helper received `EINVAL` on these
disks. The shipped helper uses the kernel's NFSv2 client directly. It binds
its own port and needs no mountd, exported filesystem or rpcbind registration.

## Rebuild the update

From the Xiri checkout, build the fork module with the matching kernel tools,
then build the native helper against the sgimips sysroot and write the ISO.
Choose a new output pathname for each build.

```sh
lab/ip28-kernel/build-module.sh ../NetBSD-xiri .work/netbsd-octane-build/tools .work/browser-network-build
packaging/mozilla/network/build.sh .work/netbsd-build/tools .work/fam/sysroot \
    .work/browser-network-build/module/compat_irix_o32.kmod .work/browser-network.iso
```

The distributed update ISO has SHA-256
`2924112e20d60752e821bb916c38e9fab6de7693ae8630b14d913b52009c6326`.
The module installed by both images is
`8be760a6e36bb163c83d5038654841b86572bc49645ebdcfbd997f9377dcb7fc`.
The in-guest installer ran twice on fresh private copies of both previous
disks. The second installation preserved the original module backup. The
98 host regression tests passed. [Update sources](../../packaging/mozilla/network/).

## Standalone CHDs

| Release | CHD bytes | SHA-256 |
| --- | ---: | --- |
| 6.5.22f | 501,724,600 | `7bf3269dfa297286dbd532812a98fb384f004b7fa9df6a0017a42ecfd01ab64e` |
| 6.5.30f | 481,604,908 | `1ff9eacf2141fb1cd4271141d138b794ba66f63cdb521c9a1c00c895f4c9165d` |

Each standalone CHD passed raw and overall SHA-1 verification with `chdman`.
A fresh overlay then cold-booted through xdm, mounted the resolver and loaded
the expected module. Repeating service startup kept the same PID. Stopping it
unmounted the directory and ended that process. Restarting it restored normal
lookups. On both disks, `xiritest` launched the browser from **Applications**, reached FrogFind
and CERN, and submitted the search. A View menu remained painted over part of
the 6.5.22f browser in the cold-boot capture while navigation continued.
