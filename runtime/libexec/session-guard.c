/* Supervise only this launch's descendants, including setsid/double-fork.
 * NetBSD NOTE_TRACK attaches child knotes inside fork, before the child runs.
 * Run as the session user; neither UID-wide scans nor kill(-1) are used. */
#include <sys/types.h>
#include <sys/event.h>
#include <sys/proc.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

struct member { pid_t pid; uint32_t sec, usec; size_t generation; int live, identity, sent; };
static struct member *members;
static size_t capacity, total, alive;
static volatile sig_atomic_t requested;
static void stop(int sig) { requested = sig; }

static long long now(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) { perror("clock_gettime"); exit(2); }
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int info(pid_t pid, struct kinfo_proc2 *p)
{
    int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, sizeof(*p), 1};
    size_t size = sizeof(*p);
    memset(p, 0, sizeof(*p));
    return sysctl(mib, 6, p, &size, NULL, 0) == 0 && size == sizeof(*p) && p->p_pid == pid;
}

static int events(int kq)
{
    struct kevent ev[64];
    struct timespec zero = {0, 0};
    int n, failed = 0;
    while ((n = kevent(kq, NULL, 0, ev, 64, &zero)) > 0) {
        for (int i = 0; i < n; ++i) {
            if ((ev[i].flags & EV_ERROR) || (ev[i].fflags & NOTE_TRACKERR)) {
                fprintf(stderr, "tracking failed pid=%lu flags=%x data=%lld\n",
                    (unsigned long)ev[i].ident, ev[i].fflags, (long long)ev[i].data);
                failed = 1;
            }
            pid_t pid = (pid_t)ev[i].ident;
            if (pid == getpid()) continue;
            if (ev[i].fflags & NOTE_CHILD) {
                size_t j;
                for (j = 0; j < capacity && members[j].live; ++j) {}
                if (j == capacity) {
                    size_t next = capacity ? capacity * 2 : 64;
                    struct member *grown = realloc(members, next * sizeof(*grown));
                    if (!grown) { failed = 1; continue; }
                    memset(grown + capacity, 0, (next - capacity) * sizeof(*grown));
                    members = grown; capacity = next;
                }
                struct member *m = &members[j];
                *m = (struct member){.pid=pid, .live=1, .generation=total+1};
                ++alive; ++total;
                printf("OWN pid=%d parent=%lld\n", pid, (long long)ev[i].data);
            }
            if (ev[i].fflags & NOTE_EXIT) {
                size_t j;
                for (j = 0; j < capacity; ++j)
                    if (members[j].live && members[j].pid == pid) break;
                if (j == capacity) {
                    fprintf(stderr, "unmatched exit pid=%d\n", pid); failed = 1;
                } else { members[j].live = 0; --alive; }
            }
        }
    }
    if (n < 0 && errno != EINTR) { perror("kevent"); failed = 1; }
    return failed;
}

static int identify(int kq)
{
    int failed = 0;
    for (size_t i = 0; i < capacity; ++i) {
        if (!members[i].live || members[i].identity) continue;
        size_t generation = members[i].generation;
        struct kinfo_proc2 p;
        if (!info(members[i].pid, &p) || !p.p_uvalid ||
            (p.p_realstat != SACTIVE && p.p_realstat != SSTOP)) continue;
        /* NOTE_CHILD is queued before fork assigns p_start. Wait until the
         * child is fully initialized, then drain exits before retaining its
         * identity: a PID recycled before this query has an exit queued.
         * events() may grow/reuse slots, so retain no pointer across it. */
        failed |= events(kq);
        struct member *m = &members[i];
        if (!m->live || m->generation != generation) continue;
        m->identity = 1; m->sec = p.p_ustart_sec; m->usec = p.p_ustart_usec;
    }
    return failed;
}

static int signal_members(int sig)
{
    int failed = 0;
    for (size_t i = 0; i < capacity; ++i) {
        struct member *m = &members[i];
        struct kinfo_proc2 p;
        if (!m->live || m->sent == sig || !info(m->pid, &p)) continue;
        /* Dying/zombie processes have no valid p_start in KERN_PROC2.
         * Their NOTE_EXIT retires them; they cannot receive another signal. */
        if (!p.p_uvalid || (p.p_realstat != SACTIVE && p.p_realstat != SSTOP) ||
            m->identity <= 0) continue;
        /* Refuse stale identities, rather than signaling a recycled PID. */
        if (m->sec != p.p_ustart_sec || m->usec != p.p_ustart_usec) {
            if (m->identity > 0)
                fprintf(stderr, "identity changed pid=%d old=%u.%06u new=%u.%06u\n",
                    m->pid, m->sec, m->usec, p.p_ustart_sec, p.p_ustart_usec);
            m->identity = -1; failed = 1; continue;
        }
        if (kill(m->pid, sig) && errno != ESRCH) { perror("kill descendant"); failed = 1; }
        m->sent = sig;
    }
    return failed;
}

static void report_remaining(int kq, pid_t leader, int finished)
{
    struct stat st;
    long long queued = fstat(kq, &st) == 0 ? (long long)st.st_size : -1;
    fprintf(stderr, "cleanup deadline leader=%d reaped=%d remaining=%zu queued=%lld\n",
        leader, finished, alive, queued);
    for (size_t i = 0; i < capacity; ++i) {
        struct member *m = &members[i];
        if (!m->live) continue;
        struct kinfo_proc2 p;
        int present = info(m->pid, &p);
        fprintf(stderr, "remaining pid=%d generation=%zu identity=%d start=%u.%06u sent=%d present=%d state=%u uvalid=%u current_start=%u.%06u\n",
            m->pid, m->generation, m->identity, m->sec, m->usec, m->sent,
            present, (unsigned)p.p_realstat, (unsigned)p.p_uvalid,
            p.p_ustart_sec, p.p_ustart_usec);
    }
}

