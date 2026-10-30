/* Observe execve directly: shells may interpret ENOEXEC files as scripts. */
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
run(const char *path, int reject)
{
    int out[2], err[2], status = 0, exec_error = 0;
    char output[256];
    if (pipe(out) || pipe(err) || fcntl(err[1], F_SETFD, FD_CLOEXEC) < 0) {
        perror("pipe/fcntl"); return 1;
    }
    pid_t pid = fork();
    if (pid < 0) { perror("fork"); return 1; }
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
    int finished = 0;
    for (int i = 0; i < 200; i++) {
        pid_t got = waitpid(pid, &status, WNOHANG);
        if (got == pid) { finished = 1; break; }
        if (got < 0 && errno != EINTR) break;
        nanosleep(&delay, NULL);
    }
    if (!finished) {
        kill(pid, SIGKILL); waitpid(pid, &status, 0);
        fprintf(stderr, "TIMEOUT %s\n", path);
        close(out[0]); close(err[0]); return 1;
    }
    ssize_t ne = read(err[0], &exec_error, sizeof(exec_error));
    ssize_t no = read(out[0], output, sizeof(output));
    close(out[0]); close(err[0]);
    printf("EXEC %s errno_bytes=%zd errno=%d output_bytes=%zd exit=%d signal=%d\n",
        path, ne, exec_error, no, WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    if (reject)
        return !(ne == (ssize_t)sizeof(exec_error) && exec_error == ENOEXEC && no == 0 &&
            WIFEXITED(status) && WEXITSTATUS(status) == 126);
    const char expected[] = "XIRI_ABI_PROBE\n";
    return !(ne == 0 && no == (ssize_t)sizeof(expected)-1 &&
        memcmp(output, expected, sizeof(expected)-1) == 0 &&
        WIFEXITED(status) && WEXITSTATUS(status) == 37);
}

int
main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "usage: %s native irix-marked irix-unbranded\n", argv[0]);
        return 2;
    }
    int failed = run(argv[1], 0);
    failed |= run(argv[2], 1);
    failed |= run(argv[3], 1);
    puts(failed ? "BASELINE_FAIL" : "BASELINE_PASS native=works irix=ENOEXEC");
    return failed ? 1 : 0;
}
