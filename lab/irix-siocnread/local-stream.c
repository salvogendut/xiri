/* n32 SIOCNREAD on a connected Unix stream, as used by local X clients. */
typedef unsigned int word;
extern void probe_call(word, const word *, word *);
#define PTR(p) ((word)(p))

static int
trap(word number, word a, word b, word c, word d)
{
	word args[] = {a, b, c, d, 0, 0}, result[3];
	probe_call(number, args, result);
	return result[2] ? -(int)result[0] : (int)result[0];
}

static int
queued(int fd, int expected)
{
	int count = -1;
	return trap(1054, fd, 0x4004730a, PTR(&count), 0) == 0 &&
	    count == expected;
}

#define report(s) trap(1004, 1, PTR(s), sizeof(s) - 1, 0)

int
main(void)
{
	int pair[2], count = -1;
	char bytes[3];

	if (trap(1155, 1, 2, 0, PTR(pair)) != 0)
		return 1;
	if (!queued(pair[1], 0))
		return 2;
	if (trap(1004, pair[0], PTR("abc"), 3, 0) != 3 || !queued(pair[1], 3))
		return 3;
	if (trap(1003, pair[1], PTR(bytes), 1, 0) != 1 ||
	    bytes[0] != 'a' || !queued(pair[1], 2))
		return 4;
	if (trap(1003, pair[1], PTR(bytes), 2, 0) != 2 ||
	    bytes[0] != 'b' || bytes[1] != 'c' || !queued(pair[1], 0))
		return 5;
	report("queued=0,3,2,0\n");

	if (trap(1006, pair[0], 0, 0, 0) != 0 ||
	    trap(1003, pair[1], PTR(bytes), 1, 0) != 0)
		return 6;
	int rc = trap(1054, pair[1], 0x4004730a, PTR(&count), 0);
	if (rc == 0 && count == 0)
		report("eof=0\n");
	else if (rc == -131 && count == -1)
		report("eof=ECONNRESET\n");
	else
		return 7;
	return 0;
}
