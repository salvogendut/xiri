/* SPDX-License-Identifier: GPL-2.0-only */
/* Read a file from the root XFS partition of a regular raw or CHD donor. */
#include <sys/stat.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
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
	uint32_t hunkbytes, slots, cached[256];
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
		uint32_t slot = idx % d->slots;
		unsigned char *block = d->hunk + (size_t)slot * d->hunkbytes;
		if (idx != d->cached[slot]) {
			chd_error e = chd_read(d->chd, idx, block);
			if (e != CHDERR_NONE) {
				warnx("CHD hunk %u: %s", idx, chd_error_string(e));
				return EIO;
			}
			d->cached[slot] = idx;
		}
		if (n > count - *done)
			n = count - *done;
		memcpy(dst + *done, block + pos, n);
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
		if (!d->hunkbytes)
			errx(1, "invalid CHD hunk size");
		d->slots = 1;
		while (d->slots < 256 && d->hunkbytes <= (4U << 20) / (2 * d->slots))
			d->slots *= 2;
		memset(d->cached, 0xff, sizeof(d->cached));
		d->hunk = malloc((size_t)d->slots * d->hunkbytes);
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

static unsigned char scratch[XFS_DIR_WORKSPACE_SIZE], buf[64 * 1024];

static struct xfs_inode_image
lookup(struct xfs_reader *reader, const char *source, bool follow)
{
	struct xfs_path_workspace path;
	struct xfs_inode_image file;
	uint64_t ino;
	const char *why = NULL;
	if (xfs_lookup_path(reader, source, strlen(source), follow, &path,
	    scratch, sizeof(scratch), &ino, &why) ||
	    xfs_read_inode(reader, ino, scratch, sizeof(scratch), &file, &why))
		errx(1, "%s: %s", source, why ? why : "XFS lookup failed");
	return file;
}

static void
copy_file(struct xfs_reader *reader, const char *source, struct xfs_inode_image *file,
    FILE *output, char *digest)
{
	SHA256_CTX hash;
	const char *why = NULL;
	if (!S_ISREG(file->mode))
		errx(1, "%s is not a regular donor file", source);
	SHA256_Init(&hash);
	for (uint64_t offset = 0; offset < file->size;) {
		size_t done;
		if (xfs_read_file(reader, file, offset, buf, sizeof(buf), &done,
		    scratch, sizeof(scratch), &why) || done == 0)
			errx(1, "%s: %s", source, why ? why : "short XFS read");
		if (output && fwrite(buf, 1, done, output) != done)
			err(1, "write %s", source);
		SHA256_Update(&hash, buf, done);
		offset += done;
	}
	SHA256_End(&hash, digest);
}

static void
directory(const char *name)
{
	struct stat st;
	if (mkdir(name, 0755) == -1 &&
	    (errno != EEXIST || lstat(name, &st) == -1 || !S_ISDIR(st.st_mode)))
		errx(1, "cannot create staging directory %s", name);
}

/* The caller supplies a newly created private staging directory. Never walk
 * a host symlink, including the absolute links imported for IRIX clients. */
