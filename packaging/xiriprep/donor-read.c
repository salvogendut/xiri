/* SPDX-License-Identifier: GPL-2.0-only */
/* Read a file from the root XFS partition of a regular raw or CHD donor. */
#include <sys/stat.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <sha2.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libchdr/chd.h>
#include "xfs_directory.h"
#include "xfs_log.h"

struct donor {
	FILE *file;
	chd_file *chd;
	uint64_t start;
	uint32_t hunkbytes, cached;
	unsigned char *hunk;
};

static uint32_t
big32(const unsigned char *p)
{
	return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
	    (uint32_t)p[2] << 8 | p[3];
}

static int
read_image(void *cookie, uint64_t offset, void *out, size_t count, size_t *done)
{
	struct donor *d = cookie;
	unsigned char *dst = out;
	offset += d->start;
	*done = 0;
	if (d->chd == NULL) {
		ssize_t n;
		do {
			n = pread(fileno(d->file), dst, count, (off_t)offset);
		} while (n < 0 && errno == EINTR);
		if (n < 0)
			return errno;
		*done = (size_t)n;
		return 0;
	}
	while (*done < count) {
		uint32_t idx = offset / d->hunkbytes;
		uint32_t pos = offset % d->hunkbytes;
		size_t n = d->hunkbytes - pos;
		if (idx != d->cached) {
			chd_error e = chd_read(d->chd, idx, d->hunk);
			if (e != CHDERR_NONE) {
				warnx("CHD hunk %u: %s", idx, chd_error_string(e));
				return EIO;
			}
			d->cached = idx;
		}
		if (n > count - *done)
			n = count - *done;
		memcpy(dst + *done, d->hunk + pos, n);
		*done += n;
		offset += n;
	}
	return 0;
}

static struct xfs_io
open_root(struct donor *d, const char *path)
{
	unsigned char sector[512];
	struct stat st;
	uint32_t sum = 0;
	uint64_t size, length;
	const unsigned char *part;
	size_t done;
	unsigned root;
	int fd = open(path, O_RDONLY | O_NONBLOCK);
	if (fd == -1 || fstat(fd, &st) == -1)
		err(1, "%s", path);
	if (!S_ISREG(st.st_mode))
		errx(1, "supply a disk image file on a mounted filesystem");
	d->file = fdopen(fd, "rb");
	if (d->file == NULL)
		err(1, "fdopen");
	if (pread(fd, sector, 8, 0) != 8)
		errx(1, "cannot read disk image signature");
	size = (uint64_t)st.st_size;
	if (memcmp(sector, "MComprHD", 8) == 0) {
		chd_error e = chd_open_file(d->file, CHD_OPEN_READ, NULL, &d->chd);
		if (e != CHDERR_NONE)
			errx(1, "%s: %s", path, chd_error_string(e));
		const chd_header *header = chd_get_header(d->chd);
		size = header->logicalbytes;
		d->hunkbytes = header->hunkbytes;
		d->cached = UINT32_MAX;
		d->hunk = malloc(d->hunkbytes);
		if (d->hunk == NULL)
			err(1, "allocate CHD hunk");
	}
	if (read_image(d, 0, sector, sizeof(sector), &done) || done != sizeof(sector))
		errx(1, "cannot read SGI volume header");
	for (size_t i = 0; i < sizeof(sector); i += 4)
		sum += big32(sector + i);
	root = (unsigned)sector[4] << 8 | sector[5];
	if (big32(sector) != 0x0be5a941 || sum != 0 || root >= 16)
		errx(1, "invalid SGI volume header or root partition number");
	/* SGI volume header partition table: block count, first block, type. */
	part = sector + 312 + 12 * root;
	length = (uint64_t)big32(part) * sizeof(sector);
	d->start = (uint64_t)big32(part + 4) * sizeof(sector);
	if (big32(part + 8) != 10 || length == 0 || d->start > size ||
	    length > size - d->start)
		errx(1, "invalid or truncated SGI root XFS partition");
	return (struct xfs_io){ .cookie = d, .size = length, .read = read_image };
}

int
main(int argc, char **argv)
{
	static unsigned char scratch[XFS_DIR_WORKSPACE_SIZE], buf[64 * 1024];
	struct donor donor = {0};
	struct xfs_path_workspace path;
	struct xfs_inode_image file;
	struct xfs_reader reader;
	uint64_t ino, offset = 0;
	const char *why = NULL;
	const char *expected = NULL;
	int fingerprint = argc == 4 && strcmp(argv[1], "--sha256") == 0;
	FILE *verified = NULL;
	SHA256_CTX hash;
	char hex[SHA256_DIGEST_STRING_LENGTH];
	if (fingerprint) {
		argv++;
		argc--;
	} else if (argc == 5 && strcmp(argv[1], "--expect-sha256") == 0) {
		expected = argv[2];
		if (strlen(expected) != 64 || strspn(expected, "0123456789abcdef") != 64)
			errx(2, "invalid expected SHA256");
		argv += 2;
		argc -= 2;
	}
	if (argc != 3 || argv[2][0] != '/')
		errx(2, "usage: xiri-donor-read [--sha256 | --expect-sha256 digest] disk-image /path/inside/donor");
	struct xfs_io io = open_root(&donor, argv[1]);
	/* On a snapshot without a clean unmount, only expose a checksum or
	 * bytes that exactly match a digest from the destination's profile. */
	if (xfs_reader_open(&io, scratch, sizeof(scratch), &reader, &why) ||
	    (!fingerprint && !expected && xfs_require_clean_log(&reader, scratch, sizeof(scratch), &why)) ||
	    xfs_lookup_path(&reader, argv[2], strlen(argv[2]), true, &path,
	        scratch, sizeof(scratch), &ino, &why) ||
	    xfs_read_inode(&reader, ino, scratch, sizeof(scratch), &file, &why))
		errx(1, "%s: %s", argv[2], why ? why : "XFS read failed");
	if (!S_ISREG(file.mode))
		errx(1, "%s is not a regular donor file", argv[2]);
	if (expected != NULL && (verified = tmpfile()) == NULL)
		err(1, "create temporary file for verified export");
	if (fingerprint || expected)
		SHA256_Init(&hash);
	while (offset < file.size) {
		size_t done;
		if (xfs_read_file(&reader, &file, offset, buf, sizeof(buf), &done,
		    scratch, sizeof(scratch), &why) || done == 0)
			errx(1, "%s: %s", argv[2], why ? why : "short XFS read");
		if (fingerprint || expected)
			SHA256_Update(&hash, buf, done);
		if (!fingerprint && fwrite(buf, 1, done, verified ? verified : stdout) != done)
			err(1, "write");
		offset += done;
	}
	if (fingerprint)
		puts(SHA256_End(&hash, hex));
	if (verified != NULL) {
		if (strcmp(expected, SHA256_End(&hash, hex)) != 0)
			errx(1, "%s: content differs from the profile", argv[2]);
		if (fseeko(verified, 0, SEEK_SET) != 0)
			err(1, "rewind verified file");
		size_t n;
		while ((n = fread(buf, 1, sizeof(buf), verified)) != 0) {
			if (fwrite(buf, 1, n, stdout) != n)
				err(1, "write");
		}
		if (ferror(verified))
			err(1, "read verified file");
		fclose(verified);
	}
	if (fflush(stdout))
		err(1, "write");
	if (donor.chd != NULL)
		chd_close(donor.chd);
	free(donor.hunk);
	fclose(donor.file);
	return 0;
}
