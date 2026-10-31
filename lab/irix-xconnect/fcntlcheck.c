/* Native observer verifies the shared file-status flags changed by an IRIX child. */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    int wanted = atoi(argv[2]), status, fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd != 3) return 2;
    pid_t child = fork();
    if (child < 0) return 2;
    if (!child) {
        char *av[] = {argv[1], NULL}, *ev[] = {NULL};
        execve(argv[1], av, ev);
        _exit(126);
    }
    if (waitpid(child, &status, 0) != child || !WIFEXITED(status) || WEXITSTATUS(status)) return 2;
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDWR ||
        !!(flags & O_NONBLOCK) != !!(wanted & 128) ||
        !!(flags & O_APPEND) != !!(wanted & 8) || close(fd)) return 2;
    return 0;
}
