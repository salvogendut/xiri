/* Native foreground control launched by the original interactive IRIX shell. */
#include <sys/types.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static volatile sig_atomic_t received;
static void caught(int number) { received = number; }

int main(int argc, char **argv)
{
    sigset_t blocked, previous;
    struct sigaction action = { .sa_handler = caught };
    if (argc != 2) return 2;
    int fd = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) return 3;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGINT);
    sigaddset(&blocked, SIGALRM);
    if (sigprocmask(SIG_BLOCK, &blocked, &previous) ||
        sigaction(SIGINT, &action, NULL) || sigaction(SIGALRM, &action, NULL)) return 4;
    int foreground = getpgrp() == tcgetpgrp(STDIN_FILENO);
    dprintf(fd, "READY pid=%ld pgid=%ld tpgid=%ld foreground=%d\n",
        (long)getpid(), (long)getpgrp(), (long)tcgetpgrp(STDIN_FILENO), foreground);
    alarm(60);
    while (!received) sigsuspend(&previous);
    alarm(0);
    dprintf(fd, "DONE signal=%d SIGINT=%d\n", (int)received, received == SIGINT);
    close(fd);
    return foreground && received == SIGINT ? 0 : 5;
}
