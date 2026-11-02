/* Measure FAM execution events using two overlapping instances of sleep. */
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fam.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static long long milliseconds(void)
{
    struct timeval t;
    if (gettimeofday(&t, NULL)) exit(2);
    return (long long)t.tv_sec * 1000 + t.tv_usec / 1000;
}

static void drain(FAMConnection *fc, const char *phase)
{
    long long end = milliseconds() + 2200;
    printf("PHASE %s\n", phase); fflush(stdout);
    while (milliseconds() < end) {
        while (FAMPending(fc)) {
            FAMEvent e;
            if (FAMNextEvent(fc, &e) < 0) exit(3);
            printf("EVENT code=%d request=%d path=%s\n", e.code,
                e.fr.reqnum, e.filename); fflush(stdout);
        }
        struct timeval timeout;
        fd_set fds;
        timeout.tv_sec = 0; timeout.tv_usec = 100000;
        FD_ZERO(&fds); FD_SET(FAMCONNECTION_GETFD(fc), &fds);
        if (select(FAMCONNECTION_GETFD(fc)+1, &fds, NULL, NULL,
                &timeout) < 0 && errno != EINTR) exit(4);
    }
}

static pid_t start(const char *path)
{
    pid_t pid = fork();
    if (pid < 0) exit(5);
    if (!pid) { execl(path, path, "30", (char *)NULL); _exit(126); }
    return pid;
}

static void stop(pid_t pid)
{
    int status;
    if (kill(pid, SIGTERM) || waitpid(pid, &status, 0) != pid) exit(6);
    if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGTERM) exit(7);
}

int main(int argc, char **argv)
{
    FAMConnection fc;
    FAMRequest first, late;
    pid_t one, two;
    if (argc != 2 && argc != 3) return 2;
    const char *executable = argc == 3 ? argv[2] : argv[1];
    alarm(30);
    if (FAMOpen(&fc) || FAMMonitorFile(&fc, argv[1], &first, NULL)) return 8;
    drain(&fc, "initial");
    one = start(executable); drain(&fc, "first-start");
    if (FAMMonitorFile(&fc, argv[1], &late, NULL)) return 9;
    drain(&fc, "subscribe-running");
    two = start(executable); drain(&fc, "second-start");
    stop(one); drain(&fc, "first-stop");
    stop(two); drain(&fc, "last-stop");
    if (FAMCancelMonitor(&fc, &late) || FAMCancelMonitor(&fc, &first)) return 10;
    drain(&fc, "cancel");
    if (FAMClose(&fc)) return 11;
    return 0;
}
