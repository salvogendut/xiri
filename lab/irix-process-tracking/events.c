/* Native NetBSD child-event oracle. Run only in a disposable guest.
 * Pipe records identify every intended child independently of kqueue.
 * Every child has an alarm; closing the parent releases held children. */
#include <sys/types.h>
#include <sys/event.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

enum { CHILDREN = 8, MAX_BATCH = 64 };
struct birth { pid_t pid, parent; int code; };

static void
fail(const char *message)
{
    fprintf(stderr, "EVENT_FAIL %s errno=%d\n", message, errno);
    exit(2);
}

static long long
now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) fail("clock_gettime");
    return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void
publish(int fd, pid_t parent, int code)
{
    struct birth b = { getpid(), parent, code };
    if (write(fd, &b, sizeof(b)) != (ssize_t)sizeof(b)) _exit(3);
}

static void
read_birth(int fd, struct birth *b)
{
    size_t used = 0;
    while (used < sizeof(*b)) {
        ssize_t n = read(fd, (char *)b + used, sizeof(*b) - used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) fail("missing birth record");
        used += (size_t)n;
    }
}

static void
one_round(int kq, const char *mode, int batch, int round)
{
    int births[2], gate[2], status;
    struct birth known[CHILDREN];
    unsigned seen[CHILDREN] = {0};
    pid_t direct[CHILDREN], parent = getpid();
    int orphan = !strcmp(mode, "orphan"), held = !strcmp(mode, "held");
    int count = orphan ? CHILDREN / 2 : CHILDREN;
    if (pipe(births) || pipe(gate)) fail("pipe");
    for (int i = 0; i < count; ++i) {
        direct[i] = fork();
        if (direct[i] < 0) fail("fork");
        if (!direct[i]) {
            close(kq); close(births[0]); close(gate[1]);
            alarm(15);
            publish(births[1], parent, 37);
            if (orphan) {
                if (setsid() < 0) _exit(4);
                pid_t first = getpid(), grandchild = fork();
                if (grandchild < 0) _exit(5);
                if (!grandchild) {
                    alarm(15);
                    publish(births[1], first, 41);
                    close(births[1]); close(gate[0]);
                    /* Require reparenting, rather than merely allowing the
                     * grandchild to race its parent's exit. */
                    while (getppid() == first) {
                        struct timespec pause = {0, 1000000};
                        nanosleep(&pause, NULL);
                    }
                    _exit(41);
                }
            }
            close(births[1]);
            if (held) {
                char c;
                ssize_t n;
                do n = read(gate[0], &c, 1); while (n < 0 && errno == EINTR);
                if (n != 0) _exit(6);
            }
            close(gate[0]); _exit(37);
        }
    }
    close(births[1]); close(gate[0]);
    for (int i = 0; i < CHILDREN; ++i) {
        read_birth(births[0], &known[i]);
        for (int j = 0; j < i; ++j)
            if (known[i].pid == known[j].pid) fail("duplicate oracle PID");
    }
    close(births[0]); close(gate[1]);
    long long deadline = now() + 15000;
    int tracks = 0, exits = 0;
    while (tracks != CHILDREN || exits != CHILDREN) {
        struct kevent events[MAX_BATCH];
        struct timespec timeout = {0, 20000000};
        int n = kevent(kq, NULL, 0, events, batch, &timeout);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) fail("kevent");
        for (int i = 0; i < n; ++i) {
            struct kevent *e = &events[i];
            int j;
            for (j = 0; j < CHILDREN && known[j].pid != (pid_t)e->ident; ++j) {}
            if (j == CHILDREN || e->filter != EVFILT_PROC ||
                (e->flags & EV_ERROR) || (e->fflags & NOTE_TRACKERR))
                fail("unexpected event");
            if (e->fflags == NOTE_CHILD && !(seen[j] & 1)) {
                if (e->data != known[j].parent) fail("wrong fork parent");
                seen[j] |= 1; ++tracks;
            } else if (e->fflags == NOTE_EXIT && seen[j] == 1) {
                status = (int)e->data;
                if (!(e->flags & EV_EOF) || !WIFEXITED(status) ||
                    WEXITSTATUS(status) != known[j].code) fail("wrong exit status");
                seen[j] |= 2; ++exits;
            } else fail("duplicate, missing or reordered child event");
        }
        if (now() >= deadline) {
            fprintf(stderr, "EVENT_TIMEOUT mode=%s batch=%d round=%d tracks=%d exits=%d\n",
                mode, batch, round, tracks, exits);
            for (int j = 0; j < CHILDREN; ++j)
                fprintf(stderr, "PENDING pid=%d parent=%d seen=%u\n",
                    known[j].pid, known[j].parent, seen[j]);
            exit(2);
        }
    }
    for (int i = 0; i < count; ++i) {
        pid_t done;
        do done = waitpid(direct[i], &status, 0); while (done < 0 && errno == EINTR);
        if (done != direct[i] || !WIFEXITED(status) || WEXITSTATUS(status) != 37)
            fail("direct child not reaped");
    }
    struct kevent event;
    struct timespec zero = {0, 0};
    if (kevent(kq, NULL, 0, &event, 1, &zero) != 0) fail("trailing event");
}

int
main(int argc, char **argv)
{
    if (argc != 3) return 2;
    int batch = atoi(argv[1]), rounds = atoi(argv[2]);
    if ((batch != 1 && batch != MAX_BATCH) || rounds < 1 || rounds > 64) return 2;
    alarm(240);
    setvbuf(stdout, NULL, _IOLBF, 0);
    int kq = kqueue();
    struct kevent change;
    EV_SET(&change, getpid(), EVFILT_PROC, EV_ADD, NOTE_TRACK | NOTE_EXIT, 0, NULL);
    if (kq < 0 || kevent(kq, &change, 1, NULL, 0, NULL)) fail("register events");
    const char *modes[] = {"fast", "orphan", "held"};
    for (unsigned m = 0; m < sizeof(modes) / sizeof(modes[0]); ++m) {
        for (int r = 0; r < rounds; ++r) one_round(kq, modes[m], batch, r);
        printf("EVENT_PASS uid=%u mode=%s batch=%d rounds=%d births=%d exits=%d\n",
            (unsigned)getuid(), modes[m], batch, rounds, rounds * CHILDREN, rounds * CHILDREN);
    }
    close(kq);
    return 0;
}
