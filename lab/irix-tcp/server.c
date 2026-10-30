/* Native NetBSD peer: verify real foreign TCP read/write, bound all waits. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int count = argc == 2 ? atoi(argv[1]) : 4;
    alarm(180);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {.sin_len = sizeof(address),
        .sin_family = AF_INET, .sin_port = htons(6111),
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    if (fd < 0 || bind(fd, (struct sockaddr *)&address, sizeof(address)) || listen(fd, 4)) return 2;
    puts("RDY"); fflush(stdout);
    for (int i = 0; i < count; i++) {
        int client = accept(fd, NULL, NULL);
        char data[8]; size_t used = 0;
        if (client < 0) return 2;
        while (used < sizeof(data)) {
            ssize_t n = read(client, data + used, sizeof(data) - used);
            if (n <= 0) return 2;
            used += (size_t)n;
        }
        if (memcmp(data, "XIRI_TCP", 8)) return 2;
        for (used = 0; used < sizeof(data);) {
            ssize_t n = write(client, data + used, sizeof(data) - used);
            if (n <= 0) return 2;
            used += (size_t)n;
        }
        if (close(client)) return 2;
    }
    return close(fd) ? 2 : 0;
}
