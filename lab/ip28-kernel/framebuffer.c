/* Check the RAM-only framebuffer mapping and its page boundaries. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <dev/wscons/wsconsio.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

int
main(void)
{
    int fd = open("/dev/ttyE0", O_RDWR);
    struct wsdisplay_fbinfo info;
    unsigned stride;
    if (fd < 0 || ioctl(fd, WSDISPLAYIO_GINFO, &info) ||
        ioctl(fd, WSDISPLAYIO_LINEBYTES, &stride)) return 1;
    if (info.width != 1280 || info.height != 1024 ||
        info.depth != 32 || stride != 1280 * 4) return 2;
    int mode = WSDISPLAYIO_MODE_DUMBFB;
    if (ioctl(fd, WSDISPLAYIO_SMODE, &mode)) return 3;
    size_t size = (size_t)stride * info.height;
    long page = sysconf(_SC_PAGESIZE);
    if (page <= 0) return 3;
    const off_t invalid[] = { -page, (off_t)size, (off_t)size + page };
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); i++) {
        void *p = mmap(NULL, page, PROT_READ | PROT_WRITE, MAP_SHARED, fd, invalid[i]);
        if (p != MAP_FAILED) { munmap(p, page); return 4; }
    }
    volatile uint32_t *fb = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if ((const void *)fb == MAP_FAILED) { perror("framebuffer mmap"); return 6; }
    fb[0] = 0x000000ff;
    fb[size / 4 - 1] = 0x00ff0000;
    if (fb[0] != 0x000000ff || fb[size / 4 - 1] != 0x00ff0000) return 7;
    mode = WSDISPLAYIO_MODE_EMUL;
    if (munmap((void *)fb, size) || ioctl(fd, WSDISPLAYIO_SMODE, &mode) || close(fd)) return 8;
    printf("FRAMEBUFFER_PASS %ux%ux%u stride=%u size=%zu\n",
        info.width, info.height, info.depth, stride, size);
    return 0;
}
