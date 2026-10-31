/* Native peer independently records each connection's bytes in fixed BE records. */
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
    alarm(600);
    int held = -1, fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {.sin_len = sizeof(address),
        .sin_family = AF_INET, .sin_port = htons(6114),
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    if (count <= 0 || fd < 0 || bind(fd, (struct sockaddr *)&address,
        sizeof(address)) || listen(fd, 4)) return 2;
    puts("RDY"); fflush(stdout);
    for (int i = 0; i < count; i++) {
        int client = accept(fd, NULL, NULL);
        unsigned char header[8], record[24] = {0};
        if (client < 0 || (held >= 0 && close(held))) return 2;
        held = -1;
        for (size_t used = 0; used < sizeof(header);) {
            ssize_t n = read(client, header + used, sizeof(header) - used);
            if (n <= 0) return 2;
            used += (size_t)n;
        }
        size_t used = 0;
        for (;;) {
            unsigned char extra;
            ssize_t n = read(client, used < 16 ? record + 8 + used : &extra,
                used < 16 ? 16 - used : 1);
            if (n < 0 || (used == 16 && n != 0)) return 2;
            if (!n) break;
            used += (size_t)n;
        }
        memcpy(record, header, 4);
        uint32_t length = htonl((uint32_t)used), ack;
        memcpy(record + 4, &length, 4); memcpy(&ack, header + 4, 4);
        if (ntohl(ack) > 1) return 2;
        if (ack && write(client, &length, 4) != 4) return 2;
        if (fwrite(record, 1, sizeof(record), stdout) != sizeof(record) ||
            fflush(stdout)) return 2;
        if (ack) held = client;
        else if (close(client)) return 2;
    }
    return (held >= 0 && close(held)) || close(fd) ? 2 : 0;
}
