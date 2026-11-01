/* Report the actual native limits inherited by an original foreign fixture. */
#include <sys/resource.h>
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    const int resources[] = {RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_DATA, RLIMIT_STACK,
        RLIMIT_CORE, RLIMIT_NOFILE, RLIMIT_AS, RLIMIT_RSS, RLIMIT_NTHR};
    if (argc < 3) return 2;
    if (atoi(argv[1])) {
        const struct rlimit files = {37, 99}, threads = {17, 41};
        const struct rlimit size = atoi(argv[1]) == 2 ?
            (struct rlimit){UINT64_C(0x80000001), UINT64_C(0xf1234567)} :
            (struct rlimit){UINT64_C(0x123456789), UINT64_C(0x23456789a)};
        if (setrlimit(RLIMIT_NOFILE, &files) || setrlimit(RLIMIT_NTHR, &threads) ||
            setrlimit(RLIMIT_FSIZE, &size)) { perror("setrlimit"); return 3; }
    }
    for (size_t i = 0; i < sizeof(resources)/sizeof(resources[0]); i++) {
        struct rlimit limit;
        if (getrlimit(resources[i], &limit)) { perror("getrlimit"); return 4; }
        fprintf(stderr, "NATIVE_LIMIT resource=%zu soft=%" PRIu64 " hard=%" PRIu64 "\n",
            i, (uint64_t)limit.rlim_cur, (uint64_t)limit.rlim_max);
    }
    fflush(stderr);
    execv(argv[2], &argv[2]);
    perror("execv");
    return 5;
}
