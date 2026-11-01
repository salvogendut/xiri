/* Disposable-guest supervisor. UID 1234 is reserved for this one job.
 * Drop all privilege before fork, so cleanup cannot signal other identities.
 * Native kill(-1) excludes its caller and checks each target's credentials.
 * This covers descendants that call setsid or outlive the launcher. */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define JOB_UID 1234
static pid_t seen[256];
static size_t nseen;

static long long now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int owned(int report)
{
    int mib[6] = {CTL_KERN, KERN_PROC2, KERN_PROC_ALL, 0,
        sizeof(struct kinfo_proc2), 0};
    struct kinfo_proc2 *p;
    size_t len = 0;
    int count = 0;
    if (sysctl(mib, 6, NULL, &len, NULL, 0)) return -1;
    len += 32 * sizeof(*p);
    p = malloc(len);
    if (!p) return -1;
    mib[5] = len / sizeof(*p);
    if (sysctl(mib, 6, p, &len, NULL, 0)) { free(p); return -1; }
    for (size_t i = 0; i < len / sizeof(*p); i++) {
        if (p[i].p_pid == getpid() ||
            (p[i].p_ruid != JOB_UID && p[i].p_uid != JOB_UID &&
             p[i].p_svuid != JOB_UID)) continue;
        count++;
        size_t j;
        for (j = 0; j < nseen; j++) if (seen[j] == p[i].p_pid) break;
        if (report && j == nseen) {
            if (nseen == sizeof(seen)/sizeof(seen[0])) { free(p); return -1; }
            seen[nseen++] = p[i].p_pid;
            printf("OWN pid=%d ppid=%d sid=%d pgid=%d tpgid=%d flags=%x comm=%s\n",
                p[i].p_pid, p[i].p_ppid, p[i].p_sid, p[i].p__pgid,
                p[i].p_tpgid, p[i].p_eflag, p[i].p_comm);
        }
    }
    free(p);
    return count;
}

int main(int argc, char **argv)
{
    int pipes[3][2], status = 0, finished = 0, killed = 0, failed = 0;
    unsigned char data[3][8192];
    size_t used[3] = {0}, total[3] = {0};
    char *end;
    if (argc < 3) return 2;
    long duration = strtol(argv[1], &end, 10);
    if (*end || duration < 100 || duration > 120000) return 2;
    if (owned(0) != 0) { fprintf(stderr, "reserved UID is occupied\n"); return 2; }
    if (setgroups(0, NULL) || setgid(JOB_UID) || setuid(JOB_UID) ||
        getuid() != JOB_UID || geteuid() != JOB_UID ||
        getgid() != JOB_UID || getegid() != JOB_UID || getgroups(0, NULL) != 0)
        return 2;
    for (int i = 0; i < 3; i++)
        if (pipe(pipes[i]) || fcntl(pipes[i][0], F_SETFL, O_NONBLOCK) < 0) return 2;
    if (fcntl(pipes[2][1], F_SETFD, FD_CLOEXEC) < 0) return 2;
    pid_t pid = fork();
    if (pid < 0) return 2;
    if (!pid) {
        int fd = open("/dev/null", O_RDONLY);
        if (fd < 0 || dup2(fd, 0) < 0 || dup2(pipes[0][1], 1) < 0 ||
            dup2(pipes[1][1], 2) < 0) _exit(125);
        for (int i = 3, limit = getdtablesize(); i < limit; i++)
            if (i != pipes[2][1]) close(i);
        execvp(argv[2], argv + 2);
        int e = errno;
        if (write(pipes[2][1], &e, sizeof(e)) != sizeof(e)) _exit(124);
        _exit(126);
    }
    struct pollfd pfd[3];
    for (int i = 0; i < 3; i++) {
        close(pipes[i][1]);
        pfd[i] = (struct pollfd){pipes[i][0], POLLIN, 0};
    }
    long long start = now(), deadline = start + duration;
    int remaining = -1;
    for (;;) {
        if (poll(pfd, 3, 20) < 0 && errno != EINTR) failed = 1;
        for (int i = 0; i < 3; i++) {
            unsigned char buf[512];
            ssize_t n;
            for (int j = 0; j < 16; j++) {
                n = read(pipes[i][0], buf, sizeof(buf));
                if (n <= 0) break;
                size_t take = (size_t)n < sizeof(data[i]) - used[i] ?
                    (size_t)n : sizeof(data[i]) - used[i];
                memcpy(data[i] + used[i], buf, take);
                used[i] += take; total[i] += n;
            }
        }
        if (!finished) {
            pid_t got = waitpid(pid, &status, WNOHANG);
            if (got == pid) finished = 1;
            else if (got < 0 && errno != EINTR) failed = 1;
        }
        remaining = owned(1);
        if (remaining < 0) failed = 1;
        if (finished && remaining == 0) break;
        if (!killed && (failed || now() >= deadline)) {
            if (kill(-1, SIGKILL) && errno != ESRCH) failed = 1;
            killed = 1; deadline = now() + 5000;
        } else if (killed && now() >= deadline) { failed = 1; break; }
        usleep(20000);
    }
    for (int i = 0; i < 3; i++) {
        unsigned char buf[512];
        ssize_t n;
        while ((n = read(pipes[i][0], buf, sizeof(buf))) > 0) {
            size_t take = (size_t)n < sizeof(data[i]) - used[i] ?
                (size_t)n : sizeof(data[i]) - used[i];
            memcpy(data[i] + used[i], buf, take);
            used[i] += take; total[i] += n;
        }
        close(pipes[i][0]);
    }
    int e = 0;
    if (used[2] == sizeof(e)) memcpy(&e, data[2], sizeof(e));
    printf("GUARD pid=%d exit=%d signal=%d killed=%d absent=%d valid=%d elapsed=%lld\n",
        pid, finished && WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        finished && WIFSIGNALED(status) ? WTERMSIG(status) : 0,
        killed, remaining == 0, !failed, now()-start);
    printf("EXEC bytes=%zu errno=%d\n", total[2], e);
    for (int i = 0; i < 2; i++) {
        printf("%s bytes=%zu hex=", i ? "STDERR" : "STDOUT", total[i]);
        for (size_t j = 0; j < used[i]; j++) printf("%02x", data[i][j]);
        putchar('\n');
    }
    return failed || remaining != 0 || total[0] > sizeof(data[0]) ||
        total[1] > sizeof(data[1]) || (total[2] && total[2] != sizeof(e)) ? 2 : 0;
}
