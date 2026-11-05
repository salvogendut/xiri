/* Guest-only delay injection. Interpose real libc calls, never fabricate
 * process events. After the guard prints its verdict, audit its queue at
 * close. Do not install this library in the production runtime. */
#include <sys/types.h>
#include <sys/event.h>
#include <sys/proc.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <dlfcn.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static pid_t owner;
static int queue = -1, triggered, delay_signal, suppress;
static long delay_ms;
static int (*real_kill)(pid_t, int);
static int (*real_close)(int);
static int (*real_kqueue)(void);
static int (*real_kevent)(int, const struct kevent *, size_t,
    struct kevent *, size_t, const struct timespec *);

static long long
now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) _exit(90);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

__attribute__((constructor)) static void
setup(void)
{
    owner = getpid();
    real_kill = dlsym(RTLD_NEXT, "kill");
    real_close = dlsym(RTLD_NEXT, "close");
    real_kqueue = dlsym(RTLD_NEXT, "kqueue");
    real_kevent = dlsym(RTLD_NEXT, "__kevent100");
    if (!real_kill || !real_close || !real_kqueue || !real_kevent) _exit(91);
    const char *mode = getenv("XIRI_DELAY_CASE");
    if (!mode) _exit(92);
    delay_ms = !strcmp(mode, "fast") ? 0 : 7000;
    delay_signal = !strcmp(mode, "kill") ? SIGKILL : SIGTERM;
    suppress = !strcmp(mode, "live");
    /* The worker must execute without the injection library. Forked children
     * retain this address space briefly; the owner check excludes them. */
    unsetenv("LD_PRELOAD");
}

int
kqueue(void)
{
    int fd = real_kqueue();
    if (getpid() == owner) queue = fd;
    return fd;
}

int
kill(pid_t pid, int sig)
{
    if (getpid() != owner || pid <= 1) return real_kill(pid, sig);
    int result = suppress ? 0 : real_kill(pid, sig), saved = errno;
    if (!triggered && sig == delay_signal) {
        triggered = 1;
        long long begin = now(), end = begin + delay_ms;
        fprintf(stderr, "INJECT pid=%d signal=%d suppress=%d result=%d delay=%ld\n",
            pid, sig, suppress, result, delay_ms);
        while (now() < end) {
            struct timespec pause = {0, 10000000};
            nanosleep(&pause, NULL);
        }
        struct kinfo_proc2 p;
        int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, sizeof(p), 1};
        size_t size = sizeof(p);
        memset(&p, 0, sizeof(p));
        int present = sysctl(mib, 6, &p, &size, NULL, 0) == 0 &&
            size == sizeof(p) && p.p_pid == pid;
        fprintf(stderr, "DELAY_RETURN pid=%d elapsed=%lld present=%d state=%u uvalid=%u\n",
            pid, now()-begin, present, (unsigned)p.p_realstat, (unsigned)p.p_uvalid);
        /* NetBSD kqueue_stat exposes KQ_COUNT without consuming an event. */
        struct stat st;
        if (fstat(queue, &st)) _exit(93);
        fprintf(stderr, "QUEUE_BEFORE_RETURN pending=%lld\n", (long long)st.st_size);
    }
    errno = saved;
    return result;
}

int
close(int fd)
{
    if (getpid() == owner && fd == queue) {
        struct timespec zero = {0, 0};
        struct kevent ev[64];
        int n, total = 0;
        while ((n = real_kevent(fd, NULL, 0, ev, 64, &zero)) > 0) {
            for (int i = 0; i < n; ++i)
                fprintf(stderr, "PENDING pid=%lu filter=%d flags=%x fflags=%x data=%lld\n",
                    (unsigned long)ev[i].ident, ev[i].filter, ev[i].flags,
                    ev[i].fflags, (long long)ev[i].data);
            total += n;
        }
        fprintf(stderr, "QUEUE_CLOSE pending=%d error=%d injected=%d\n",
            total, n < 0 ? errno : 0, triggered);
    }
    return real_close(fd);
}
