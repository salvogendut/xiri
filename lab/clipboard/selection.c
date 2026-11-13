/* Native Xlib observation/control for real IRIX/native clipboard clients.
 * A bounded lab fixture, not a clipboard manager. One INCR receiver at a time.
 */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define LIMIT (16UL * 1024 * 1024)
static Display *d;
static Window w;
static Atom incr, prop, targets;

static void die(const char *s) { perror(s); exit(2); }
static void expired(int s) { (void)s; _exit(124); }
static Atom atom(const char *s) { return XInternAtom(d, s, False); }
static unsigned char *property(Window win, Atom p, Atom *type, int *fmt,
    unsigned long *n, Bool del)
{
    unsigned char *data = NULL;
    unsigned long after;
    if (XGetWindowProperty(d, win, p, 0, LIMIT / 4, del, AnyPropertyType,
        type, fmt, n, &after, &data) != Success || after) {
        fprintf(stderr, "property failed or exceeds limit\n"); exit(2);
    }
    return data;
}
static void state(void)
{
    const char *names[] = {"PRIMARY", "CLIPBOARD", "CLIPBOARD_MANAGER"};
    for (unsigned i = 0; i < sizeof names / sizeof names[0]; i++)
        printf("%s owner=0x%lx\n", names[i], XGetSelectionOwner(d, atom(names[i])));
    for (unsigned i = 0; i < 8; i++) {
        char name[32]; Atom type; int fmt; unsigned long n;
        snprintf(name, sizeof name, "CUT_BUFFER%u", i);
        unsigned char *data = property(DefaultRootWindow(d), atom(name), &type, &fmt, &n, False);
        printf("%s bytes=%lu\n", name, n * (unsigned long)fmt / 8);
        XFree(data);
    }
}
static int receive(Atom sel, Atom target, const char *path)
{
    if (XGetSelectionOwner(d, sel) == None) {
        fprintf(stderr, "no selection owner\n"); return 4;
    }
    XConvertSelection(d, sel, target, prop, w, CurrentTime);
    XEvent ev;
    do { XNextEvent(d, &ev); } while (ev.type != SelectionNotify);
    if (ev.xselection.property == None) {
        fprintf(stderr, "target refused\n"); return 5;
    }
    Atom type; int fmt; unsigned long n;
    unsigned char *data = property(w, prop, &type, &fmt, &n, False);
    FILE *out = fopen(path, "wb");
    if (!out) die(path);
    unsigned long total = 0, chunks = 0;
    int incremental = type == incr;
    if (incremental) {
        if (fmt != 32 || n != 1) { fprintf(stderr, "malformed INCR\n"); return 2; }
        XFree(data); data = NULL;
        XDeleteProperty(d, w, prop); XFlush(d);
    }
    for (;;) {
        if (incremental) {
            do { XNextEvent(d, &ev); } while (ev.type != PropertyNotify ||
                ev.xproperty.atom != prop || ev.xproperty.state != PropertyNewValue);
            data = property(w, prop, &type, &fmt, &n, True);
            /* Ignore the already-consumed INCR announcement still in our queue. */
            if (type == None) { XFree(data); data = NULL; continue; }
        }
        /* Some older clients label this TARGETS, rather than ATOM. Report
         * the returned type below, but still inspect the advertised atoms. */
        if (target == targets && fmt == 32) {
            for (unsigned long i = 0; i < n; i++) {
                char *name = XGetAtomName(d, ((Atom *)data)[i]);
                fprintf(out, "%s\n", name ? name : "unknown");
                if (name) XFree(name);
            }
        } else {
            if (fmt != 8 || total + n > LIMIT) {
                char *name = XGetAtomName(d, type);
                fprintf(stderr, "unexpected type=%s format=%d or transfer too large\n",
                    name ? name : "unknown", fmt);
                if (name) XFree(name);
                return 2;
            }
            if (n && fwrite(data, 1, n, out) != n) die("write");
        }
        total += n; chunks++;
        XFree(data); data = NULL;
        XFlush(d);
        if (!incremental || !n) break;
    }
    if (fclose(out)) die("close");
    char *name = XGetAtomName(d, type);
    printf("received type=%s format=%d items=%lu chunks=%lu incr=%d\n",
        name ? name : "unknown", fmt, total, chunks, incremental);
    if (name) XFree(name);
    return 0;
}
static int serve(Atom sel, Atom encoding, const char *path, unsigned long chunk)
{
    FILE *in = fopen(path, "rb");
    if (!in) die(path);
    unsigned char *data = malloc(LIMIT + 1);
    if (!data) die("malloc");
    size_t size = fread(data, 1, LIMIT + 1, in);
    if (ferror(in) || size > LIMIT) { fprintf(stderr, "input too large or unreadable\n"); return 2; }
    fclose(in);
    if (chunk < 1 || chunk > 65536) { fprintf(stderr, "chunk outside 1..65536\n"); return 2; }
    XSetSelectionOwner(d, sel, w, CurrentTime);
    XSync(d, False);
    if (XGetSelectionOwner(d, sel) != w) { fprintf(stderr, "ownership failed\n"); return 2; }
    printf("owner=0x%lx bytes=%zu chunk=%lu\n", w, size, chunk); fflush(stdout);
    Window requestor = None; Atom pending = None;
    size_t offset = 0;
    for (;;) {
        XEvent ev; XNextEvent(d, &ev);
        if (ev.type == SelectionClear) { puts("selection replaced"); break; }
        if (ev.type == PropertyNotify && requestor != None &&
            ev.xproperty.window == requestor && ev.xproperty.atom == pending &&
            ev.xproperty.state == PropertyDelete) {
            size_t length = size - offset;
            if (length > chunk) length = chunk;
            XChangeProperty(d, requestor, pending, encoding, 8, PropModeReplace, data + offset, length);
            offset += length;
            if (!length) { requestor = None; puts("INCR complete"); fflush(stdout); }
            XFlush(d);
        }
        if (ev.type != SelectionRequest) continue;
        XSelectionRequestEvent *r = &ev.xselectionrequest;
        Atom p = r->property == None ? r->target : r->property;
        XSelectionEvent reply = { .type = SelectionNotify, .display = d,
            .requestor = r->requestor, .selection = r->selection, .target = r->target,
            .property = None, .time = r->time };
        char *name = XGetAtomName(d, r->target);
        printf("request target=%s\n", name ? name : "unknown"); fflush(stdout);
        if (name) XFree(name);
        if (r->target == targets) {
            Atom supported[] = { targets, encoding, atom("TEXT") };
            XChangeProperty(d, r->requestor, p, XA_ATOM, 32, PropModeReplace,
                (unsigned char *)supported, 3);
            reply.property = p;
        } else if ((r->target == encoding || r->target == atom("TEXT")) && requestor == None) {
            if (size > chunk) {
                requestor = r->requestor; pending = p; offset = 0;
                unsigned long length = size;
                XSelectInput(d, requestor, PropertyChangeMask);
                XChangeProperty(d, requestor, p, incr, 32, PropModeReplace,
                    (unsigned char *)&length, 1);
            } else XChangeProperty(d, r->requestor, p, encoding, 8, PropModeReplace, data, size);
            reply.property = p;
        }
        XSendEvent(d, r->requestor, False, 0, (XEvent *)&reply);
        XFlush(d);
    }
    free(data); return 0;
}
int main(int argc, char **argv)
{
    if (argc < 2) return 2;
    signal(SIGALRM, expired); alarm(!strcmp(argv[1], "serve") ? 600 : 45);
    d = XOpenDisplay(NULL);
    if (!d) { fprintf(stderr, "cannot open DISPLAY\n"); return 2; }
    w = XCreateSimpleWindow(d, DefaultRootWindow(d), 0, 0, 1, 1, 0, 0, 0);
    XSelectInput(d, w, PropertyChangeMask);
    incr = atom("INCR"); prop = atom("XIRI_SELECTION_TEST"); targets = atom("TARGETS");
    int rc = 2;
    if (argc == 2 && !strcmp(argv[1], "state")) { state(); rc = 0; }
    if (argc == 5 && !strcmp(argv[1], "get")) rc = receive(atom(argv[2]), atom(argv[3]), argv[4]);
    if (argc == 6 && !strcmp(argv[1], "serve")) rc = serve(atom(argv[2]), atom(argv[3]), argv[4], strtoul(argv[5], NULL, 0));
    XCloseDisplay(d); return rc;
}
