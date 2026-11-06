/* Exercise original FAM v1 framing under two native accounts concurrently.
 * Send deliberately wrong request credentials: connection ownership wins. */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <arpa/inet.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int own, group, other, forbidden, created, deleted;

static void transfer(int fd, void *buf, size_t length, int writing)
{
    char *p = buf;
    while (length) {
        ssize_t n = writing ? write(fd, p, length) : read(fd, p, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) errx(1, "FAM connection closed or failed");
        p += n; length -= (size_t)n;
    }
}

static void monitor_dir(int fd, unsigned req, const char *path, unsigned claim)
{
    char msg[4096];
    int n = snprintf(msg, sizeof(msg), "M%u %u 0 %s", req, claim, path);
    if (n < 0 || (size_t)n + 5 >= sizeof(msg)) errx(1, "path too long");
    /* A second string supplies forged supplementary group zero as well. */
    memcpy(msg + n + 1, "1 0", 4);
    uint32_t size = htonl((uint32_t)n + 5);
    transfer(fd, &size, sizeof(size), 1);
    transfer(fd, msg, (size_t)n + 5, 1);
}

static long long now_ms(void)
{
    struct timeval t;
    if (gettimeofday(&t, NULL)) err(1, "gettimeofday");
    return (long long)t.tv_sec * 1000 + t.tv_usec / 1000;
}

static void events(int fd, int ms)
{
    long long end = now_ms() + ms;
    while (now_ms() < end) {
        struct pollfd p = { fd, POLLIN, 0 };
        if (poll(&p, 1, 100) <= 0) continue;
        uint32_t size;
        char msg[8192], code;
        unsigned req;
        transfer(fd, &size, sizeof(size), 0);
        size = ntohl(size);
        if (!size || size >= sizeof(msg)) errx(1, "invalid event length");
        transfer(fd, msg, size, 0); msg[size] = 0;
        if (sscanf(msg, "%c%u", &code, &req) != 2) errx(1, "invalid event");
        printf("EVENT %s", msg);
        if (code == 'e' && req == 1 && strstr(msg, "private-marker")) own++;
        if (code == 'e' && req == 3 && strstr(msg, "group-marker")) group++;
        if (req == 2 && strstr(msg, "private-marker")) other++;
        if (req == 4 && strstr(msg, "root-marker")) forbidden++;
        if (req == 1 && strstr(msg, "transition-marker")) {
            if (code == 'F') created++;
            if (code == 'A') deleted++;
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 7) errx(2, "port own-dir other-dir group-dir root-dir claimed-uid");
    alarm(45);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)strtoul(argv[1], NULL, 10));
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0 || connect(fd, (struct sockaddr *)&addr, sizeof(addr))) err(1, "connect");
    for (unsigned i = 1; i <= 4; ++i)
        monitor_dir(fd, i, argv[i + 1], i == 4 ? 0 : (unsigned)strtoul(argv[6], NULL, 10));
    events(fd, 4000);
    char path[4096];
    if (snprintf(path, sizeof(path), "%s/transition-marker", argv[2]) >= (int)sizeof(path))
        errx(1, "path too long");
    int file = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (file < 0) err(1, "create marker");
    close(file); events(fd, 4000);
    if (unlink(path)) err(1, "unlink marker");
    events(fd, 4000); close(fd);
    if (!own || !group || other || forbidden || !created || !deleted)
        errx(1, "uid=%u own=%d group=%d other=%d root=%d created=%d deleted=%d",
            (unsigned)getuid(), own, group, other, forbidden, created, deleted);
    printf("FAM_MULTIUSER_PASS uid=%u own=1 supplementary=1 other=0 forged_root=0 created=1 deleted=1\n",
        (unsigned)getuid());
    return 0;
}
