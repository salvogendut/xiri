/* Native peer returns the accepted socket's own address independently of the foreign query. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int count = argc == 2 ? atoi(argv[1]) : 0;
    alarm(300);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {.sin_len = sizeof(address),
        .sin_family = AF_INET, .sin_port = htons(6113),
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    if (count <= 0 || fd < 0 || bind(fd, (struct sockaddr *)&address,
        sizeof(address)) || listen(fd, 4)) return 2;
    puts("RDY"); fflush(stdout);
    for (int i = 0; i < count; i++) {
        struct sockaddr_in local;
        socklen_t length = sizeof(local);
        int client = accept(fd, NULL, NULL);
        if (client < 0 || getsockname(client, (struct sockaddr *)&local, &length)) return 2;
        unsigned char data[16] = {0, 2};
        if (length != sizeof(local) || local.sin_family != AF_INET ||
            local.sin_addr.s_addr != htonl(INADDR_LOOPBACK) || local.sin_port != htons(6113)) return 2;
        memcpy(data + 2, &local.sin_port, 2);
        memcpy(data + 4, &local.sin_addr, 4);
        for (size_t used = 0; used < sizeof(data);) {
            ssize_t n = write(client, data + used, sizeof(data) - used);
            if (n <= 0) return 2;
            used += (size_t)n;
        }
        unsigned char end;
        if (read(client, &end, 1) != 0 || close(client)) return 2;
    }
    return close(fd) ? 2 : 0;
}
