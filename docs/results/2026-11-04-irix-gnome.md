# GNOME startup and original IRIX gedit on NetBSD

Original gedit 0.9.7 now opens, edits text, saves a new document, reopens it
and overwrites it as xiritest. Its existing Freeware Icon Catalog entry
launches the editor and changes to the yellow opened artwork. The
[PNG](images/2026-11-04-irix-gedit.png) shows the reopened document after a
second save. Preferences, help, image decoding and plug-ins remain separate
follow-ups. These results use a candidate module and additional resources in
a disposable copy of the GIMP CHD; the published manual CHD is unchanged.
The [machine-readable record](2026-11-04-irix-gnome.json) retains application,
regression, resource, startup and cleanup evidence. Every owned test guest
halted cleanly, and the final host check found no remaining emulator processes.

## Diagnosed failure

The [catalog survey](2026-11-03-irix-catalog.md) found nine busy launch
targets without application windows, including three GNOME Terminal routes.
An independent, untraced gedit retry in a fresh xiritest home reproduces the
failure: about 30.51 seconds of accumulated CPU time, 80.9% in the late
guest `ps` sample, and no viewable application window before the 45-second
test stop. The guard verifies cleanup of its one tracked process.

A short trace contains 3,337 entry/return pairs: 1,669 calls to
`socket(1, 2, 0)` returning IRIX `EAFNOSUPPORT` (124), alternating with 1,668
`close(-1)` failures. A separate bounded native ptrace sampler places the
caller at `iiop_connection_server_unix+0xe8` in original ORBit `libIIOP.so.1`.
The sampled instruction bytes match that original library. This establishes
gedit's Unix listener loop; the other applications need their own observations.

The original gedit executable is unchanged, SHA-256
`19c648f17373da8b9412e1cba988d7135f2ba177ca20ba62509de0c80a96ccef`.
No vendor source is used. The [baseline record](2026-11-04-irix-gnome-baseline.json)
retains the process, trace and sampler evidence.

## Compatibility and resource changes

`compat_irix_o32` now translates pathname Unix stream sockets, including
bind, listen, connect, accept, local/peer names, ordinary stream I/O and
legacy sendmsg/recvmsg with data-only messages. The adapter converts the
foreign 16-bit address family to NetBSD's length/family fields and translates
the foreign socket type. NetBSD owns sockets, filesystem permissions and
credentials. No new core-kernel hook or emulator change is required.

NetBSD `xiri` commit `0b2e08f1c0b` is byte-equivalent to the recorded build
inputs. The module SHA-256 is
`4c868b35245339976c4ed0c987b36c78cec350941028a4ca02127c6e1af406b5`;
the N64 core remains at qualified source `9390bc04900`. The build record
retains its actual pre-commit parent and dirty-source hashes.

This is a bounded subset. Unix datagrams, socketpair and descriptor passing
remain unsupported. Local recvmsg rejects address/rights outputs. Native
`sun_path` is four bytes smaller than IRIX's; overlong paths are rejected
without truncation. Accept is qualified for Unix sockets only. Unix
SIOCNREAD, additional output-fault/accept combinations and broader concurrency
need further work. The qualifier distinguishes 96 original-IRIX comparisons
from 40 explicit subset-policy observations, rather than claiming full socket
compatibility.

With the socket module alone, gedit stops looping and exits with a missing
`libgnomevfs-pthread.so` diagnostic. Static DT_NEEDED closure did not discover
that dynamically loaded backend. The read-only
[resource stager](../../scripts/stage-irix-gnome.py) imports:

| Original source | Destination / purpose |
| --- | --- |
| `/usr/freeware/share/gedit` | Same path beneath `/emul/irix`: original dialogs and application data |
| `/usr/freeware/lib32/gedit` | Same prefix: original editor plug-ins; individual plug-ins remain unqualified |
| `/usr/freeware/lib32/vfs` | Same prefix: GNOME VFS modules |
| `/usr/freeware/etc/vfs` | Same prefix: module configuration |
| `/usr/freeware/lib32/libgnomevfs-pthread.so` | Same prefix: dynamically loaded threading backend |
| `/usr/freeware/lib32/libbz2.so.1` | Same prefix: additional module dependency |
| `/usr/freeware/share/pixmaps/gedit-icon.png` | Same prefix: application icon; loading still warns despite verified presence |

The [ledger](../../lab/irix-gnome/resources.json) records all 50 paths:
42 files and eight directories, with original/applied modes, hashes and
dependency edges. ELF files follow the existing 0555 import policy; data
uses 0644 and directories 0755, owned by root. Source bytes are unchanged.
The existing native `/usr/freeware` alias is retained. No old user preferences
or package database are imported.

## Checks

