/* Native parent verifies the standard exec module's busy-unload guard. */
#include <sys/types.h>
#include <sys/module.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int
main(int argc, char **argv)
{
    int input[2], ack[2], status, error = 0;
    pid_t child;
    if (argc != 2 || pipe(input) || pipe(ack) ||
        fcntl(ack[1], F_SETFD, FD_CLOEXEC) == -1)
        return 2;
    /* Bound both the parent and its child, including error paths. */
    alarm(40);
    child = fork();
    if (child == -1) return 2;
    if (child == 0) {
        char *const av[] = {argv[1], NULL};
        char *const ev[] = {NULL};
        alarm(30);
        close(input[1]); close(ack[0]);
        if (dup2(input[0], STDIN_FILENO) == -1) _exit(125);
        close(input[0]);
        execve(argv[1], av, ev);
        error = errno;
        (void)write(ack[1], &error, sizeof(error));
        _exit(126);
    }
    close(input[0]); close(ack[1]);
    /* EOF on the close-on-exec pipe proves the foreign exec succeeded. */
    ssize_t n = read(ack[0], &error, sizeof(error));
    close(ack[0]);
    int failed = n != 0 || waitpid(child, &status, WNOHANG) != 0;
    if (!failed) {
        errno = 0;
        int result = modctl(MODCTL_UNLOAD, "compat_irix_o32");
        error = errno;
        printf("BUSY result=%d errno=%d\n", result, error);
        failed = result != -1 || error != EBUSY;
    }
    if (!failed && write(input[1], " XIRI_MODULE_BUSY_OK\n", 21) != 21)
        failed = 1;
    close(input[1]);
    if (failed) (void)kill(child, SIGKILL);
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) ||
        WEXITSTATUS(status) != 0) failed = 1;
    if (!failed) {
        errno = 0;
        int result = modctl(MODCTL_UNLOAD, "compat_irix_o32");
        error = errno;
        printf("IDLE result=%d errno=%d\n", result, error);
        failed = result != 0;
    }
    return failed ? 1 : 0;
}
