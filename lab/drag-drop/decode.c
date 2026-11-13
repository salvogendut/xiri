/* Exercise the runtime's bounded filename decoder without an X server. */
#include <stdio.h>
#include "drop-files.h"
int main(int argc, char **argv)
{
    unsigned char data[XIRI_DROP_LIMIT + 1];
    if (argc != 2) return 2;
    size_t size = fread(data, 1, sizeof(data), stdin), length;
    unsigned count;
    char *uris = drop_uris(data, size, argv[1], &length, &count);
    if (!uris) return 1;
    int failed = fwrite(uris, 1, length, stdout) != length;
    free(uris); return failed ? 2 : 0;
}
