/* Native observer checks that a foreign setsockopt changes the real socket. */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    int keepalive = atoi(argv[2]), wanted = atoi(argv[3]), value = !wanted;
    int level = keepalive ? SOL_SOCKET : IPPROTO_TCP;
    int option = keepalive ? SO_KEEPALIVE : TCP_NODELAY;
    int fd = socket(AF_INET, SOCK_STREAM, 0), status;
    socklen_t size = sizeof(value);
    if (fd != 3 || setsockopt(fd, level, option, &value, sizeof(value))) return 2;
    pid_t child = fork();
    if (child < 0) return 2;
    if (!child) {
        char *av[] = {argv[1], NULL}, *ev[] = {NULL};
        execve(argv[1], av, ev);
        _exit(126);
    }
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status) ||
        getsockopt(fd, level, option, &value, &size) || size != sizeof(value) ||
        !!value != wanted || close(fd)) return 2;
    return 0;
}
