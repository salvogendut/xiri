/* Native parent: bounded direct exec, separate stdout/stderr/exec-error pipes. */
#include <sys/types.h>
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

#ifndef RUNNER_TIMEOUT_MS
#define RUNNER_TIMEOUT_MS 5000
#endif

static long long
milliseconds(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

int
main(int argc, char **argv)
{
    int pipes[3][2], status = 0, finished = 0, killed = 0;
    unsigned char data[3][4096];
    size_t used[3] = {0}, total[3] = {0};
    unsigned long ids[4] = {0};
    int with_ids = argc >= 6;
    int with_args = argc >= 7 && strcmp(argv[6], "--") == 0;
    if (argc != 2 && argc != 6 && !with_args) return 2;
    if (with_ids) {
        for (int i = 0; i < 4; i++) {
            char *end;
            errno = 0;
            ids[i] = strtoul(argv[i + 2], &end, 10);
            if (errno || *end || !*argv[i + 2] || ids[i] > 65534) return 2;
        }
    }
    for (int i = 0; i < 3; i++) {
        if (pipe(pipes[i]) || fcntl(pipes[i][0], F_SETFL, O_NONBLOCK) < 0) return 2;
    }
    if (fcntl(pipes[2][1], F_SETFD, FD_CLOEXEC) < 0) return 2;
    pid_t pid = fork();
    if (pid < 0) return 2;
    if (pid == 0) {
        if (setpgid(0, 0)) _exit(125);
        char **av = calloc((size_t)argc + 1, sizeof(*av));
        if (av == NULL) _exit(123);
        av[0] = argv[1];
        if (with_args)
            for (int i = 7; i < argc; i++) av[i - 6] = argv[i];
        char *const ev[] = {NULL};
        int fd = open("input.txt", O_RDONLY);
        if (fd < 0 || dup2(fd, 0) < 0) _exit(125);
        close(fd);
        for (int i = 0; i < 3; i++) close(pipes[i][0]);
        if (dup2(pipes[0][1], 1) < 0 || dup2(pipes[1][1], 2) < 0) _exit(125);
        close(pipes[0][1]); close(pipes[1][1]);
        /* Native setup lets the foreign identity calls report independently
         * chosen real/effective IDs, without adding foreign credential setters. */
        if (with_ids && (setgroups(0, NULL) ||
            setregid((gid_t)ids[2], (gid_t)ids[3]) ||
            setreuid((uid_t)ids[0], (uid_t)ids[1]))) _exit(125);
        execve(argv[1], av, ev);
        int e = errno;
        if (write(pipes[2][1], &e, sizeof(e)) != sizeof(e)) _exit(124);
        _exit(126);
    }
    if (setpgid(pid, pid) && errno != EACCES && errno != ESRCH) return 2;
    struct pollfd pfd[3];
    for (int i = 0; i < 3; i++) {
        close(pipes[i][1]);
        pfd[i] = (struct pollfd){pipes[i][0], POLLIN, 0};
    }
    long long started = milliseconds();
    long long deadline = started + RUNNER_TIMEOUT_MS;
    while (!finished) {
        if (poll(pfd, 3, 20) < 0 && errno != EINTR) return 2;
        for (int i = 0; i < 3; i++) {
            unsigned char buffer[512];
            ssize_t n;
            /* Bounded draining keeps a writing child from defeating timeout. */
            for (int j = 0; j < 16; j++) {
                n = read(pipes[i][0], buffer, sizeof(buffer));
                if (n <= 0) break;
                size_t take = (size_t)n < sizeof(data[i]) - used[i] ?
                    (size_t)n : sizeof(data[i]) - used[i];
                memcpy(data[i] + used[i], buffer, take);
                used[i] += take; total[i] += (size_t)n;
            }
        }
        pid_t got = waitpid(pid, &status, WNOHANG);
        if (got == pid) finished = 1;
        else if (got < 0 && errno != EINTR) return 2;
        else if (!killed && milliseconds() >= deadline) {
            if (kill(pid, SIGKILL)) return 2;
            killed = 1;
        }
    }
    /* Own the complete inherited process group, including foreign fork children. */
    if (kill(-pid, SIGKILL) && errno != ESRCH) return 2;
    long long cleanup_deadline = milliseconds() + 5000;
    int group_absent = 0;
    do {
        if (kill(-pid, 0) < 0 && errno == ESRCH) { group_absent = 1; break; }
        poll(NULL, 0, 10);
    } while (milliseconds() < cleanup_deadline);
    /* All owned writers are stopped; collect the final bytes. */
    for (int i = 0; i < 3; i++) {
        unsigned char buffer[512];
        ssize_t n;
        while ((n = read(pipes[i][0], buffer, sizeof(buffer))) > 0) {
            size_t take = (size_t)n < sizeof(data[i]) - used[i] ?
                (size_t)n : sizeof(data[i]) - used[i];
            memcpy(data[i] + used[i], buffer, take);
            used[i] += take; total[i] += (size_t)n;
        }
        close(pipes[i][0]);
    }
    int exec_error = 0;
    if (used[2] == sizeof(exec_error)) memcpy(&exec_error, data[2], sizeof(exec_error));
    printf("OBS path=%s errno_bytes=%zu errno=%d exit=%d signal=%d killed=%d\n",
        argv[1], total[2], exec_error, WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        WIFSIGNALED(status) ? WTERMSIG(status) : 0, killed);
    for (int i = 0; i < 2; i++) {
        printf("%s bytes=%zu hex=", i == 0 ? "STDOUT" : "STDERR", total[i]);
        for (size_t j = 0; j < used[i]; j++) printf("%02x", data[i][j]);
        putchar('\n');
    }
    printf("GROUP absent=%d\n", group_absent);
#ifdef RUNNER_TIMING
    printf("ELAPSED_MS %lld\n", milliseconds() - started);
#endif
    return !group_absent || total[0] > sizeof(data[0]) || total[1] > sizeof(data[1]) ||
        (total[2] != 0 && total[2] != sizeof(exec_error)) ? 2 : 0;
}
