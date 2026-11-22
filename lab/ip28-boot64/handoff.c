/* SPDX-License-Identifier: BSD-2-Clause */
/* Standalone ELF64 payload: validate the loader's data, BSS and bootinfo. */
typedef unsigned long u64;
typedef long (*write_fn)(u64, const void *, u64, u64 *);

struct btinfo {
	u64 next;
	int type;
};

static volatile u64 initialized = 0x1122334455667788UL;
static volatile u64 zeroed[1024];

static void
message(const char *s)
{
	const u64 *vector = *(const u64 *const *)0xffffffffa0001040UL;
	write_fn write = (write_fn)vector[27];
	u64 n = 0, done = 0;

	while (s[n] != 0)
		n++;
	(void)write(1, s, n, &done);
}

int
probe(int argc, char **argv, int magic, const void *bootinfo)
{
	const struct btinfo *bi = bootinfo;
	int have_magic = 0, have_path = 0, have_symbols = 0;
	u64 offset = 0, i;

	if (initialized != 0x1122334455667788UL)
		goto fail;
	for (i = 0; i < sizeof(zeroed) / sizeof(zeroed[0]); i++)
		if (zeroed[i] != 0)
			goto fail;
	if (argc < 1 || argc > 32 || argv == (void *)0 ||
	    argv[0] == (void *)0 || argv[0][0] == 0 || magic != 0x20080808)
		goto fail;
	while (offset + sizeof(*bi) <= 1024) {
		bi = (const void *)((const char *)bootinfo + offset);
		if (bi->type == 0)
			break;
		if (bi->next < sizeof(*bi) || bi->next > 1024 - offset)
			goto fail;
		if (bi->type == 1 &&
		    *(const int *)((const char *)bi + sizeof(*bi)) == magic)
			have_magic = 1;
		if (bi->type == 2 &&
		    ((const char *)bi)[sizeof(*bi)] != 0)
			have_path = 1;
		if (bi->type == 3)
			have_symbols = 1;
		offset += bi->next;
	}
	if (!have_magic || !have_path || !have_symbols)
		goto fail;
	message("XIRI_IP28_LOADER_HANDOFF_PASS: data BSS argv bootinfo\r\n");
	return 0;
fail:
	message("XIRI_IP28_LOADER_HANDOFF_FAIL\r\n");
	return 1;
}
