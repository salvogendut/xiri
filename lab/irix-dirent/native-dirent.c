/* Observe native directory order and inode numbers independently of IRIX. */
#include <sys/types.h>
#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    DIR *directory;
    struct dirent *entry;
    int first = 1;
    if (argc != 2) return 90;
    directory = opendir(argv[1]);
    if (!directory) { printf("{\"error\":%d}\n", errno); return 0; }
    printf("{\"entries\":[");
    while ((entry = readdir(directory)) != NULL) {
        if (!entry->d_fileno) continue;
        /* Fixture names have no JSON quoting characters. */
        printf("%s{\"name\":\"%s\",\"ino\":%ju}", first ? "" : ",",
            entry->d_name, (uintmax_t)entry->d_fileno);
        first = 0;
    }
    printf("]}\n");
    return closedir(directory) != 0;
}
