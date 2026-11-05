/* Native swap-control regression; run only in a disposable guest with no swap. */
#include <sys/types.h>
#include <sys/swap.h>
#include <sys/sysctl.h>
#include <stdbool.h>
#include <stdio.h>
#include <unistd.h>

int
main(void)
{
    if (swapctl(SWAP_NSWAP, NULL, 0) != 0) {
        fprintf(stderr, "SWAP_CONTROL requires no configured swap devices\n");
        return 2;
    }
    const bool requested[] = {false, true, false, true};
    int failures = 0;
    for (unsigned i = 0; i < sizeof(requested) / sizeof(requested[0]); i++) {
        bool actual = !requested[i];
        size_t size = sizeof(actual);
        int write_rc = sysctlbyname("vm.swap_encrypt", NULL, NULL,
            &requested[i], sizeof(requested[i]));
        int read_rc = sysctlbyname("vm.swap_encrypt", &actual, &size, NULL, 0);
        bool valid = !write_rc && !read_rc && size == sizeof(actual) && actual == requested[i];
        printf("SWAP_CONTROL requested=%u actual=%u size=%zu write_rc=%d read_rc=%d valid=%u\n",
            requested[i], actual, size, write_rc, read_rc, valid);
        failures += !valid;
    }
    printf("SWAP_CONTROL_RESULT cases=4 failures=%d final_requested=1\n", failures);
    return failures ? 1 : 0;
}
