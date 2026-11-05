/* Native adversarial lifecycle fixtures; do not run outside the guest lab. */
#include <sys/types.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
/* One kernel snapshot: a process can disappear between kill(0) and ps. */
static int check_dead(pid_t pid)
{
    struct kinfo_proc2 p;
    int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, sizeof(p), 1};
    size_t size = sizeof(p);
    memset(&p, 0, sizeof(p));
    if (sysctl(mib, 6, &p, &size, NULL, 0)) { perror("postcheck sysctl"); return 2; }
    if (size == 0) return 0;
    if (size != sizeof(p) || p.p_pid != pid) return 2;
    return (p.p_realstat == SZOMB || p.p_realstat == SDYING || p.p_realstat == SDEAD) ? 0 : 1;
}

static int postcheck_control(void)
{
    int gate[2], status, rc = 2, reaped = 0;
    if (pipe(gate)) return 2;
    pid_t child = fork();
    if (child < 0) { close(gate[0]); close(gate[1]); return 2; }
    if (!child) {
        char c;
        close(gate[1]);
        if (read(gate[0], &c, 1) != 1) _exit(2);
        _exit(37);
    }
    close(gate[0]);
    /* A live child must fail the assertion.  Publish its exit only afterward. */
    int live = check_dead(child);
    if (live != 1 || write(gate[1], "x", 1) != 1) goto out;
    siginfo_t info;
    memset(&info, 0, sizeof(info));
    if (waitid(P_PID, child, &info, WEXITED | WNOWAIT) || info.si_status != 37) goto out;
    int zombie = check_dead(child);
    /* Force the real exit/reap race between the old assertion's two queries. */
    if (zombie || kill(child, 0) || waitpid(child, &status, 0) != child) goto out;
    reaped = 1;
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 37) goto out;
    int absent = check_dead(child);
    char command[128];
    snprintf(command, sizeof(command), "ps -p %d -o stat= | grep '^Z' >/dev/null", child);
    int old = system(command);
    int valid = !absent && WIFEXITED(old) && WEXITSTATUS(old) == 1;
    printf("PID_POSTCHECK_CONTROL live_rejected=%d zombie_accepted=%d absent_accepted=%d "
        "old_reaped_failed=%d valid=%d\n", live == 1, !zombie, !absent,
        WIFEXITED(old) && WEXITSTATUS(old) == 1, valid);
    rc = valid ? 0 : 1;
out:
    close(gate[1]);
    if (!reaped) {
        kill(child, SIGKILL);
        while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    }
    return rc;
}
static void hold(const char *file)
{
    signal(SIGTERM, SIG_IGN);
    FILE *f = fopen(file, "a");
    if (!f) _exit(3);
    fprintf(f, "%d\n", getpid()); fclose(f);
    for (;;) pause();
}
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    if (!strcmp(argv[1], "check-dead")) {
        char *end;
        errno = 0;
        long pid = strtol(argv[2], &end, 10);
        if (errno || !*argv[2] || *end || pid < 1 || pid > INT_MAX) return 2;
        int rc = check_dead((pid_t)pid);
        if (rc) fprintf(stderr, "PID_POSTCHECK_FAILED pid=%ld result=%d\n", pid, rc);
        return rc;
    }
    if (!strcmp(argv[1], "postcheck-control")) return postcheck_control();
    if (!strcmp(argv[1], "hold")) hold(argv[2]);
    if (!strcmp(argv[1], "live-burst")) {
        for (int i=0; i<24; ++i) {
            pid_t p=fork(); if (p<0) return 3;
            if (!p) hold(argv[2]);
        }
        hold(argv[2]);
    }
    if (!strcmp(argv[1], "burst")) {
        for (int i=0; i<24; ++i) {
            pid_t p=fork(); if (p<0) return 3;
            if (!p) { pid_t q=fork(); if (q<0) _exit(4); if (!q) _exit(0); _exit(0); }
        }
        while (wait(NULL)>0) {}
        return 0;
    }
    if (!strcmp(argv[1], "escape") || !strcmp(argv[1], "fail")) {
        int gate[2]; if (pipe(gate)) return 3;
        pid_t p=fork(); if (p<0) return 3;
        if (!p) {
            close(gate[0]);
            if (setsid()<0) _exit(4);
            pid_t q=fork(); if (q<0) _exit(5);
            if (q) _exit(0);
            signal(SIGTERM,SIG_IGN);
            FILE *f=fopen(argv[2],"a"); if(!f) _exit(6);
            fprintf(f,"%d\n",getpid()); fclose(f);
            if (write(gate[1],"x",1)!=1) _exit(7);
            close(gate[1]); for (;;) pause();
        }
        close(gate[1]); char c;
        if (read(gate[0],&c,1)!=1) return 8;
        close(gate[0]); waitpid(p,NULL,0);
        if (!strcmp(argv[1],"fail")) return 7;
        hold(argv[2]);
    }
    return 2;
}
