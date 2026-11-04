/* Native o32 mount ABI regression. Run only in the disposable guest, as root.
 * The probe CD must already be mounted at /cdrom; no writes to the CD occur. */
#include <sys/types.h>
#include <sys/mount.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include "cd9660_mount.h"
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned checks, failures;
static const size_t old_size = offsetof(struct iso_args, uid);

static void check(const char *name, int ok, long got, long expected)
{
    ++checks; if (!ok) ++failures;
    printf("CD9660 %s %s got=%ld expected=%ld\n", ok ? "PASS" : "FAIL", name, got, expected);
}

static void query(size_t length, size_t expected_length, mode_t mask, mode_t dmask,
    uid_t uid, gid_t gid)
{
    struct { struct iso_args args; unsigned char tail[16]; } buffer;
    memset(&buffer, 0x5a, sizeof(buffer));
    errno = 0;
    int rc = mount(MOUNT_CD9660, "/cdrom", MNT_GETARGS, &buffer, length);
    check("getargs-size", rc == (int)expected_length, rc, expected_length);
    if (rc < 0) return;
    unsigned char *bytes = (unsigned char *)&buffer;
    int preserved = 1;
    for (size_t i = expected_length; i < sizeof(buffer); ++i)
        if (bytes[i] != 0x5a) preserved = 0;
    check("getargs-bounds", preserved, preserved, 1);
    if (expected_length != sizeof(struct iso_args)) return;
    check("getargs-uid", buffer.args.uid == uid, buffer.args.uid, uid);
    check("getargs-gid", buffer.args.gid == gid, buffer.args.gid, gid);
    check("getargs-fmask", buffer.args.fmask == mask, buffer.args.fmask, mask);
    check("getargs-dmask", buffer.args.dmask == dmask, buffer.args.dmask, dmask);
}

static void access_check(int allowed)
{
    pid_t child = fork();
    if (child < 0) { perror("fork"); exit(2); }
    if (!child) {
        if (setgroups(0, NULL) || setgid(1234) || setuid(1234)) _exit(2);
        int fd = open("/cdrom/guard-loop.sh", O_RDONLY);
        if (fd < 0) _exit(1);
        char byte;
        int ok = read(fd, &byte, 1) == 1;
        close(fd); _exit(ok ? 0 : 2);
    }
    int status;
    if (waitpid(child, &status, 0) != child) exit(2);
    int got = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    check("unprivileged-read", got == (allowed ? 0 : 1), got, allowed ? 0 : 1);
}

