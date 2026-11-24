#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void
done(int sig)
{
    (void)sig;
    running = 0;
}

int
main(void)
{
    const size_t size = 24 * 1024 * 1024;
    volatile unsigned char *pages = malloc(size);

    if (pages == NULL)
        return 1;
    for (size_t offset = 0; offset < size; offset += 4096)
        pages[offset] = 1;
    signal(SIGALRM, done);
    alarm(40);
    while (running)
        ++pages[0];
    return 0;
}
