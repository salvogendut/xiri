/* Native-only isolation of controlling-terminal teardown through nullfs.
 * mode 0 uses /dev/pts; mode 1 probes the compatibility alias directly;
 * mode 2 reopens the native device before acquiring the controlling tty. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <util.h>
int main(int argc, char **argv)
{
    int master, status, mode, ready[2];
    char native[128], alias[160];
    if (argc != 2 || (mode = atoi(argv[1])) < 0 || mode > 2) return 2;
    master = open("/emul/irix/dev/ptc", O_RDWR | O_NOCTTY);
    if (master < 0) return 2;
    char *name = ptsname(master);
    if (!name || strlen(name) >= sizeof(native)) return 2;
    strcpy(native, name);
    if (strncmp(native, "/dev/pts/", 9)) return 2;
    snprintf(alias, sizeof(alias), "/emul/irix%s", native);
    if (pipe(ready)) return 2;
    pid_t pid = fork();
    if (pid < 0) return 2;
    if (!pid) {
        close(ready[0]);
        close(master);
        if (setsid() < 0) _exit(3);
        int fd = open(mode ? alias : native, O_RDWR | O_NOCTTY);
        if (fd < 0) _exit(4);
        if (mode == 2) {
            int direct = open(native, O_RDWR | O_NOCTTY);
            struct stat a, b;
            if (direct < 0 || fstat(fd, &a) || fstat(direct, &b) ||
                !S_ISCHR(a.st_mode) || !S_ISCHR(b.st_mode) ||
                a.st_rdev != b.st_rdev) _exit(5);
            close(fd); fd = direct;
        }
        if (ioctl(fd, TIOCSCTTY, NULL)) _exit(6);
        printf("NATIVE_CTTY mode=%d pid=%d tty=%s acquired=1\n", mode, getpid(), native);
        fflush(stdout);
        if (write(ready[1], "R", 1) != 1) _exit(7);
        sleep(1);
        _exit(37);
    }
    close(ready[1]);
    char byte;
    if (read(ready[0], &byte, 1) != 1) return 2;
    close(master);
    if (waitpid(pid, &status, 0) != pid) return 2;
    printf("NATIVE_CTTY mode=%d exit=%d signal=%d\n", mode,
        WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    return !(WIFSIGNALED(status) && WTERMSIG(status) == SIGHUP);
}