int main(int argc, char **argv)
{
    char *end;
    /* A kernel-visible marker lets shutdown select desktop supervisors,
     * leaving nested/application guards and unrelated same-user work alone. */
    if (argc > 1 && !strcmp(argv[1], "--desktop")) { --argc; ++argv; }
    if (argc < 3 || !*argv[1] || getuid() == 0 || getuid() != geteuid() || getgid() != getegid()) {
        fprintf(stderr, "Usage (as the session user): session-guard [--desktop] milliseconds program [args...]\n");
        return 2;
    }
    errno = 0;
    long duration = strtol(argv[1], &end, 10);
    if (errno || *end || duration < 0 || duration > 86400000) return 2;
    const char *stop_file = getenv("XIRI_SESSION_STOP_FILE");
    const char *save_env = getenv("XIRI_SESSION_SAVE");
    char *save_program = save_env ? strdup(save_env) : NULL;
    if ((save_env && !save_program) || unsetenv("XIRI_SESSION_SAVE")) return 2;
    /* Only this desktop guard owns the save hook. A nested guard used for
     * one terminal/application must not end or save the entire desktop. */
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = stop; sigemptyset(&sa.sa_mask);
    for (int i = 0, signals[] = {SIGINT, SIGTERM, SIGHUP}; i < 3; ++i)
        if (sigaction(signals[i], &sa, NULL)) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    int kq = kqueue();
    struct kevent change;
    EV_SET(&change, getpid(), EVFILT_PROC, EV_ADD, NOTE_TRACK | NOTE_EXIT, 0, NULL);
    if (kq < 0 || kevent(kq, &change, 1, NULL, 0, NULL)) { perror("register descendants"); return 2; }
    pid_t leader = fork();
    if (leader < 0) { perror("fork"); close(kq); return 2; }
    if (!leader) {
        close(kq);
        if (setsid() < 0) { perror("setsid"); _exit(125); }
        execvp(argv[2], argv + 2);
        perror("session exec"); _exit(126);
    }
    int status = 0, finished = 0, failed = 0, phase = 0, final_check = 0;
    long long start = now(), deadline = duration ? start + duration : LLONG_MAX;
    long long stopping = 0;
    pid_t saver = -1;
    long long saving_since = 0;
    const char *reason = "leader-exit";
    for (;;) {
        failed |= events(kq);
        if (!final_check) failed |= identify(kq);
        if (!finished) {
            pid_t done = waitpid(leader, &status, WNOHANG);
            if (done == leader) finished = 1;
            else if (done < 0 && errno != EINTR) failed = 1;
        }
        if (finished && alive == 0) break;
        if (final_check) {
            report_remaining(kq, leader, finished);
            failed = 1;
            break;
        }
        if (!phase && (failed || requested || finished || now() >= deadline ||
                      (stop_file && access(stop_file, F_OK) == 0))) {
            reason = failed ? "tracking-error" : requested ? "signal" : finished ? "leader-exit" :
                     now() >= deadline ? "timeout" : "logout";
            phase = 1; stopping = now();
            /* Let the window manager save while its clients still exist.
             * The helper and its descendants are tracked by this same guard.
             * Keep draining events, and retain a bounded cleanup path even
             * when the X server or an application does not respond. */
            if (!failed && !finished && save_program && *save_program == '/') {
                saver = fork();
                if (saver == 0) {
                    close(kq);
                    execl(save_program, save_program, (char *)NULL);
                    perror("session save exec"); _exit(126);
                }
                if (saver > 0) { phase = -1; saving_since = now(); }
                else perror("session save fork");
            }
        }
        if (phase == -1) {
            int saved_status = 0;
            pid_t done = waitpid(saver, &saved_status, WNOHANG);
            if (done == saver || (done < 0 && errno != EINTR) || failed ||
                now() - saving_since >= 15000) {
                printf("SESSION_SAVE completed=%d exit=%d elapsed=%lld\n", done == saver,
                    done == saver && WIFEXITED(saved_status) ? WEXITSTATUS(saved_status) : -1,
                    now() - saving_since);
                phase = 1; stopping = now();
            }
        }
        if (phase > 0) {
            if (now() - stopping >= 1000) phase = 2;
            failed |= signal_members(phase == 1 ? SIGTERM : SIGKILL);
            if (now() - stopping >= 6000) {
                /* Signals/sysctls or scheduling can consume the remaining
                 * grace period after this iteration's event drain. Check
                 * already queued exits and reap once more before declaring
                 * failure. This adds neither a wait nor another signal. */
                final_check = 1;
                continue;
            }
        }
        struct timespec pause = {0, 20000000};
        nanosleep(&pause, NULL);
    }
    printf("GUARD pid=%d exit=%d signal=%d stopped=%d absent=%d valid=%d tracked=%zu remaining=%zu reason=%s uid=%u gid=%u elapsed=%lld\n",
        leader, finished && WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        finished && WIFSIGNALED(status) ? WTERMSIG(status) : 0, phase != 0,
        alive == 0, !failed, total, alive, reason, (unsigned)getuid(), (unsigned)getgid(), now()-start);
    close(kq); free(members); free(save_program);
    if (failed || alive) return 2;
    if (strcmp(reason, "leader-exit")) return 0;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
