/* Direct exec observations for the synthetic o32 experiment. */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int
run(const char *path, const char *expect)
{
    int out[2], err[2], status = 0, exec_error = 0, finished = 0, killed = 0;
    char output[256];
    if (pipe(out) || pipe(err) || fcntl(err[1], F_SETFD, FD_CLOEXEC) < 0) {
        perror("pipe/fcntl"); exit(2);
    }
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); exit(2); }
    if (pid == 0) {
        char *const argv[] = { (char *)path, NULL };
        char *const envp[] = { NULL };
        close(out[0]); close(err[0]);
        if (dup2(out[1], STDOUT_FILENO) < 0) _exit(125);
        close(out[1]);
        execve(path, argv, envp);
        exec_error = errno;
        if (write(err[1], &exec_error, sizeof(exec_error)) != (ssize_t)sizeof(exec_error)) _exit(124);
        _exit(126);
    }
    close(out[1]); close(err[1]);
    struct timespec delay = { .tv_sec = 0, .tv_nsec = 100000000 };
    int limit = strcmp(expect, "timeout") == 0 ? 30 : 200;
    for (int i = 0; i < limit; i++) {
        pid_t got = waitpid(pid, &status, WNOHANG);
        if (got == pid) { finished = 1; break; }
        if (got < 0 && errno != EINTR) break;
        nanosleep(&delay, NULL);
    }
    if (!finished) {
        if (kill(pid, SIGKILL) != 0) { perror("kill"); exit(2); }
        while (waitpid(pid, &status, 0) < 0) {
            if (errno != EINTR) { perror("waitpid"); exit(2); }
        }
        killed = 1;
    }
    ssize_t ne = read(err[0], &exec_error, sizeof(exec_error));
    ssize_t no = read(out[0], output, sizeof(output));
    close(out[0]); close(err[0]);
    const char expected[] = "XIRI_ABI_PROBE\n";
    int pass = 0;
    if (strcmp(expect, "reject") == 0)
        pass = !killed && ne == (ssize_t)sizeof(exec_error) && exec_error == ENOEXEC && no == 0 &&
            WIFEXITED(status) && WEXITSTATUS(status) == 126;
    else if (strcmp(expect, "timeout") == 0)
        pass = killed && ne == 0 && no == 0 && WIFSIGNALED(status) && WTERMSIG(status) == SIGKILL;
    else if (strcmp(expect, "signal") == 0)
        pass = !killed && ne == 0 && no == 0 && WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV;
    else if (strcmp(expect, "quiet") == 0 || strcmp(expect, "output") == 0)
        pass = !killed && ne == 0 && WIFEXITED(status) && WEXITSTATUS(status) == 37 &&
            (strcmp(expect, "quiet") == 0 ? no == 0 :
             no == (ssize_t)sizeof(expected)-1 && memcmp(output, expected, sizeof(expected)-1) == 0);
    printf("CASE %s expect=%s errno_bytes=%zd errno=%d output_bytes=%zd exit=%d signal=%d killed=%d %s\n",
        path, expect, ne, exec_error, no, WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        WIFSIGNALED(status) ? WTERMSIG(status) : 0, killed, pass ? "PASS" : "FAIL");
    fflush(stdout);
    return !pass;
}

int
main(int argc, char **argv)
{
    if (argc != 2) { fprintf(stderr, "usage: %s cases.txt\n", argv[0]); return 2; }
    FILE *cases = fopen(argv[1], "r");
    if (!cases) { perror("cases"); return 2; }
    char line[128], path[64], expect[16];
    int failed = 0, count = 0;
    while (fgets(line, sizeof(line), cases)) {
        if (sscanf(line, "%63s %15s", path, expect) != 2) { fclose(cases); return 2; }
        failed |= run(path, expect);
        count++;
    }
    if (ferror(cases)) failed = 1;
    fclose(cases);
    if (!count) failed = 1;
    printf("EXPERIMENT_%s cases=%d\n", failed ? "FAIL" : "PASS", count);
    return failed ? 1 : 0;
}
