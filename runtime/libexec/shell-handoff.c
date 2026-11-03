/* Explicit native policy at the IRIX terminal -> NetBSD shell boundary.
 * The native tty layer owns controlling-terminal and foreground-group setup.
 * This is not an implementation of foreign termios or signal frames. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
extern char **environ;
int main(int argc, char **argv)
{
    if (argc != 2 || !isatty(0) || !isatty(1) || !isatty(2)) return 125;
    /* Native session teardown must own the native ptyfs vnode. A controlling
     * tty through the nullfs compatibility view can panic on revoke. Reopen
     * the same native device while the inherited descriptors still hold it,
     * verify its identity, and replace all three before acquiring the ctty. */
    char path[128];
    struct stat inherited, direct;
    if (ttyname_r(0, path, sizeof(path)) || strncmp(path, "/dev/pts/", 9) ||
        !path[9] || strspn(path + 9, "0123456789") != strlen(path + 9) ||
        fstat(0, &inherited) || !S_ISCHR(inherited.st_mode)) return 125;
    for (int i = 1; i < 3; i++) {
        if (fstat(i, &direct) || !S_ISCHR(direct.st_mode) ||
            inherited.st_rdev != direct.st_rdev) return 125;
    }
    int fd = open(path, O_RDWR | O_NOCTTY);
    if (fd < 0 || fstat(fd, &direct) || !S_ISCHR(direct.st_mode) ||
        inherited.st_rdev != direct.st_rdev) return 125;
    for (int i = 0; i < 3; i++) if (dup2(fd, i) < 0) return 125;
    close(fd);
    if (ioctl(0, TIOCSCTTY, NULL) || tcsetpgrp(0, getpgrp())) {
        perror("native controlling terminal"); return 125;
    }
    struct winsize ws = {24, 80, 0, 0};
    if (ioctl(0, TIOCSWINSZ, &ws)) { perror("native window size"); return 125; }
    FILE *out = fopen(argv[1], "wx");
    if (!out) { perror("native handoff report"); return 125; }
    fprintf(out, "NATIVE_HANDOFF pid=%d sid=%d pgid=%d tpgid=%d uid=%d euid=%d gid=%d egid=%d groups=%d tty=%s rows=%d cols=%d\n",
        getpid(), getsid(0), getpgrp(), tcgetpgrp(0), getuid(), geteuid(),
        getgid(), getegid(), getgroups(0, NULL), ttyname(0), ws.ws_row, ws.ws_col);
    if (fclose(out)) return 125;
    char *const av[] = {"sh", "-i", NULL};
    execve("/bin/sh", av, environ);
    perror("native shell exec");
    return 126;
}
