# One IRIX n32 pthread

[create-join.c](create-join.c) starts one worker through the installed SGI
`libpthread.so`. The worker checks its pthread identity, records its process
ID, changes a shared integer from 35 to 42 and returns the address of that
integer. The parent joins and checks all four results.

On IRIX with the n32 C development tools installed, build and run using:

```sh
cc -n32 -mips3 -o create-join create-join.c -lpthread
./create-join
./create-join system
```

Run both commands as an ordinary user and as root. On both original
releases, default scope exits zero with
`same_pid 1 distinct_thread 1 value 42 returned_pointer 1`. The order of
`worker ran` and `create 0` depends on scheduling. Only root passed the
explicit system-scope case in these controls. An ordinary user got
`attr_setscope 1` (EPERM) and fixture exit 4.

To see the two returns from a successful call, run as root on original IRIX:

```sh
/usr/sbin/par -s -i -SS -T -o /tmp/thread.par ./create-join
grep nsproc /tmp/thread.par
```

Copy the same executable to a writable directory on each Xiri guest and run
it as the logged-in user. The timeout bounds the vendor library's retry loop.
Use a separate trace filename for each mode and user.

```sh
/usr/bin/timeout -k 2 10 ./create-join
/usr/bin/timeout -k 2 10 ktrace -i -t u -f thread.ktrace ./create-join
strings thread.ktrace | grep -E 'syscall=(1204|1082) '
```

## Building with the original development CDs and a cross compiler

The qualified donors have SGI cpp and the runtime libraries. The development
CDs supplied the n32 assembler, linker, headers and startup objects. The lab
installed those tools into a private `/tmp/pt-sdk` on its 6.5.22f donor
overlay. The C compiler front end was unavailable, so the following three
steps produced the measured executable. The linker used the donor's runtime
libraries. Keep the SDK and intermediate files private.

1. On the IRIX donor, preprocess the fixture using the SDK and base-system headers.

   ```sh
   /usr/lib32/cmplrs/cpp -P -I/tmp/pt-sdk/usr/include \
       -D_LANGUAGE_C -D__sgi -D__mips=3 -D_MIPSEB -D_MIPS_ISA=3 \
       -D_MIPS_SIM=2 -D_MIPS_SZPTR=32 -D_MIPS_SZINT=32 \
       -D_MIPS_SZLONG=32 -D_LONGLONG create-join.c > probe.i
   ```

2. Transfer `probe.i` to the host. Emit n32 MIPS III assembly with the NetBSD
   cross compiler. Remove GNU assembler metadata and mode directives from
   this listing for the SGI assembler.

   ```sh
   mips64--netbsd-gcc -mabi=n32 -march=mips3 -mabicalls -fPIC -G0 -O1 \
       -fno-stack-protector -fno-builtin -fno-asynchronous-unwind-tables \
       -fno-unwind-tables -fno-merge-constants -fno-ident -S probe.i -o gcc.s
   sed -E '/^[[:space:]]*\.(abicalls|section \.mdebug|previous|nan|module|type|size|set[[:space:]]+(nomips16|nomicromips)|file|ident)/d' gcc.s > probe.s
   ```

3. Return `probe.s` to the donor. The private assembler driver needs the
   donor's cpp and acpp available under `$TOOLROOT/usr/lib32/cmplrs/`.

   ```sh
   export TOOLROOT=/tmp/pt-sdk
   crt=$TOOLROOT/usr/lib32/mips3
   "$TOOLROOT/usr/lib32/cmplrs/as" -n32 -mips3 -KPIC -c probe.s -o probe.o
   "$TOOLROOT/usr/lib/ld" -s -n32 -mips3 -call_shared -o create-join \
       "$crt/crt1.o" probe.o -L/usr/lib32 -lpthread -lc "$crt/crtn.o"
   ```

The SGI-assembled executable has ELF flags `0x20000024` and requests
`/usr/lib32/libc.so.1`. An exploratory GNU-assembled build carried
`EF_MIPS_NOREORDER` (`0x20000025`). Both donors ran it, and both Xiri
loaders rejected it before `main`. The [four-guest results](../../docs/results/2026-11-25-irix-pthread.md)
use the SGI-assembled file on every guest.

## Raw worker entry

The independent [n32 assembly probe](entry.S) supplies different addresses
for the syscall trampoline and the descriptor entry. It records which one
runs, the registers on entry, and the fixed-address PRDA as seen by each
thread. Build it from the project root with the sgimips toolchain.

```sh
mips64--netbsd-gcc -EB -march=mips3 -mabi=n32 -mno-abicalls -fno-pic -G0 \
    -c lab/irix-pthread/entry.S -o entry.o
mips64--netbsd-ld -EB -m elf32btsmipn32 --build-id=none \
    -z max-page-size=8192 -T lab/irix-prda/probe.ld entry.o -o entry
```

Run `./entry > entry.bin` in the guest, then copy the 100-byte file to
the host and run `python3 lab/irix-pthread/check-entry.py < entry.bin`.
The checker accepts the guest's process ID and verifies the stack pointer
relative to the supplied stack top. Timeout, partial output, a shared PRDA
marker or entry through the wrong trampoline fails the check.

## Event workers, address-based waits and stack guards

[event.c](event.c) builds the following independent n32 executables. Each runs as
an ordinary user and prints the actual syscall results. A negative number
is the IRIX errno from that call. From the project root, build the tests
into a private directory with the NetBSD sgimips cross tools on `PATH`.

