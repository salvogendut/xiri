/* Freestanding n32 control. Input is the existing elfmap-full-and-tail case. */
typedef unsigned int word;
#define PTR(x) ((word)(x))
#define ROUNDS 4
#define SHARE_FLAGS 0x020000ff
__asm__(".pushsection .note.probe,\"a\",@note\n"
    ".long 5,4,0x49524958\n.asciz \"Xiri\"\n.balign 4\n.long 1\n.popsection");

static int
call(word number, word x, word y, word z, word w)
{
	register word v0 __asm__("$2") = number;
	register word a0 __asm__("$4") = x, a1 __asm__("$5") = y;
	register word a2 __asm__("$6") = z, a3 __asm__("$7") = w;
	__asm__ volatile("syscall\n\tnop" : "+r"(v0), "+r"(a0), "+r"(a1),
	    "+r"(a2), "+r"(a3) : : "memory", "$1", "$3", "$8", "$9", "$10",
	    "$11", "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo");
	return a3 ? -(int)v0 : (int)v0;
}

struct phdr { word type, offset, va, pa, filesz, memsz, flags, align; };
static struct { char ehdr[52]; struct phdr loads[2]; } image;
static char stack[4096] __attribute__((aligned(16)));
static word started, mapped, finished, ready_to_exit;
static int bases[2][ROUNDS];

static void
publish(word *flag)
{
	__atomic_store_n(flag, 1, __ATOMIC_RELEASE);
}

static void
wait_for(word *flag)
{
	while (!__atomic_load_n(flag, __ATOMIC_ACQUIRE))
		call(1082, 1, 0, 0, 0);
}

static void
map_images(int fd, int row)
{
	for (int i = 0; i < ROUNDS; i++)
		bases[row][i] = call(1040, 68, fd, PTR(image.loads), 2);
}

static void
worker(int fd)
{
	publish(&started);
	wait_for(&mapped);
	map_images(fd, 1);
	publish(&finished);
	wait_for(&ready_to_exit);
	call(1130, 21, 1, 0, 0);
	for (;;) {}
}

static int
check(int fd)
{
	if (call(1003, fd, PTR(&image), sizeof(image), 0) != sizeof(image))
		return 2;
	if (image.loads[0].va != 0x0e000000 || image.loads[1].va != 0x0e020000 ||
	    image.loads[1].filesz != 0x1004)
		return 3;
	word desc[] = { PTR(worker), fd, SHARE_FLAGS, PTR(stack + sizeof(stack)), 0 };
	if (call(1130, 20, 0, 0, 0) || call(1204, PTR(worker), SHARE_FLAGS, PTR(desc), 0) != 1)
		return 4;
	wait_for(&started);
	publish(&mapped);
	map_images(fd, 0);
	wait_for(&finished);
	int at_preferred = 0;
	for (int row = 0; row < 2; row++) {
		for (int i = 0; i < ROUNDS; i++) {
			int base = bases[row][i];
			if (base <= 0)
				return 5;
			if ((word)base == image.loads[0].va)
				at_preferred++;
			int (*code)(void) = (void *)(base + 256);
			word *data = (void *)(base + 0x20000);
			if (code() != 0x13572468 || *data != 0x3c3c3c3c ||
			    data[0x1004/4] != 0 || data[0x2000/4] != 0)
				return 6;
			*data = 1 + row * ROUNDS + i;
		}
	}
	if (at_preferred != 1)
		return 7;
	struct phdr bad[2] = { image.loads[0], image.loads[1] };
	bad[1].offset = 0x400000;
	if (call(1040, 68, fd, PTR(bad), 2) >= 0)
		return 8;
#ifdef TEST_READ_ERROR
	/* The qualification-only module returns EIO on the 0x1003-byte
	 * tail read, after inserting both the text and the anonymous tail.
	 * Reusing the exact address verifies that both have been removed. */
	bad[0] = image.loads[0];
	bad[1] = image.loads[1];
	bad[0].va = bad[0].pa = 0x1e000000;
	bad[1].va = bad[1].pa = 0x1e020000;
	bad[1].filesz--;
	if (call(1040, 68, fd, PTR(bad), 2) != -5)
		return 10;
	bad[1].filesz++;
	if (call(1040, 68, fd, PTR(bad), 2) != (int)bad[0].va)
		return 11;
#endif
	for (int row = 0; row < 2; row++) {
		for (int i = 0; i < ROUNDS; i++) {
			volatile word *data = (void *)(bases[row][i] + 0x20000);
			if (*data != (word)(1 + row * ROUNDS + i))
				return 9;
		}
	}
	publish(&ready_to_exit);
	return 0;
}

void
_start(void)
{
	int fd = call(1005, PTR("elfmap-full-and-tail"), 0, 0, 0);
	int status = fd < 0 ? 1 : check(fd);
	if (status == 0) {
		static const char pass[] = "8 maps, executable text, private data, zero BSS and preserved markers passed\n";
		call(1004, 1, PTR(pass), sizeof(pass)-1, 0);
	}
	call(1001, status, 0, 0, 0);
	for (;;) {}
}
