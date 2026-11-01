/* Native process control: IRIX exec must not relax native page-zero policy. */
#include <sys/mman.h>
#include <sys/sysctl.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
int main(void)
{
    int guard = -1;
    size_t size = sizeof(guard);
    if (sysctlbyname("vm.user_va0_disable", &guard, &size, NULL, 0)) return 2;
    int fd = open("/dev/zero", O_RDONLY);
    if (fd < 0) return 2;
    void *p = mmap(NULL, getpagesize(), PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_FIXED, fd, 0);
    int e = errno;
    close(fd);
    if (p != MAP_FAILED) { munmap(p, getpagesize()); return 3; }
    printf("NATIVE_ZERO page=%d guard=%d errno=%d\n", getpagesize(), guard, e);
    return guard == 1 && e == EINVAL ? 0 : 4;
}
