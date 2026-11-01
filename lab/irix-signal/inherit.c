/* Extra native qualification: a fork child must inherit the foreign handler
 * and trampoline. Report failure through the parent's checked exit status. */
#define probe_call checked_call
#include "probe.c"
#undef probe_call
extern void probe_call(U, const U *, struct reply *);

void checked_call(U number, const U *args, struct reply *result)
{
    probe_call(number, args, result);
    if (number == 1002 && !result->error && result->second) {
        struct reply original = *result, r;
        U a[6] = {0};
        probe_call(1020, a, &r);
        U pid = r.value, unblock[4] = {0x20000, 0, 0, 0};
        /* Parent deliberately blocked SIGCHLD before fork. Release that
         * inherited hold in the child before testing its inherited handler. */
        a[0] = 2;
        a[1] = (U)unblock;
        probe_call(1164, a, &r);
        a[0] = pid;
        a[1] = 18;
        probe_call(1037, a, &r);
        if (r.error || count != 1) {
            a[0] = 38;
            probe_call(1001, a, &r);
        }
        *result = original;
    }
}
