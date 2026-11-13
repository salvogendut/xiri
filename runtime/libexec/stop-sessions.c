/* End marked desktop guards before rc.shutdown stops xdm and FAM.
 * Process identities come from the kernel; no user-written PID files or
 * commands are trusted. The guards save with their own login credentials. */
#include <sys/types.h>
#include <sys/event.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <errno.h>
#include <kvm.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define GUARD "/usr/local/libexec/xiri/session-guard"
struct target { struct kinfo_proc2 process; int waiting; };

static void timeout(int sig)
{
    static const char message[] = "XIRI_SESSIONS timeout; continuing system shutdown\n";
    (void)sig;
    (void)write(STDERR_FILENO, message, sizeof(message)-1);
    _exit(2);
}

static int current(const struct kinfo_proc2 *old)
{
    struct kinfo_proc2 p;
    int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, old->p_pid, sizeof(p), 1};
    size_t size = sizeof(p);
    if (sysctl(mib, 6, &p, &size, NULL, 0)) return -1;
    return size == sizeof(p) && p.p_pid == old->p_pid && p.p_uvalid &&
        (p.p_realstat == SACTIVE || p.p_realstat == SSTOP) &&
        p.p_ustart_sec == old->p_ustart_sec && p.p_ustart_usec == old->p_ustart_usec &&
        p.p_uid == old->p_uid && p.p_ruid == old->p_ruid &&
        !strcmp(p.p_comm, "session-guard");
}

int main(int argc, char **argv)
{
    (void)argv;
    if (argc != 1 || getuid() != 0 || geteuid() != 0) {
        fputs("Usage (as root): stop-sessions\n", stderr);
        return 2;
    }
    /* One deadline covers all desktops, including process queries. The
     * per-user guard already bounds save (15s) and cleanup (6s). */
    signal(SIGALRM, timeout);
    alarm(30);
    setvbuf(stdout, NULL, _IOLBF, 0);
    char error[_POSIX2_LINE_MAX];
    kvm_t *kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, error);
    if (!kd) { fprintf(stderr, "process query: %s\n", error); return 2; }
    int count;
    struct kinfo_proc2 *processes = kvm_getproc2(kd, KERN_PROC_ALL, 0,
        sizeof(*processes), &count);
    if (!processes) { fprintf(stderr, "process query: %s\n", kvm_geterr(kd)); kvm_close(kd); return 2; }
    struct target *targets = calloc(count ? (size_t)count : 1, sizeof(*targets));
    if (!targets) { perror("allocate sessions"); kvm_close(kd); return 2; }
    size_t selected = 0, remaining = 0;
    int failed = 0;
    for (int i = 0; i < count; ++i) {
        const struct kinfo_proc2 *p = &processes[i];
        if (!p->p_uid || p->p_uid != p->p_ruid || !p->p_uvalid ||
            (p->p_realstat != SACTIVE && p->p_realstat != SSTOP) ||
            strcmp(p->p_comm, "session-guard")) continue;
        char **args = kvm_getargv2(kd, p, 0);
        if (!args) {
            if (current(p) != 0) { fprintf(stderr, "cannot inspect guard %d\n", p->p_pid); failed = 1; }
            continue;
        }
        if (!args[0] || !args[1] || strcmp(args[0], GUARD) || strcmp(args[1], "--desktop")) continue;
        targets[selected++].process = *p;
    }
    kvm_close(kd);
    int kq = kqueue();
    if (kq < 0) { perror("kqueue"); free(targets); return 2; }
    for (size_t i = 0; i < selected; ++i) {
        struct target *t = &targets[i];
        struct kevent event;
        EV_SET(&event, t->process.p_pid, EVFILT_PROC, EV_ADD, NOTE_EXIT, 0, NULL);
        if (kevent(kq, &event, 1, NULL, 0, NULL)) {
            if (errno != ESRCH) { perror("watch guard"); failed = 1; }
            continue;
        }
        int same = current(&t->process);
        if (same != 1) {
            if (same < 0) { perror("recheck guard"); failed = 1; }
            continue;
        }
        if (kill(t->process.p_pid, SIGTERM)) {
            if (errno != ESRCH) { perror("stop guard"); failed = 1; }
            continue;
        }
        t->waiting = 1; ++remaining;
        printf("XIRI_SESSIONS request pid=%d uid=%u\n", t->process.p_pid, t->process.p_uid);
    }
    while (remaining) {
        struct kevent events[32];
        int n = kevent(kq, NULL, 0, events, 32, NULL);
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("wait guards"); failed = 1; break;
        }
        for (int i = 0; i < n; ++i) {
            if (events[i].flags & EV_ERROR) { failed = 1; continue; }
            if (!(events[i].fflags & NOTE_EXIT)) continue;
            for (size_t j = 0; j < selected; ++j) {
                struct target *t = &targets[j];
                if (t->waiting && (uintptr_t)t->process.p_pid == events[i].ident) {
                    t->waiting = 0; --remaining;
                    printf("XIRI_SESSIONS exited pid=%d status=%lld\n", t->process.p_pid, (long long)events[i].data);
                    if (events[i].data) failed = 1;
                    break;
                }
            }
        }
    }
    printf("XIRI_SESSIONS complete selected=%zu remaining=%zu valid=%d\n", selected, remaining, !failed);
    close(kq); free(targets);
    return failed || remaining ? 2 : 0;
}
