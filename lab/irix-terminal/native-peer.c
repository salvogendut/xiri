/* Native peer for foreign receive cleanup; run inside the bounded runner. */
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    int mode = atoi(argv[2]), pair[2], status, input;
    if (mode < 0 || mode > 3 || socketpair(AF_UNIX, SOCK_STREAM, 0, pair)) return 2;
    input = open("input.txt", O_RDONLY);
    if (input < 0) return 2;
    pid_t child = fork();
    if (child < 0) return 2;
    if (!child) {
        if (dup2(pair[1], 0) < 0) _exit(125);
        close(pair[0]); close(pair[1]); close(input);
        char *const args[] = {argv[1], argv[2], NULL};
        char *const env[] = {NULL};
        execve(argv[1], args, env);
        _exit(126);
    }
    close(pair[1]);
    union { struct cmsghdr alignment; char bytes[CMSG_SPACE(2*sizeof(int))]; } control;
    memset(&control, 0, sizeof(control));
    struct iovec vector = {(void *)"D", 1};
    struct msghdr msg;
    memset(&msg, 0, sizeof(msg));
    msg.msg_iov = &vector; msg.msg_iovlen = 1;
    msg.msg_control = &control;
    msg.msg_controllen = CMSG_SPACE((mode == 1 ? 2 : 1)*sizeof(int));
    struct cmsghdr *cm = CMSG_FIRSTHDR(&msg);
    cm->cmsg_level = SOL_SOCKET; cm->cmsg_type = SCM_RIGHTS;
    cm->cmsg_len = CMSG_LEN((mode == 1 ? 2 : 1)*sizeof(int));
    int descriptors[2] = {input, input};
    memcpy(CMSG_DATA(cm), descriptors, (mode == 1 ? 2 : 1)*sizeof(int));
    int failed = sendmsg(pair[0], &msg, 0) != 1;
    close(input); close(pair[0]);
    if (failed) kill(child, SIGKILL);
    while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
    return failed || !WIFEXITED(status) ? 125 : WEXITSTATUS(status);
}
