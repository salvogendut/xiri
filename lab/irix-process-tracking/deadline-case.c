/* Disposable native guest fixture. Pipe lifetime bounds every worker,
 * including failed-guard cases. The same-user sentinel is outside the
 * guard's tree. No UID-wide or guessed-PID cleanup is used. */
#include <sys/types.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static void
fail(const char *what)
{
    perror(what);
    exit(90);
}

static void
pause_ms(long ms)
{
    struct timespec left = {ms / 1000, ms % 1000 * 1000000};
    while (nanosleep(&left, &left) < 0 && errno == EINTR) {}
}

static int
living(pid_t pid)
{
    struct kinfo_proc2 p;
    int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, sizeof(p), 1};
    size_t size = sizeof(p);
    memset(&p, 0, sizeof(p));
    if (sysctl(mib, 6, &p, &size, NULL, 0)) fail("sysctl");
    if (size == 0) return 0;
    if (size != sizeof(p) || p.p_pid != pid) fail("process record");
    return p.p_realstat != SZOMB && p.p_realstat != SDEAD;
}

static int
wait_child(pid_t child)
{
    int status;
    pid_t done;
    do done = waitpid(child, &status, 0); while (done < 0 && errno == EINTR);
    if (done != child) fail("waitpid");
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

static void
worker(int birth, int gate, const char *mode)
{
    alarm(30);
    if (!strcmp(mode, "kill")) signal(SIGTERM, SIG_IGN);
    int ready[2] = {-1, -1};
    if (!strcmp(mode, "leader")) {
        if (pipe(ready)) fail("ready pipe");
        pid_t child = fork();
        if (child < 0) fail("worker fork");
        if (child) {
            char byte;
            close(ready[1]); close(birth); close(gate);
            if (read(ready[0], &byte, 1) != 1) _exit(93);
            _exit(37);
        }
        close(ready[0]); alarm(30);
    }
    pid_t pid = getpid();
    if (write(birth, &pid, sizeof(pid)) != (ssize_t)sizeof(pid)) _exit(94);
    close(birth);
    if (ready[1] >= 0) {
        if (write(ready[1], "x", 1) != 1) _exit(95);
        close(ready[1]);
    }
    char byte;
    ssize_t n;
    do n = read(gate, &byte, 1); while (n < 0 && errno == EINTR);
    _exit(n == 0 ? 0 : 96);
}

int
main(int argc, char **argv)
{
    if (argc == 5 && !strcmp(argv[1], "--worker"))
        worker(atoi(argv[2]), atoi(argv[3]), argv[4]);
    if (argc != 4 || getuid() == 0) return 90;
    alarm(60);
    const char *mode = argv[3];
    if (strcmp(mode,"fast") && strcmp(mode,"term") && strcmp(mode,"kill") &&
        strcmp(mode,"live") && strcmp(mode,"signal") && strcmp(mode,"logout") &&
        strcmp(mode,"leader")) return 90;
    char self[PATH_MAX], guard[PATH_MAX], library[PATH_MAX];
    if (!realpath(argv[0], self) || !realpath(argv[1], guard) || !realpath(argv[2], library))
        fail("realpath");
    int sentinel_pipe[2], birth[2], gate[2];
    if (pipe(sentinel_pipe)) fail("sentinel pipe");
    pid_t sentinel = fork();
    if (sentinel < 0) fail("sentinel fork");
    if (!sentinel) {
        char c;
        alarm(60); close(sentinel_pipe[1]);
        _exit(read(sentinel_pipe[0], &c, 1) == 0 ? 0 : 97);
    }
    close(sentinel_pipe[0]);
    if (pipe(birth) || pipe(gate)) fail("worker pipes");
    char stdout_path[64], stderr_path[64], stop_path[64];
    snprintf(stdout_path, sizeof(stdout_path), "%s.guard", mode);
    snprintf(stderr_path, sizeof(stderr_path), "%s.trace", mode);
    snprintf(stop_path, sizeof(stop_path), "%s.logout", mode);
    int out = open(stdout_path, O_CREAT|O_EXCL|O_WRONLY, 0600);
    int err = open(stderr_path, O_CREAT|O_EXCL|O_WRONLY, 0600);
    if (out < 0 || err < 0) fail("guard logs");
    pid_t supervisor = fork();
    if (supervisor < 0) fail("guard fork");
    if (!supervisor) {
        close(sentinel_pipe[1]); close(birth[0]); close(gate[1]);
        if (dup2(out, STDOUT_FILENO) < 0 || dup2(err, STDERR_FILENO) < 0) _exit(98);
        close(out); close(err);
        char born[16], held[16];
        snprintf(born, sizeof(born), "%d", birth[1]);
        snprintf(held, sizeof(held), "%d", gate[0]);
        if (setenv("LD_PRELOAD", library, 1) || setenv("XIRI_DELAY_CASE", mode, 1)) _exit(98);
        if (!strcmp(mode, "logout") && setenv("XIRI_SESSION_STOP_FILE", stop_path, 1)) _exit(98);
        const char *duration = (!strcmp(mode,"signal") || !strcmp(mode,"logout")) ? "0" : "2000";
        execl(guard, guard, duration, self, "--worker", born, held, mode, (char *)NULL);
        _exit(99);
    }
    close(out); close(err); close(birth[1]); close(gate[0]);
    pid_t target;
    if (read(birth[0], &target, sizeof(target)) != (ssize_t)sizeof(target) || target <= 1)
        fail("worker birth");
    close(birth[0]);
    if (!strcmp(mode,"signal") && kill(supervisor, SIGTERM)) fail("request stop");
    if (!strcmp(mode,"logout")) {
        int fd = open(stop_path, O_CREAT|O_EXCL|O_WRONLY, 0600);
        if (fd < 0) fail("logout file");
        close(fd);
    }
    int rc = wait_child(supervisor), live = living(target), independent = living(sentinel);
    /* Release any intentionally surviving worker through our private pipe. */
    close(gate[1]);
    for (int i = 0; i < 200 && living(target); ++i) pause_ms(10);
    int safe = !living(target);
    close(sentinel_pipe[1]);
    int sentinel_rc = wait_child(sentinel);
    int expected = !strcmp(mode,"live") ? 2 : !strcmp(mode,"leader") ? 37 : 0;
    int expected_live = !strcmp(mode,"live");
    printf("DEADLINE case=%s uid=%u guard=%d worker=%d rc=%d expected=%d live=%d expected_live=%d sentinel=%d sentinel_rc=%d safe_cleanup=%d\n",
        mode, (unsigned)getuid(), supervisor, target, rc, expected, live,
        expected_live, independent, sentinel_rc, safe);
    return rc != expected || live != expected_live || !independent || sentinel_rc || !safe;
}
