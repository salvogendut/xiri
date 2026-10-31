/* Native source peer: readiness byte, fixed data/EOF, then client-close receipt. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int count = argc == 2 ? atoi(argv[1]) : 0;
    alarm(900);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {.sin_len = sizeof(address),
        .sin_family = AF_INET, .sin_port = htons(6115),
        .sin_addr.s_addr = htonl(INADDR_LOOPBACK)};
    if (count <= 0 || fd < 0 || bind(fd, (struct sockaddr *)&address,
        sizeof(address)) || listen(fd, 4)) return 2;
    puts("RDY"); fflush(stdout);
    for (int i = 0; i < count; i++) {
        int client = accept(fd, NULL, NULL);
        uint32_t header[2], record[3];
        if (client < 0) return 2;
        for (size_t used = 0; used < sizeof(header);) {
            ssize_t n = read(client, (char *)header + used, sizeof(header) - used);
            if (n <= 0) return 2;
            used += (size_t)n;
        }
        unsigned mode = ntohl(header[1]);
        if (mode > 2) return 2;
        size_t count = mode == 0 ? 9 : 1;
        if (write(client, "RXIRI_RCV", count) != (ssize_t)count ||
            (mode != 2 && shutdown(client, SHUT_WR))) return 2;
        unsigned char extra;
        ssize_t n = read(client, &extra, 1);
        if ((n != 0 && !(n == -1 && errno == ECONNRESET)) || close(client)) return 2;
        record[0] = header[0]; record[1] = header[1]; record[2] = htonl((uint32_t)count-1);
        if (fwrite(record, sizeof(record), 1, stdout) != 1 || fflush(stdout)) return 2;
    }
    return close(fd) ? 2 : 0;
}
