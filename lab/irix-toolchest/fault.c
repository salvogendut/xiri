/* Deliberately fault at a labelled instruction to validate the native tracer. */
int main(void)
{
    __asm__ volatile(
        ".set push\n"
        ".set noreorder\n"
        ".globl xiri_fault_site\n"
        "xiri_fault_site:\n"
        "lw $2,0($0)\n"
        "nop\n"
        ".set pop\n" ::: "$2");
    return 0;
}