static void
extract(struct xfs_reader *reader, FILE *plan)
{
	char *line = NULL;
	size_t cap = 0, nfiles = 0;
	ssize_t length;
	while ((length = getline(&line, &cap, plan)) >= 0) {
		char dest[PATH_MAX], hex[SHA256_DIGEST_STRING_LENGTH];
		char *row = line, *kind = strsep(&row, "|"), *mode = strsep(&row, "|");
		char *source = strsep(&row, "|"), *override = strsep(&row, "|");
		if (!row || !mode || !source || !override || strlen(kind) != 1 ||
		    source[0] != '/' || !length || line[length - 1] != '\n')
			errx(1, "invalid desktop plan");
		line[length - 1] = 0;
		int len = *override ? snprintf(dest, sizeof(dest), ".%s", override) :
		    snprintf(dest, sizeof(dest), "./emul/irix%s", source);
		if (len < 0 || (size_t)len >= sizeof(dest) ||
		    (strncmp(dest, "./emul/irix/", 12) && strncmp(dest, "./usr/local/share/xiri/fonts/", 29)) ||
		    strstr(dest, "/../") || strstr(dest, "/./") || strstr(dest, "//") ||
		    !strcmp(strrchr(dest, '/'), "/..") || !strcmp(strrchr(dest, '/'), "/.") ||
		    dest[len - 1] == '/')
			errx(1, "invalid plan destination for %s", source);
		for (char *part = dest + 2; (part = strchr(part, '/')) != NULL; part++) {
			*part = 0;
			directory(dest);
			*part = '/';
		}
		struct xfs_inode_image file = lookup(reader, source, *kind == 'f');
		if (*kind == 'd' && S_ISDIR(file.mode)) {
			directory(dest);
		} else if (*kind == 's' && S_ISLNK(file.mode)) {
			size_t done;
			const char *why = NULL;
			if (file.size != strlen(row) || file.size >= sizeof(buf) ||
			    xfs_read_file(reader, &file, 0, buf, sizeof(buf), &done,
			        scratch, sizeof(scratch), &why) || done != file.size ||
			    memcmp(buf, row, done) || symlink(row, dest) == -1)
				errx(1, "%s: catalog or resource link differs or cannot be created", source);
		} else if (*kind == 'f' && (!strcmp(mode, "0444") || !strcmp(mode, "0555"))) {
			FILE *out = fopen(dest, "wx");
			if (!out)
				err(1, "%s", dest);
			copy_file(reader, source, &file, out, hex);
			if (strcmp(hex, row))
				errx(1, "%s: content differs from the profile", source);
			if (fchmod(fileno(out), !strcmp(mode, "0555") ? 0555 : 0444) || fclose(out))
				err(1, "%s", dest);
		} else {
			errx(1, "%s: unexpected plan or inode type", source);
		}
		if (++nfiles % 200 == 0)
			fprintf(stderr, "Verified %zu desktop entries\n", nfiles);
	}
	if (ferror(plan) || !nfiles)
		errx(1, "empty or unreadable desktop plan");
	free(line);
}

int
main(int argc, char **argv)
{
	struct donor donor = {0};
	struct xfs_reader reader;
	const char *why = NULL, *expected = NULL;
	FILE *verified = NULL, *plan = NULL;
	char hex[SHA256_DIGEST_STRING_LENGTH];
	bool fingerprint = argc == 4 && !strcmp(argv[1], "--sha256");
	if (fingerprint) {
		argv++; argc--;
	} else if (argc == 5 && !strcmp(argv[1], "--expect-sha256")) {
		expected = argv[2];
		if (strlen(expected) != 64 || strspn(expected, "0123456789abcdef") != 64)
			errx(2, "invalid expected SHA256");
		argv += 2; argc -= 2;
	} else if (argc == 5 && !strcmp(argv[1], "--extract")) {
		if (!(plan = fopen(argv[2], "r")))
			err(1, "open desktop plan");
		argv += 2; argc -= 2;
	}
	if (argc != 3 || (!plan && argv[2][0] != '/'))
		errx(2, "usage: xiri-donor-read [--sha256 | --expect-sha256 digest] image /source\n"
		    "       xiri-donor-read --extract plan image private-directory");
	struct xfs_io io = open_root(&donor, argv[1]);
	if (xfs_reader_open(&io, scratch, sizeof(scratch), &reader, &why) ||
	    (!plan && !fingerprint && !expected &&
	    xfs_require_clean_log(&reader, scratch, sizeof(scratch), &why)))
		errx(1, "%s: %s", argv[1], why ? why : "XFS read failed");
	if (plan) {
		if (chdir(argv[2]) == -1)
			err(1, "%s", argv[2]);
		extract(&reader, plan);
		fclose(plan);
	} else {
		struct xfs_inode_image file = lookup(&reader, argv[2], true);
		if (expected && !(verified = tmpfile()))
			err(1, "create temporary file for verified export");
		copy_file(&reader, argv[2], &file, fingerprint ? NULL : verified ? verified : stdout, hex);
		if (fingerprint)
			puts(hex);
		if (expected) {
			if (strcmp(hex, expected))
				errx(1, "%s: content differs from the profile", argv[2]);
			if (fseeko(verified, 0, SEEK_SET))
				err(1, "rewind verified file");
			size_t n;
			while ((n = fread(buf, 1, sizeof(buf), verified)) > 0)
				if (fwrite(buf, 1, n, stdout) != n)
					err(1, "write");
			if (ferror(verified))
				err(1, "read verified file");
			fclose(verified);
		}
	}
	if (fflush(stdout))
		err(1, "write");
	if (donor.chd)
		chd_close(donor.chd);
	free(donor.hunk);
	fclose(donor.file);
	return 0;
}
