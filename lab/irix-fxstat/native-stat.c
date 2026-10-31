/* Independent native fstat observer; emits named values, never a foreign layout. */
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    struct stat s;
    if (argc != 3) return 2;
    int fd = !strcmp(argv[1], "STDIN") ? 0 : open(argv[1], atoi(argv[2]));
    if (fd < 0 || fstat(fd, &s)) {
        printf("{\"errno\":%d}\n", errno);
        return 0;
    }
    printf("{\"errno\":0,\"dev_major\":%ju,\"dev_minor\":%ju,"
        "\"ino\":%ju,\"mode\":%ju,\"nlink\":%ju,\"uid\":%ju,\"gid\":%ju,"
        "\"rdev_major\":%ju,\"rdev_minor\":%ju,\"size\":%jd,"
        "\"atime\":%jd,\"atime_nsec\":%ld,\"mtime\":%jd,\"mtime_nsec\":%ld,"
        "\"ctime\":%jd,\"ctime_nsec\":%ld,\"blksize\":%jd,\"blocks\":%jd}\n",
        (uintmax_t)major(s.st_dev),(uintmax_t)minor(s.st_dev),
        (uintmax_t)s.st_ino,(uintmax_t)s.st_mode,(uintmax_t)s.st_nlink,
        (uintmax_t)s.st_uid,(uintmax_t)s.st_gid,
        (uintmax_t)major(s.st_rdev),(uintmax_t)minor(s.st_rdev),(intmax_t)s.st_size,
        (intmax_t)s.st_atim.tv_sec,s.st_atim.tv_nsec,
        (intmax_t)s.st_mtim.tv_sec,s.st_mtim.tv_nsec,
        (intmax_t)s.st_ctim.tv_sec,s.st_ctim.tv_nsec,
        (intmax_t)s.st_blksize,(intmax_t)s.st_blocks);
    return 0;
}