```sh
out=.work/event-probes
mkdir -p "$out"
for name in event waitwake waitpair guard bounds sigpoll ordered16 ordered47 \
    waiting47 caughtwait47 caughtearly47; do
    case "$name" in
        event) flag= ;;
        waitwake) flag=-DWAIT_WAKE ;;
        waitpair) flag=-DWAIT_PAIR ;;
        guard) flag=-DSTACK_GUARD ;;
        bounds) flag=-DSTACK_GUARD_BOUNDS ;;
        sigpoll) flag=-DSIGNAL_POLL ;;
        ordered16) flag=-DEVENT_SIGNAL ;;
        ordered47) flag="-DEVENT_SIGNAL -DEVENT_PRIVATE" ;;
        waiting47) flag="-DEVENT_SIGNAL -DEVENT_PRIVATE -DEVENT_WAITING" ;;
        caughtwait47) flag="-DEVENT_SIGNAL -DEVENT_PRIVATE -DEVENT_CAUGHT -DEVENT_WAITING" ;;
        caughtearly47) flag="-DEVENT_SIGNAL -DEVENT_PRIVATE -DEVENT_CAUGHT" ;;
    esac
    mips64--netbsd-gcc -O2 -Wall -Wextra -Werror -EB -march=mips3 \
        -mabi=n32 -mno-abicalls -fno-pic -G0 -ffreestanding \
        -fno-stack-protector $flag -c lab/irix-pthread/event.c -o "$out/$name.o"
    mips64--netbsd-ld -EB -m elf32btsmipn32 --build-id=none \
        -z max-page-size=8192 -T lab/irix-prda/probe.ld \
        -o "$out/$name" "$out/$name.o"
done
```

Copy the binaries to a writable guest directory, make them executable and
run each separately. `event` keeps an ordinary worker alive, starts two
event workers together, then starts a replacement after releasing both.
It checks for distinct IDs among live workers and records the replacement
ID. `waitwake` blocks on one lock word while the parent posts two early
wakeups to another word on the same page. The waiter and waker use different
request structures for each word. After consuming both early wakeups, the
worker must still wait for a third. `waitpair` first posts and consumes a
wake before creating any workers. It then starts two workers on the same
lock word and checks that each wake releases exactly one. It supplies
wake policy 65535 for the early wake and 0 for the later wakes, matching
the vendor calling convention in which only the wait initializes policy.
`guard` maps a private writable region
after creating a worker, toggles its first 8 KiB to `PROT_NONE` and back to
read/write, then checks its marker.

`bounds` checks Xiri's threaded range restrictions. It creates two private
pages beside a shared page, starts a worker, then protects one byte of the
first page. A one-byte read from `/dev/zero` into that page must return
EFAULT while the neighbouring page accepts the same read. After restoring
read/write access, both pages must accept it. The probe also checks that a
request spanning the private/shared boundary fails before changing either
page, and that the per-thread PRDA page rejects a protection change.

`sigpoll` isolates n32 syscall 1166 in a single thread. It blocks SIGUSR1,
waits up to 10 ms with no pending signal, sends SIGUSR1 to itself and polls
twice with a zero timeout. Both original releases returned `-11, 16, -11`,
with signal 16 in the result structure. The executable also times a 200 ms wait with a null info pointer and
checks that a nanosecond field of one billion returns EINVAL.

`ordered16` blocks SIGUSR1 in the event worker. The parent sends it to that
worker by its IRIX thread ID. Once the send returns, the worker reads its
signal and polls again to check consumption. The other four variants block
SGI's private pthread signal 47 in the worker. Each expects the targeted
send to succeed. The receiver's result depends on the disposition.

| Probe | Disposition | Sender timing | First wait | Immediate second wait |
| --- | --- | --- | --- | --- |
| `ordered47` | Default | Before wait | EAGAIN | EAGAIN |
| `waiting47` | Default | Delayed sender | EAGAIN | EAGAIN |
| `caughtearly47` | SA_SIGINFO handler | Before wait | 47, reported signo 47 | EAGAIN |
| `caughtwait47` | SA_SIGINFO handler | Delayed sender | 47, reported signo 47 | EAGAIN |

The early-send worker waits for an acknowledgement from the sender before
calling `__sigpoll`. In the delayed-send variants the worker publishes that it
has blocked the signal, then starts a 500 ms timed wait while the sender
sleeps ten ticks. The caught variants install the handler before creating
workers. An unexpected asynchronous invocation fails the test. See the
[Mozilla investigation](../../docs/results/2026-11-25-mozilla-input.md) for
the syscall sequence measured in the native browser.

To see the blocking and waking threads separately on IRIX, run `par` as
root after the ordinary-user checks.

```sh
/usr/sbin/par -s -i -SS -T -o /tmp/waitwake.par ./waitwake
grep usync_cntl /tmp/waitwake.par
```

[Original IRIX and Xiri comparison](../../docs/results/2026-11-25-irix-event-workers.md) ·
[Private lock implementation and retest](../../docs/results/2026-11-25-irix-usync.md) ·
[Private stack-guard implementation and retest](../../docs/results/2026-11-25-irix-stack-guard.md) ·
[Mozilla signal waits and local X connections](../../docs/results/2026-11-25-mozilla-event-diagnosis.md) ·
[Timed and directed signal results](../../docs/results/2026-11-25-mozilla-sigpoll.md).
