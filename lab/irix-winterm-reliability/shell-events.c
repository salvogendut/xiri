/* Original libc-level child notification and PTY EOF observations. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char *_getpty(int *, int, mode_t, int);
static volatile sig_atomic_t notices;
static void notice(int sig) { (void)sig; notices++; }
static void state(const char *label)
{
    struct sigaction action;
    int rc, error;
    memset(&action, 0, sizeof(action));
    errno = 0; rc = sigaction(SIGCHLD, NULL, &action); error = errno;
    printf("ACTION %s rc=%d errno=%d flags=%#x handler=%s\n", label,
        rc, error, action.sa_flags, action.sa_handler == notice ? "fixture" : "other");
}
static void read_master(const char *label, int fd)
{
    unsigned char byte = 0xa5;
    int rc, error;
    errno = 0; rc = read(fd, &byte, 1); error = errno;
    printf("READ %s rc=%d errno=%d byte=%02x\n", label, rc, error, byte);
}
int main(int argc, char **argv)
{
    int master, slave, rc, error, status = 0, i;
    pid_t child, got;
    char *path;
    void (*old)(int);
    if (argc == 2 && !strcmp(argv[1], "user") &&
        (setgid(1234) || setuid(1234))) return 2;
    printf("IDENTITY uid=%lu abi=%d NOCLDSTOP=%#x NOCLDWAIT=%#x\n",
        (unsigned long)getuid(), _MIPS_SIM, SA_NOCLDSTOP, SA_NOCLDWAIT);
    state("initial");
    errno = 0; old = signal(SIGCHLD, notice); error = errno;
    printf("SIGNAL success=%d errno=%d\n", old != SIG_ERR, error);
    state("after-signal");
    child = fork();
    if (child < 0) return 3;
    if (!child) _exit(37);
    got = 0;
    for (i = 0; i < 100 && got == 0; i++) {
        usleep(10000);
        errno = 0; got = waitpid(child, &status, WNOHANG); error = errno;
    }
    printf("CHILD notices=%d reaped=%d errno=%d exited=%d status=%d\n",
        (int)notices, got == child, error, WIFEXITED(status), WEXITSTATUS(status));
    if (got != child) { kill(child, SIGKILL); waitpid(child, NULL, 0); }
    path = _getpty(&master, O_RDWR | O_NONBLOCK, 0600, 0);
    if (!path) return 4;
    read_master("before-slave", master);
    slave = open(path, O_RDWR | O_NOCTTY);
    if (slave < 0) return 5;
    read_master("slave-open", master);
    if (write(slave, "Q", 1) != 1) return 6;
    usleep(10000);
    read_master("data", master);
    close(slave);
    read_master("slave-closed", master);
    errno = 0; rc = write(master, "Z", 1); error = errno;
    printf("WRITE slave-closed rc=%d errno=%d\n", rc, error);
    close(master);
    return 0;
}
