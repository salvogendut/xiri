/* Run against an unused loopback port. Print raw ABI observations as words. */
typedef unsigned int word;
struct reply { word value, second, error; };
extern void probe_call(word, const word *, struct reply *);
#define PTR(p) ((word)(unsigned long)(p))

static int
call(word n, word a, word b, word c, word d, word e)
{
	word args[6] = { a, b, c, d, e, 0 };
	struct reply ret;
	probe_call(n, args, &ret);
	return ret.error ? -(int)ret.value : (int)ret.value;
}

int
main(void)
{
	int out[16], value = -1, length = 4;
	word address[4] = { 0x00029f91, 0x7f000001, 0, 0 };
	int fd = call(1107, 2, 2, 0, 0, 0);
	struct { int fd; short events, revents; } pollfd = { fd, 4, 0 };

	if (fd < 0)
		return 1;
	out[0] = call(1095, fd, 0xffff, 0x1007, PTR(&value), PTR(&length));
	out[1] = value;
	out[2] = length;
	out[3] = call(1062, fd, 4, 0x80, 0, 0);
	out[4] = call(1091, fd, PTR(address), sizeof(address), 0, 0);
	out[5] = call(1087, PTR(&pollfd), 1, 5000, 0, 0);
	out[6] = call(1095, fd, 0xffff, 0x1007, PTR(&value), PTR(&length));
	out[7] = value;
	out[8] = call(1095, fd, 0xffff, 0x1007, PTR(&value), PTR(&length));
	out[9] = value;
	length = 1;
	value = -1;
	out[10] = call(1095, fd, 0xffff, 0x1007, PTR(&value), PTR(&length));
	out[11] = value;
	out[12] = length;
	out[13] = call(1095, fd, 0xffff, 0x1007, PTR(&value), 0);
	out[14] = call(1095, -1, 0xffff, 0x1007, PTR(&value), PTR(&length));
	out[15] = call(1095, fd, 0xffff, 0x1007, 0, PTR(&length));
	return call(1004, 1, PTR(out), sizeof(out), 0, 0) == sizeof(out) ? 0 : 2;
}