static void mount_case(const char *name, size_t length, mode_t mask, mode_t dmask,
    int guarded, int flags)
{
    printf("CD9660_CASE %s length=%zu guarded=%d\n", name, length, guarded);
    if (unmount("/cdrom", 0)) { perror("unmount"); exit(2); }
    struct iso_args args;
    memset(&args, 0, sizeof(args));
    args.fspec = "/dev/cd0a"; args.flags = flags;
    args.uid = 1234; args.gid = 1234; args.fmask = mask; args.dmask = dmask;
    void *data = &args, *mapping = MAP_FAILED;
    size_t page = (size_t)getpagesize(), capacity = length ? length : old_size;
    if (guarded) {
        mapping = mmap(NULL, page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
        if (mapping == MAP_FAILED || mprotect((char *)mapping + page, page, PROT_NONE)) exit(2);
        data = (char *)mapping + page - capacity;
        memcpy(data, &args, capacity);
    }
    int rc = mount(MOUNT_CD9660, "/cdrom", MNT_RDONLY, data, length);
    check("mount", rc == 0, rc, 0);
    if (mapping != MAP_FAILED) munmap(mapping, page * 2);
    if (rc) { perror("mount"); exit(2); }
    int legacy = length == 0 || length == old_size;
    mode_t effective = legacy ? 0777 : mask, effective_dir = legacy ? 0777 : dmask;
    struct stat st;
    if (stat("/cdrom/guard-loop.sh", &st)) { perror("stat"); exit(2); }
    check("file-mode", (st.st_mode & 0777) == (0644 & effective), st.st_mode & 0777, 0644 & effective);
    if (flags & ISOFSMNT_UID) check("file-owner", st.st_uid == 1234, st.st_uid, 1234);
    access_check(effective != 0);
    uid_t owner = !legacy && (flags & ISOFSMNT_UID) ? 1234 : 0;
    gid_t group = !legacy && (flags & ISOFSMNT_GID) ? 1234 : 0;
    query(sizeof(args), sizeof(args), effective, effective_dir, owner, group);
    query(sizeof(args) + 16, sizeof(args), effective, effective_dir, owner, group);
    query(old_size, old_size, 0, 0, 0, 0);
    query(0, old_size, 0, 0, 0, 0);
    /* A legacy update must keep the masks/owners of a modern mount. */
    if (!legacy && mask && (flags & ISOFSMNT_UID)) {
        rc = mount(MOUNT_CD9660, "/cdrom", MNT_RDONLY | MNT_UPDATE, &args, old_size);
        check("legacy-update", rc == 0, rc, 0);
        query(sizeof(args), sizeof(args), mask, dmask, 1234, 1234);
    }
    /* Old-size output at a guard page must not touch the new fields. */
    mapping = mmap(NULL, page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    if (mapping == MAP_FAILED || mprotect((char *)mapping + page, page, PROT_NONE)) exit(2);
    rc = mount(MOUNT_CD9660, "/cdrom", MNT_GETARGS, (char *)mapping + page - old_size, old_size);
    check("guarded-old-getargs", rc == (int)old_size, rc, old_size);
    munmap(mapping, page * 2);
}

int main(int argc, char **argv)
{
    if (getuid() != 0 || sizeof(void *) != 4) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    alarm(120);
    printf("CD9660_ABI old=%zu current=%zu\n", old_size, sizeof(struct iso_args));
    mount_case("modern-default", sizeof(struct iso_args), 0777, 0777, 0, 0);
    mount_case("modern-filtered", sizeof(struct iso_args), 0440, 0550, 0, ISOFSMNT_UID | ISOFSMNT_GID);
    mount_case("modern-zero", sizeof(struct iso_args), 0, 0, 0, 0);
    mount_case("legacy", old_size, 0, 0, 0, 0);
    mount_case("legacy-zero-length", 0, 0, 0, 0, 0);
    mount_case("guarded-legacy", old_size, 0, 0, 1, 0);
    mount_case("guarded-modern", sizeof(struct iso_args), 0777, 0777, 1, 0);
    struct iso_args args;
    memset(&args, 0, sizeof(args)); args.fspec = "/dev/cd0a";
    size_t lengths[] = {1, old_size - 1, old_size + 1, sizeof(args) - 1};
    for (unsigned i = 0; i < sizeof(lengths)/sizeof(lengths[0]); ++i) {
        for (unsigned j = 0; j < 2; ++j) {
            errno = 0;
            int rc = mount(MOUNT_CD9660, "/cdrom", j ? MNT_GETARGS : MNT_RDONLY, &args, lengths[i]);
            check("truncated-size", rc == -1 && errno == EINVAL, rc == -1 ? errno : 0, EINVAL);
        }
    }
    for (unsigned j = 0; j < 2; ++j) {
        errno = 0;
        int rc = mount(MOUNT_CD9660, "/cdrom", j ? MNT_GETARGS : MNT_RDONLY, (void *)-1, sizeof(args));
        check("faulted-copy", rc == -1 && errno == EFAULT, rc == -1 ? errno : 0, EFAULT);
    }
    printf("CD9660_RESULT checks=%u failures=%u\n", checks, failures);
    return argc == 2 && !strcmp(argv[1], "--diagnostic") ? 0 : failures != 0;
}
