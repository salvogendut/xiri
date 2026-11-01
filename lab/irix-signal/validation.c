/* Native policy checks, separate from the unchanged original-IRIX fixtures. */
#define signal_body observed_body
#define main observed_main
#include "probe.c"
#undef signal_body
#undef main

static B temporary[856] __attribute__((aligned(8)));
static void regput(U slot, Q value)
{
    if (N32) {
        put(temporary + 40 + slot * 8, value >> 32);
        put(temporary + 44 + slot * 8, (U)value);
    } else put(temporary + 40 + slot * 4, (U)value);
}

void signal_body(void)
{
    observed_body();
    U context = (U)signal_entry[6], bytes = N32 ? 800 : 512;
    for (U variant = 0; variant < 7; variant++) {
        copy(temporary, (B *)context, bytes);
        U address = (U)temporary;
        switch (variant) {
        case 0: put(temporary, 16); break;
        case 1: regput(35, 0x80000000U); break;
        case 2: regput(35, 0x400002); break;
        case 3: regput(29, 0x80000000U); break;
        case 4: put(temporary + 12, 1); break;
        case 5: put(temporary + 32, 4); break;
        case 6:
            address = rec[14] + rec[13] - 4;
            put((B *)address, 7);
            break;
        }
        reply(80 + 3 * variant, C(1088, 0, address, (U)signal_entry[4]));
    }
    U active[4];
    reply(101, C(1164, 0, 0, active));
    for (U i = 0; i < 4; i++) rec[104 + i] = active[i];
    rec[108] = 0x56414c44;
    /* The native context helper must ignore a user-supplied processor status.
     * Successful normal return and subsequent syscalls are the control. */
    if (N32) {
        put((B *)context + 40 + 36 * 8, 0xffffffffU);
        put((B *)context + 44 + 36 * 8, 0xffffffffU);
        rec[109] = 1;
    }
}

int main(int argc, char **argv)
{
    return observed_main(argc, argv);
}
