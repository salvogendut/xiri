/* A native exec must not retain the preceding IRIX process's PRDA mapping. */
#include <sys/mman.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
int main(void)
{
    char vec = 0;
    int rc = mincore((void *)0x200000, getpagesize(), &vec), e = errno;
    printf("NATIVE_PRDA absent=%d errno=%d page=%d\n", rc == -1, e, getpagesize());
    return rc == -1 && e == ENOMEM ? 0 : 2;
}
