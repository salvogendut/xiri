/* Explicit native policy at the IRIX terminal -> NetBSD shell boundary.
 * The native tty layer owns controlling-terminal and foreground-group setup.
 * This is not an implementation of foreign termios or signal frames. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
extern char **environ;
int main(int argc, char **argv)
{
    if ((argc != 1 && argc != 2) || !isatty(0) || !isatty(1) || !isatty(2)) return 125;
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
    struct winsize ws;
    if (ioctl(0, TIOCGWINSZ, &ws)) { perror("native window size"); return 125; }
    /* Preserve dimensions set by the terminal before exec. Use a fallback
     * only for dimensions that the terminal has not initialized. */
    if (!ws.ws_row || !ws.ws_col) {
        if (!ws.ws_row) ws.ws_row = 24;
        if (!ws.ws_col) ws.ws_col = 80;
        if (ioctl(0, TIOCSWINSZ, &ws)) { perror("native window size"); return 125; }
    }
    /* WM_COMMAND is saved by 4Dwm. Keep the normal invocation independent of
     * an old login's temporary directory, and give each restored terminal a
     * separate report in the current session. Explicit paths remain useful
     * for standalone terminal probes. */
    char report[PATH_MAX], first[PATH_MAX];
    FILE *out;
    if (argc == 2) {
        out = fopen(argv[1], "wx");
    } else {
        const char *job = getenv("XIRI_SESSION_DIR");
        if (!job || *job != '/' ||
            snprintf(report, sizeof(report), "%s/terminal.XXXXXX", job) >= (int)sizeof(report) ||
            snprintf(first, sizeof(first), "%s/handoff", job) >= (int)sizeof(first)) return 125;
        int report_fd = mkstemp(report);
        if (report_fd < 0) { perror("native handoff report"); return 125; }
        out = fdopen(report_fd, "w");
        if (!out) { close(report_fd); unlink(report); return 125; }
    }
    if (!out) { perror("native handoff report"); return 125; }
    fprintf(out, "NATIVE_HANDOFF pid=%d sid=%d pgid=%d tpgid=%d uid=%d euid=%d gid=%d egid=%d groups=%d tty=%s rows=%d cols=%d\n",
        getpid(), getsid(0), getpgrp(), tcgetpgrp(0), getuid(), geteuid(),
        getgid(), getegid(), getgroups(0, NULL), ttyname(0), ws.ws_row, ws.ws_col);
    if (fclose(out)) return 125;
    if (argc == 1 && link(report, first) && errno != EEXIST) {
        perror("first native handoff report"); return 125;
    }
    char *const av[] = {"sh", "-i", NULL};
    execve("/bin/sh", av, environ);
    perror("native shell exec");
    return 126;
}
