/* Xiri desktop media service for the first sgimips optical drive. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/cdio.h>
#include <sys/dkio.h>
#include <sys/mount.h>
#include <sys/scsiio.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/un.h>
#include <isofs/cd9660/cd9660_mount.h>
#include <dirent.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <util.h>

#define RUN "/var/run/xiri-cdrom"
#define DISC "/CDROM"
#define DEVICE "/dev/cd0a"
#define RAW "/dev/rcd0c"

static const struct sockaddr_un endpoint = {
    .sun_family = AF_LOCAL, .sun_path = RUN "/eject"
};
static volatile sig_atomic_t stopping;
static const char *published;
static time_t retry_at;
/* A forced tray change can leave a busy old mount behind. */
static int stale_mount;

static void
stop(int sig)
{
    (void)sig;
    stopping = 1;
}

static int
safe_directory(const char *path)
{
    struct stat st;
    if (mkdir(path, 0755) == -1 && errno != EEXIST)
        return 0;
    return lstat(path, &st) == 0 && S_ISDIR(st.st_mode) &&
        st.st_uid == 0 && !(st.st_mode & 022);
}

static int
empty_directory(const char *path)
{
    DIR *dir = opendir(path);
    if (!dir)
        return 0;
    struct dirent *entry;
    errno = 0;
    while ((entry = readdir(dir)) != NULL)
        if (strcmp(entry->d_name, ".") && strcmp(entry->d_name, ".."))
            break;
    int empty = entry == NULL && errno == 0;
    closedir(dir);
    return empty;
}

enum mounts { AVAILABLE, OWNED, IN_USE };

static enum mounts
mounts(void)
{
    struct statvfs *fs;
    int count = getmntinfo(&fs, ST_NOWAIT);
    enum mounts result = AVAILABLE;
    if (count == 0)
        return IN_USE;
    for (int i = 0; i < count; i++) {
        int at_disc = strcmp(fs[i].f_mntonname, DISC) == 0;
        const char *dev = fs[i].f_mntfromname;
        if (!at_disc && strncmp(dev, "/dev/cd0", 8) != 0)
            continue;
        if (!at_disc || strcmp(dev, DEVICE) || !(fs[i].f_flag & MNT_AUTOMOUNTED) ||
            access(RUN "/owned", F_OK) != 0)
            return IN_USE;
        result = OWNED;
    }
    return result;
}

static void
publish(const char *state)
{
    if (published && !strcmp(published, state))
        return;
    FILE *f = fopen(RUN "/next", "w");
    if (!f)
        return;
    int ok = fprintf(f, "XiriCD-%s\n", state) > 0;
    if (fclose(f) == 0 && ok && rename(RUN "/next", RUN "/CDROM") == 0)
        published = state;
}

/* The last address is the lead-out. All addresses include the MSF lead-in. */
struct audio_toc {
    unsigned first, count, start[100];
    int bus, target;
};
static struct audio_toc last_toc;

static int
audio_disc(int fd, struct audio_toc *toc)
{
    struct ioc_toc_header header;
    struct cd_toc_entry tracks[100] = {0};
    if (ioctl(fd, CDIOREADTOCHEADER, &header) < 0 || header.starting_track < 1 ||
        header.ending_track > 99 || header.ending_track < header.starting_track)
        return 0;
    toc->first = header.starting_track;
    toc->count = header.ending_track - header.starting_track + 1;
    struct ioc_read_toc_entry req = {
        .address_format = CD_MSF_FORMAT, .starting_track = header.starting_track,
        .data_len = (toc->count + 1) * sizeof(tracks[0]), .data = tracks
    };
    if (ioctl(fd, CDIOREADTOCENTRIES, &req) < 0)
        return 0;
    for (unsigned i = 0; i <= toc->count; i++) {
        if (i == toc->count ? tracks[i].track != 0xaa :
            (tracks[i].track != toc->first + i || (tracks[i].control & 4)))
            return 0;
        union msf_lba a = tracks[i].addr;
        toc->start[i] = (a.msf.minute * 60 + a.msf.second) * 75 + a.msf.frame;
        if (a.msf.second >= 60 || a.msf.frame >= 75 ||
            (i && toc->start[i] <= toc->start[i - 1]))
            return 0;
    }
    return 1;
}

#define SGI_DISC "/emul/irix/CDROM"
#define SGI_MTAB "/emul/irix/etc/mtab"
#define DISC_VIEW "/.." RUN "/disc"

static int
same_link(const char *path, const char *target)
{
    char buf[PATH_MAX];
    ssize_t n = readlink(path, buf, sizeof(buf));
    return n == (ssize_t)strlen(target) && !memcmp(buf, target, n);
}

static int
ensure_link(const char *path, const char *target)
{
    return symlink(target, path) == 0 || (errno == EEXIST && same_link(path, target));
}

static void
clear_music(void)
{
    unlink(RUN "/mtab");
    if (same_link(SGI_DISC, DISC_VIEW))
        unlink(SGI_DISC);
    last_toc.count = 0;
}

static void
print_time(FILE *f, unsigned frames)
{
    fprintf(f, "%02u:%02u:%02u\n", frames / 4500, frames / 75 % 60, frames % 75);
}

static int
finish_file(FILE *f, const char *from, const char *to)
{
    int ok = !ferror(f);
    return fclose(f) == 0 && ok && rename(from, to) == 0;
}

