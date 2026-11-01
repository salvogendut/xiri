/* The launcher exits while a descendant owns a separate session. */
#include <sys/types.h>
#include <stdlib.h>
#include <unistd.h>
int main(void)
{
    pid_t p = fork();
    if (p < 0) return 2;
    if (p) return 0;
    if (setsid() < 0) _exit(2);
    sleep(60);
    return 3;
}
