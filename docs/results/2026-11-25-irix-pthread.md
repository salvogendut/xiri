# A one-worker test for the Mozilla startup wait

On original IRIX 6.5.22f and 6.5.30f, an ordinary user created and joined
a pthread with the vendor's default attributes. On both Xiri desktops,
the same executable entered `pthread_create`, retried the missing `nsproc`
system call four times in ten seconds, and never entered the worker. Both
versions of Mozilla showed the same call and retry sequence during startup.
[Mozilla traces](2026-11-24-indy-mozilla.md)

| Caller and scope | Original 6.5.22f and 6.5.30f | Xiri with each release's libraries |
| --- | --- | --- |
| Ordinary user, default | Worker ran, join passed | Four `nsproc` attempts, timeout 124 |
| Root, default | Worker ran, join passed | Four `nsproc` attempts, timeout 124 |
| Ordinary user, system | `pthread_attr_setscope` returned EPERM (1) | Same EPERM, zero `nsproc` calls |
| Root, system | Worker ran, join passed | One `nsproc` attempt, `pthread_create` returned ENOSYS (89) |

The default-scope worker had the parent's process ID and a distinct pthread
identity. It updated the shared value to 42 and returned its address through
`pthread_join`. The original controls ran on an Indy R4400 (6.5.22f) and an
O2 R5000 (6.5.30f), using `guest` for the ordinary-user cases. Xiri used
`xiritest` on the two v5 Indy guests, R4400 and R5000 respectively, with
NetBSD 11.99.11 and the module from `1d7a8b42efb`. Each Xiri case ran
with and without tracing. The executable was identical across all four guests.
[Probe and build instructions](../../lab/irix-pthread/README.md) · [Release pins and measured traces](2026-11-25-irix-pthread.json)

The [kernel follow-up](2026-11-25-nsproc.md) records the same checks with real worker support and the subsequent Mozilla launches.

## What the kernel must supply

SGI's `par` showed one successful `nsproc` call in each traced original
run. Both scopes passed `0x020000ff` (`PR_SALL | PR_THREADS | PR_NOLIBC`).
The parent saw a return value of 1 and the new thread saw 0. The fourth
argument was null for default scope and pointed to scheduling attributes
for system scope. The default worker subsequently called
`prctl(PR_THREAD_CTL, PR_THREAD_BLOCK, ...)`. The system-scope worker
used `PR_THREAD_EXIT`. A successful join can therefore precede the exit
of the underlying default-scope kernel worker.

On Xiri, trap 1204 returned `v0=0x59, a3=1` on each attempt. In default
scope, vendor libc followed it with `sginap`, first for 100 ticks and then
200. In system scope as root, the error reached the caller immediately.
Root/system exposes the first failed call directly. Ordinary-user/default
exercises the path Mozilla takes.

The next kernel step is to start a real second execution context sharing the
process address space, with the child registers and per-thread PRDA state
expected by vendor libc. Check for the worker's write first, then verify
join, the returned pointer, and clean exit on both releases. Once those pass,
retest each catalog icon against a local HTML page.