static void
publish_music(int fd, struct audio_toc *toc)
{
    struct scsi_addr addr;
    if (ioctl(fd, SCIOCIDENTIFY, &addr) < 0 || addr.type != TYPE_SCSI ||
        addr.addr.scsi.lun != 0)
        return;
    toc->bus = addr.addr.scsi.scbus;
    toc->target = addr.addr.scsi.target;
    if (!memcmp(toc, &last_toc, sizeof(*toc)))
        return;
    clear_music();
    if (!safe_directory(RUN "/disc") || !ensure_link(SGI_MTAB, "/.." RUN "/mtab"))
        return;
    FILE *f = fopen(RUN "/info.next", "w");
    if (!f)
        return;
    fputs("album.duration: ", f);
    print_time(f, toc->start[toc->count]);
    fprintf(f, "album.tracks: %u\n", toc->count);
    for (unsigned i = 0; i < toc->count; i++) {
        fprintf(f, "track%u.start: ", toc->first + i);
        print_time(f, toc->start[i]);
        fprintf(f, "track%u.duration: ", toc->first + i);
        /* mediad ends the final track one frame before the lead-out. */
        print_time(f, toc->start[i + 1] - toc->start[i] - (i + 1 == toc->count));
    }
    if (!finish_file(f, RUN "/info.next", RUN "/disc/info.disc") ||
        !ensure_link(SGI_DISC, DISC_VIEW))
        return;
    f = fopen(RUN "/mtab.next", "w");
    if (!f)
        return;
    fprintf(f, "/dev/scsi/sc%dd%dl0 /CDROM cdda ro,nosuid 0 0\n", toc->bus, toc->target);
    if (finish_file(f, RUN "/mtab.next", RUN "/mtab"))
        last_toc = *toc;
}

static void
refresh(void)
{
    enum mounts current = mounts();
    int fd = open(RAW, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        clear_music();
        unlink(RUN "/CDROM");
        published = NULL;
        return;
    }
    int ready = 0;
    int rc = ioctl(fd, DIOCTUR, &ready);
    struct audio_toc toc = {0};
    int music = rc == 0 && ready && current == AVAILABLE && audio_disc(fd, &toc);
    if (music)
        publish_music(fd, &toc);
    else
        clear_music();
    close(fd);
    if (rc < 0)
        return;
    if (!ready && current == OWNED)
        stale_mount = 1;
    if (stale_mount) {
        if (current == OWNED && unmount(DISC, 0) == 0) {
            unlink(RUN "/owned");
            current = AVAILABLE;
        }
        stale_mount = current == OWNED;
    }
    if (!ready) {
        publish("empty");
        retry_at = 0;
        return;
    }
    if (music) {
        retry_at = 0;
        publish("music");
        return;
    }
    if (current == AVAILABLE && time(NULL) >= retry_at) {
        unlink(RUN "/owned");
        struct iso_args args = { .fspec = DEVICE, .fmask = 0555, .dmask = 0555 };
        if (safe_directory(DISC) && empty_directory(DISC) &&
            mount(MOUNT_CD9660, DISC, MNT_RDONLY | MNT_NOSUID | MNT_NODEV |
                MNT_AUTOMOUNTED, &args, sizeof(args)) == 0) {
            int marker = open(RUN "/owned", O_WRONLY | O_CREAT, 0600);
            if (marker >= 0) {
                close(marker);
                current = OWNED;
            } else
                (void)unmount(DISC, 0);
        }
        retry_at = time(NULL) + 15;
    }
    publish(current == OWNED && !stale_mount ? "data" : "other");
}

static int
eject_disc(void)
{
    enum mounts current = mounts();
    if (current == IN_USE)
        return EBUSY;
    if (current == OWNED && unmount(DISC, 0) == -1)
        return errno;
    unlink(RUN "/owned");
    int fd = open(RAW, O_RDONLY | O_NONBLOCK);
    if (fd < 0)
        return errno;
    int force = 0;
    int error = ioctl(fd, DIOCEJECT, &force) < 0 ? errno : 0;
    close(fd);
    retry_at = 0;
    return error;
}

int
main(int argc, char **argv)
{
    int sock = socket(AF_LOCAL, SOCK_STREAM, 0);
    if (sock == -1)
        err(1, "socket");
    if (argc == 2 && !strcmp(argv[1], "--eject")) {
        if (connect(sock, (const struct sockaddr *)&endpoint, sizeof(endpoint)) < 0)
            err(1, "CD-ROM eject");
        int reply;
        if (recv(sock, &reply, sizeof(reply), MSG_WAITALL) != sizeof(reply))
            errx(1, "no eject result");
        if (reply)
            errx(1, "CD-ROM eject: %s", strerror(reply));
        return 0;
    }
    if (argc != 1 || getuid() != 0)
        errx(1, "usage: cdromd [--eject]");
    umask(022);
    if (!safe_directory(RUN))
        errx(1, "cannot use %s", RUN);
    if (daemon(0, 0) < 0 || pidfile("xiri_cdrom") < 0)
        return 1;
    unlink(endpoint.sun_path);
    /* As with IRIX mediad, local users can request an ordinary eject.
     * The socket accepts no arguments and grants no raw-device access. */
    if (bind(sock, (const struct sockaddr *)&endpoint, sizeof(endpoint)) < 0 ||
        chmod(endpoint.sun_path, 0666) < 0 || listen(sock, 4) < 0)
        return 1;
    signal(SIGTERM, stop);
    signal(SIGINT, stop);
    signal(SIGPIPE, SIG_IGN);
    struct pollfd pfd = { .fd = sock, .events = POLLIN };
    while (!stopping) {
        refresh();
        if (poll(&pfd, 1, 3000) > 0 && (pfd.revents & POLLIN)) {
            int client = accept(sock, NULL, NULL);
            if (client >= 0) {
                int result = eject_disc();
                (void)write(client, &result, sizeof(result));
                close(client);
            }
        }
    }
    if (mounts() == OWNED && unmount(DISC, 0) == 0)
        unlink(RUN "/owned");
    unlink(RUN "/CDROM");
    clear_music();
    unlink(endpoint.sun_path);
    return 0;
}
