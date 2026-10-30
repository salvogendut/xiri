/* Direct exec observations for the synthetic o32 experiment. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* Fixed high descriptors keep these pipes clear of the exec-status pipe. */
static void
prepare_pipes(void)
{
    int p[2], q[2], w[2];
    char buffer[8192] = { 0 };
    ssize_t n;
    if (pipe(p) || write(p[1], "short", 5) != 5 || close(p[1]) ||
        dup2(p[0], 50) < 0 || close(p[0])) _exit(125);
    if (pipe(q) || fcntl(q[0], F_SETFL, O_NONBLOCK) < 0 ||
        dup2(q[0], 51) < 0 || dup2(q[1], 52) < 0) _exit(125);
    close(q[0]); close(q[1]);
    if (pipe(w) || fcntl(w[1], F_SETFL, O_NONBLOCK) < 0) _exit(125);
    while ((n = write(w[1], buffer, 4096)) > 0) {}
    if (n != -1 || errno != EAGAIN || read(w[0], buffer, sizeof(buffer)) != (ssize_t)sizeof(buffer) ||
        dup2(w[1], 53) < 0 || dup2(w[0], 54) < 0) _exit(125);
    close(w[0]); close(w[1]);
}

static int
verify_created_file(void)
{
    char data[16];
    struct stat st;
    int fd = open("xiri-created", O_RDONLY);
    if (fd < 0) return 0;
    ssize_t n = read(fd, data, sizeof(data));
    int pass = n == 6 && memcmp(data, "saved\n", 6) == 0 &&
        fstat(fd, &st) == 0 && S_ISREG(st.st_mode) && (st.st_mode & 07777) == 0640;
    close(fd);
    return pass;
}

static int
run(const char *path, const char *expect)
{
    int out[2], err[2], status = 0, exec_error = 0, finished = 0, killed = 0;
    char output[256];
    if (strcmp(path, "./irix-files") == 0 && unlink("xiri-created") < 0 && errno != ENOENT) {
        perror("unlink fixture output"); return 1;
    }
    if (pipe(out) || pipe(err) || fcntl(err[1], F_SETFD, FD_CLOEXEC) < 0) {
        perror("pipe/fcntl"); exit(2);
    }
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); exit(2); }
    if (pid == 0) {
        char *const simple_argv[] = { (char *)path, NULL };
        char *const full_argv[] = { "fixture", "alpha beta", "", "tail", NULL };
        char *const full_env[] = { "XIRI_ONE=alpha beta", "XIRI_EMPTY=", NULL };
        char *const empty[] = { NULL };
        char *const *argv = simple_argv;
        char *const *envp = empty;
        if (strcmp(path, "./irix-args") == 0) { argv = full_argv; envp = full_env; }
        if (strcmp(path, "./irix-args-empty") == 0) argv = empty;
        close(out[0]); close(err[0]);
        if (dup2(out[1], STDOUT_FILENO) < 0) _exit(125);
        close(out[1]);
        umask(022);
        if (strcmp(path, "./irix-partial") == 0) prepare_pipes();
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
    else if (strcmp(expect, "signal") == 0 || strcmp(expect, "fault-output") == 0)
        pass = !killed && ne == 0 && WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV &&
            (strcmp(expect, "signal") == 0 ? no == 0 :
             no == (ssize_t)sizeof(expected)-1 && memcmp(output, expected, sizeof(expected)-1) == 0);
    else if (strcmp(expect, "quiet") == 0 || strcmp(expect, "output") == 0)
        pass = !killed && ne == 0 && WIFEXITED(status) && WEXITSTATUS(status) == 37 &&
            (strcmp(expect, "quiet") == 0 ? no == 0 :
             no == (ssize_t)sizeof(expected)-1 && memcmp(output, expected, sizeof(expected)-1) == 0);
    if (pass && strcmp(path, "./irix-files") == 0 && strcmp(expect, "quiet") == 0)
        pass = verify_created_file();
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