The [Unix socket results](2026-11-04-irix-gnome-unix.json) cover 136 native
executions: o32/n32, direct/indirect traps and root/UID 1234. The same four
fixture binaries produced 68 reference records on original IRIX 6.5.22m.
Stream exchange, endpoint names, truncated/zero/negative output capacities,
unsupported types/protocols and malformed input addresses are compared.
Every native fixture exits normally with its process group absent.
Reference long-path mode 28 reused a filename: only its first original run
is clean; later EADDRINUSE results are retained and no parity claim uses them.

Another 368 existing IPv4 regressions pass unchanged: 304 TCP cases and
64 legacy recvmsg cases under both identities. They include real data
exchange with independent native peers, malformed inputs, socket options,
short/partial-fault receives, EOF, nonblocking reads and peeking.
The module builds with warnings treated as errors and passes the symbol/
relocation audit. The qualified N64 core kernel and boot wrapper are unchanged.

Actual GUI input enters two lines and saves
`/usr/people/xiritest/xiri-gedit-test.txt`. A fresh gedit process reopens the
same text. A third process, launched by catalog double-click, opens it through
the file dialog, appends another line and saves over the existing file:

| Save | Bytes | SHA-256 |
| --- | ---: | --- |
| New document | 55 | `0517af7359f4a7cde4b795dc9f8d5699b04ecd9f501527b80e8783f0a70c78d1` |
| Existing document | 87 | `427e8a18a019ac52a7f79d7d978ac6116bf43e6eac28d7b8c29120c8c1d6e466` |

The exact saved bytes match the supplied text; owner/group are 1234 and
mode is 0644. The first two GUI exits return status 0, with no tracked
descendants remaining. Preference writes still warn about an unimplemented
interface. Shared-memory transport uses its fallback; the missing help
topics and imlib image-loading warning remain visible.

The catalog-launched process also closes through its Exit toolbar button:
its PID/window disappear and FAM emits `Exited`. This detached catalog
launch does not provide a captured exit status, unlike the two guarded
direct launches. The opened icon returns to its closed shape; selection
highlighting is distinct from its running state.
An independent 60×45-pixel comparison finds 855 changed icon pixels while
running and an exact return to the original pixels after exit/deselection.

## Other application follow-ups

The same candidate and resources were used to repeat all eight remaining
previously busy targets, with the original 45-second startup guard. Each
now presents UI; these are observed startup changes, not eight functional
application passes. Their late samples show idle processes, with about
0.66–1.92 seconds of CPU in the main applications, and every guard verifies
complete descendant cleanup:

| Target | New observation / next boundary |
| --- | --- |
| Evolution | [Copy-error dialog](images/2026-11-04-irix-evolution.png); missing `/usr/freeware/share/evolution/default_user/*` |
| GNOME Terminal, glynx, Midnight Commander | [Terminal plus login-error dialog](images/2026-11-04-irix-gnome-terminal.png); `unable to fork: Function not implemented`, plus preference errors |
| Balsa | [Configure Balsa wizard](images/2026-11-04-irix-balsa.png), partly blank in the captured frame; setup was not advanced |
| Glade | [Main window, palette and properties](images/2026-11-04-irix-glade.png); OAF activation and preference-write warnings; no project edited/saved |
| Gnumeric | [Font error](images/2026-11-04-irix-gnumeric.png): no suitable default font / missing GNOME print `fontmap2` |
| XChat | [First-run download-directory notice](images/2026-11-04-irix-xchat.png); dialog not advanced, no network-use check |

The terminal diagnostic is not proof that `fork` itself is missing; trace
the child/PTY initialization path before selecting an adapter. The
[per-tab checklist](../ICON-CATALOG.md) records these follow-ups for every
matching entry without overwriting the historical survey. Direct startup
checks of wrappers do not qualify their underlying terminal program or
catalog action.

## Reproduction and limits

See the [lab guide](../../lab/irix-gnome/README.md) for the independent
fixtures, sampler, module build and disposable-guest workflow. The
[build record](../../lab/irix-gnome/build.json) pins every module input and
the equivalent committed source. Large original resources, traces and disk
overlays stay in ignored `.work` directories.

Early attempts are retained as diagnostics: the first candidate omitted
the new calls from the explicit dispatcher and failed the raw socket checks;
the corrected candidate is the one qualified here. A graphical-PROM serial
prompt wait required a harness cold-start correction. A shell `&;` typo
prevented one attempted launch. An original-IRIX X query stalled and provides
no GUI comparison. The trace transfer exceeded its first deadline; recovery
from the complete serial frame matched the guest checksum. Failed pointer/
focus attempts are excluded from GUI acceptance. None of these attempts is
counted as an application pass.

The maintained sampler has five additional native controls for normal
sampling, early exit, failed exec, invalid IDs and interrupted cleanup. An
initial early-exit test used the nonexistent native `/bin/true`; that fixture
error is retained and the control was corrected to `/bin/sleep 0`. It is
separate from gedit's startup diagnosis and from the socket qualification.
