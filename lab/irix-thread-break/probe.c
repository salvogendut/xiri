/* A freestanding n32 heap control for the 8 KiB Indy kernel. */
typedef unsigned int word;
#define PTR(x) ((word)(x))
#define SHARE_FLAGS 0x020000ff
__asm__(".pushsection .note.probe,\"a\",@note\n"
    ".long 5,4,0x49524958\n.asciz \"Xiri\"\n.balign 4\n.long 1\n.popsection");

static int
call(word number, word x, word y, word z, word w, word fd)
{
	register word v0 __asm__("$2") = number;
	register word a0 __asm__("$4") = x, a1 __asm__("$5") = y;
	register word a2 __asm__("$6") = z, a3 __asm__("$7") = w;
	register word a4 __asm__("$8") = fd, a5 __asm__("$9") = 0;
	__asm__ volatile("syscall\n\tnop" : "+r"(v0), "+r"(a0), "+r"(a1),
	    "+r"(a2), "+r"(a3), "+r"(a4), "+r"(a5) : : "memory", "$1", "$3", "$10",
	    "$11", "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo");
	return a3 ? -(int)v0 : (int)v0;
}

#define PAGE 8192U
/* The final writable segment in lab/irix-prda/probe.ld ends here. */
#define BASE 0x00802000U
#define GUARD (BASE + 8U * 1024 * 1024)
#define AT(addr) (*(volatile word *)(addr))
#define CALL(n, a, b, c, d) call(n, a, b, c, d, 0)

static char stack[4096] __attribute__((aligned(16)));
static word stage;
static int worker_status;

static int
resize(word end)
{
	return CALL(1017, end, 0, 0, 0);
}

static void
publish(word value)
{
	__atomic_store_n(&stage, value, __ATOMIC_RELEASE);
}

static void
wait_for(word value)
{
	while (__atomic_load_n(&stage, __ATOMIC_ACQUIRE) < value)
		CALL(1082, 1, 0, 0, 0);
}

static void
worker(void)
{
	publish(1);
	wait_for(2);
	if (AT(BASE + PAGE) != 37 || resize(BASE + 2 * PAGE + 1) != 0)
		worker_status = 5;
	else
		AT(BASE + 2 * PAGE) = 73;
	publish(3);
	wait_for(4);
	CALL(1130, 21, 1, 0, 0);
	for (;;) {}
}

static int
check(void)
{
	int fd = CALL(1005, PTR("/dev/zero"), 2, 0, 0);
	if (fd < 0 || call(1134, GUARD, PAGE, 3, 0x12, fd) != GUARD)
		return 1;
	AT(GUARD) = 91;
	if (resize(BASE + 2 * PAGE) || resize(BASE + PAGE))
		return 2;
	AT(BASE) = 19;
	word desc[] = { PTR(worker), 0, SHARE_FLAGS, PTR(stack + sizeof(stack)), 0 };
	if (CALL(1130, 20, 0, 0, 0) ||
	    CALL(1204, PTR(worker), SHARE_FLAGS, PTR(desc), 0) != 1)
		return 3;
	wait_for(1);
	if (resize(BASE + PAGE + 1))
		return 4;
	AT(BASE + PAGE) = 37;
	publish(2);
	wait_for(3);
	if (worker_status || AT(BASE + 2 * PAGE) != 73)
		return 5;
#ifdef LIMIT_ONLY
	/* Run separately with limited data or address-space headroom.
	 * This entire growth interval lies below the occupied guard. */
	int error = resize(BASE + 5U * 1024 * 1024);
	if (error == 0) {
		AT(BASE + 5U * 1024 * 1024 - sizeof(word)) = 101;
		return 6;
	}
	if (error != -12)
		return 11;
#else
	if (resize(GUARD + PAGE) >= 0)
		return 7;
#endif
	if (AT(GUARD) != 91 || AT(BASE + 2 * PAGE) != 73 ||
	    resize(BASE + 1) || resize(BASE + 3 * PAGE))
		return 8;
	if (AT(BASE) != 19 || AT(BASE + PAGE) || AT(BASE + 2 * PAGE))
		return 9;
	if (resize(BASE) != -122 || resize(0xffffffff) != -12 ||
	    AT(BASE) != 19 || AT(GUARD) != 91)
		return 10;
	publish(4);
	return 0;
}

void
_start(void)
{
	int status = check();
	if (status == 0) {
		static const char pass[] = "shared heap growth, shrink, zero fill and preserved mappings passed\n";
		CALL(1004, 1, PTR(pass), sizeof(pass) - 1, 0);
	}
	CALL(1001, status, 0, 0, 0);
	for (;;) {}
}
