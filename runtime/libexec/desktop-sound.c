/* Receive IRIX SoundScheme events on the user's display and play the donor's
 * named effects through the native NetBSD audio device. */
#include <sys/audioio.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <X11/Xlib.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define EFFECTS "/usr/local/share/xiri/sounds"
#define FULL_LEVEL 1000000

struct effect {
    Atom atom;
    unsigned sample;
};

static int
play(unsigned sample, long level)
{
    char path[64];
    int16_t buf[2048];
    audio_info_t info;
    snprintf(path, sizeof(path), EFFECTS "/%u.pcm", sample);
    int src = open(path, O_RDONLY);
    if (src < 0) return 1;
    int audio = open("/dev/audio", O_WRONLY);
    if (audio < 0) return 1;
    AUDIO_INITINFO(&info);
    info.play.encoding = AUDIO_ENCODING_SLINEAR_BE;
    info.play.precision = 16;
    info.play.channels = 2;
    info.play.sample_rate = 48000;
    if (ioctl(audio, AUDIO_SETINFO, &info) < 0) return 1;
    ssize_t n;
    while ((n = read(src, buf, sizeof(buf))) > 0) {
        if (n % sizeof(*buf)) return 1;
        if (level != FULL_LEVEL) {
            for (ssize_t i = 0; i < n / (ssize_t)sizeof(*buf); i++)
                buf[i] = (int64_t)buf[i] * level / FULL_LEVEL;
        }
        for (ssize_t pos = 0; pos < n;) {
            ssize_t written = write(audio, (char *)buf + pos, n - pos);
            if (written < 0 && errno == EINTR) continue;
            if (written <= 0) return 1;
            pos += written;
        }
    }
    return n < 0 || close(audio) < 0;
}

int
main(void)
{
    struct effect effects[256];
    size_t count = 0;
    char name[128];
    unsigned sample;
    Display *d = XOpenDisplay(NULL);
    if (!d) return 1;
    FILE *manifest = fopen(EFFECTS "/effects", "r");
    if (!manifest) return 1;
    while (fscanf(manifest, "%127s %u", name, &sample) == 2) {
        if (count == sizeof(effects) / sizeof(effects[0])) return 1;
        effects[count++] = (struct effect){ XInternAtom(d, name, False), sample };
    }
    if (!feof(manifest) || !count) return 1;
    fclose(manifest);
    Atom selection = XInternAtom(d, "_SGI_SoundScheme", False);
    Atom trigger = XInternAtom(d, "play", False);
    Atom mute = XInternAtom(d, "mute", False);
    Atom volume = XInternAtom(d, "level", False);
    Window win = XCreateSimpleWindow(d, DefaultRootWindow(d), 0, 0, 1, 1, 0, 0, 0);
    XGrabServer(d);
    if (XGetSelectionOwner(d, selection) != None) {
        XCloseDisplay(d);
        return 1;
    }
    XSetSelectionOwner(d, selection, win, CurrentTime);
    XUngrabServer(d);
    XSync(d, False);
    long level = FULL_LEVEL;
    int muted = 0;
    pid_t child = 0;
    for (;;) {
        XEvent event;
        XNextEvent(d, &event);
        if (child > 0 && waitpid(child, NULL, WNOHANG) == child) child = 0;
        if (event.type == SelectionClear) break;
        if (event.type != ClientMessage || event.xclient.window != win ||
            event.xclient.format != 32) continue;
        XClientMessageEvent *msg = &event.xclient;
        if (msg->message_type == mute) {
            muted = msg->data.l[1] != 0;
            if (muted && child > 0) kill(child, SIGTERM);
        } else if (msg->message_type == volume) {
            long value = msg->data.l[1];
            if (value >= 0 && value <= FULL_LEVEL) level = value;
        } else if (msg->message_type == trigger && !muted && level && child <= 0) {
            for (size_t i = 0; i < count; i++) {
                if (effects[i].atom != (Atom)msg->data.l[2]) continue;
                child = fork();
                if (child == 0) {
                    close(ConnectionNumber(d));
                    if (play(effects[i].sample, level)) {
                        perror("desktop sound");
                        _exit(1);
                    }
                    _exit(0);
                }
                break;
            }
        }
    }
    if (child > 0) {
        kill(child, SIGTERM);
        waitpid(child, NULL, 0);
    }
    XCloseDisplay(d);
    return 0;
}
