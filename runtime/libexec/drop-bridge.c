/* Translate local IRIX file-icon drops to XDND URI lists.
 * Wire references: SGI ViewKit Cut and Paste, GTK 1.2.10 gdkdnd.c,
 * and the freedesktop XDND specification. See docs/IRIX-DOCUMENTS.md.
 * This is an X client in the authenticated user's supervised session.
 */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/select.h>
#include "drop-files.h"

static Display *display;
static Window root, owner;
static char hostname[256];
static volatile sig_atomic_t stopping;
static Atom motif, receiver, initiator, drag_window, drag_targets, sgi_icon;
static Atom aware, enter, position, status, leave, drop, finished, selection, copy;
static Atom uri, targets, timestamp_atom, data_property, ack_property, singleton;
static Atom success, failure;

struct receiver {
    Window window, proxy;
    int had_motif, version;
    unsigned char original[16];
    struct receiver *next;
};
static struct receiver *receivers;
static struct {
    int mode;                       /* 0 idle, 1 untouched Motif relay, 2 translation */
    Window source, dest;
    Atom selection;
    Time time, first_time, sent_time, drop_time;
    int version, x, y, sent_x, sent_y, operation, accepted, copy_allowed;
    int waiting_status, drop_pending, drop_sent, requested, served;
    long long leave_due, deadline;
    char *uris;
    size_t length;
    unsigned files;
    XSelectionRequestEvent pending[8];
    unsigned pending_count;
} drag;

static long long now_ms(void)
{
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}
static uint32_t wire(const unsigned char *p, int bytes, int little)
{
    uint32_t n = 0;
    for (int i = 0; i < bytes; i++) n = (n << 8) | p[little ? bytes - 1 - i : i];
    return n;
}
static void put(unsigned char *p, uint32_t n, int bytes)
{
    for (int i = bytes - 1; i >= 0; i--) { p[i] = n; n >>= 8; }
}
static unsigned char *property(Window w, Atom key, Atom wanted, int format,
    unsigned long *count)
{
    Atom actual; int bits; unsigned long after; unsigned char *data = NULL;
    if (XGetWindowProperty(display, w, key, 0, XIRI_DROP_LIMIT / 4, False,
        wanted, &actual, &bits, count, &after, &data) != Success ||
        actual != wanted || bits != format || after) {
        if (data) XFree(data);
        return NULL;
    }
    return data;
}
static void xdnd(Atom kind, long a, long b, long c, long d)
{
    XEvent event = {0}; event.xclient.type = ClientMessage;
    event.xclient.window = drag.dest; event.xclient.message_type = kind;
    event.xclient.format = 32; event.xclient.data.l[0] = owner;
    event.xclient.data.l[1] = a; event.xclient.data.l[2] = b;
    event.xclient.data.l[3] = c; event.xclient.data.l[4] = d;
    XSendEvent(display, drag.dest, False, 0, &event);
}
static void motif_reply(int operation, int flags, Time time)
{
    XEvent event = {0}; event.xclient.type = ClientMessage;
    event.xclient.window = drag.source; event.xclient.message_type = motif;
    event.xclient.format = 8;
    unsigned char *p = (unsigned char *)event.xclient.data.b;
    p[0] = operation | 128; p[1] = 'B'; put(p + 2, flags, 2);
    put(p + 4, time, 4); put(p + 8, drag.sent_x, 2); put(p + 10, drag.sent_y, 2);
    XSendEvent(display, drag.source, False, 0, &event);
}
static void selection_reply(XSelectionRequestEvent *request, int valid)
{
    XEvent event = {0}; event.xselection.type = SelectionNotify;
    event.xselection.requestor = request->requestor;
    event.xselection.selection = request->selection;
    event.xselection.target = request->target; event.xselection.time = request->time;
    event.xselection.property = valid ? (request->property ? request->property : request->target) : None;
    XSendEvent(display, request->requestor, False, 0, &event);
}
static void reset(void)
{
    for (unsigned i = 0; i < drag.pending_count; i++) selection_reply(&drag.pending[i], 0);
    if (XGetSelectionOwner(display, selection) == owner)
        XSetSelectionOwner(display, selection, None, CurrentTime);
    free(drag.uris); memset(&drag, 0, sizeof(drag));
}
static void complete(int ok)
{
    if (drag.mode == 2) {
        if (!drag.drop_sent) xdnd(leave, 0, 0, 0, 0);
        if (drag.drop_pending) {
            if (!drag.drop_sent) motif_reply(5, 0x2010, drag.drop_time);
            XConvertSelection(display, drag.selection, ok ? success : failure,
                ack_property, owner, drag.drop_time);
            fprintf(stderr, "drop files=%u transfer=%s\n", drag.files, ok ? "complete" : "rejected");
        }
    }
    reset();
}
static int source_has_icons(Window source, Atom key, Atom *sel)
{
    unsigned long n;
    unsigned char *p = property(source, key, initiator, 8, &n);
    if (!p) return 0;
    int valid = n == 8 && (p[0] == 'B' || p[0] == 'l') && p[1] == 0;
    unsigned index = valid ? wire(p + 2, 2, p[0] == 'l') : 0;
    *sel = valid ? wire(p + 4, 4, p[0] == 'l') : None; XFree(p);
    if (!valid || !*sel) return 0;
    p = property(root, drag_window, XA_WINDOW, 32, &n);
    if (!p) return 0;
    Window table = n == 1 ? *(unsigned long *)p : None; XFree(p);
    if (!table) return 0;
    p = property(table, drag_targets, drag_targets, 8, &n);
    if (!p) return 0;
    valid = 0;
    if (n >= 8 && (p[0] == 'B' || p[0] == 'l') && p[1] == 0) {
        int little = p[0] == 'l'; size_t at = 8;
        unsigned lists = wire(p + 2, 2, little);
        for (unsigned i = 0; i < lists && at + 2 <= n; i++) {
            unsigned count = wire(p + at, 2, little); at += 2;
            if (count > (n - at) / 4) break;
            if (i == index) {
                for (unsigned j = 0; j < count; j++)
                    if (wire(p + at + j * 4, 4, little) == sgi_icon) valid = 1;
                break;
            }
            at += count * 4;
        }
    }
    XFree(p); return valid;
}
static void send_position(void)
{
    if (drag.waiting_status || drag.mode != 2 || drag.drop_sent) return;
    drag.sent_x = drag.x; drag.sent_y = drag.y; drag.sent_time = drag.time;
    xdnd(position, 0, ((unsigned)drag.x & 65535) << 16 | ((unsigned)drag.y & 65535), drag.time, copy);
    drag.waiting_status = 1; drag.deadline = now_ms() + 5000;
}
static void maybe_drop(void)
{
    if (!drag.drop_pending || drag.waiting_status || drag.drop_sent) return;
    if (!drag.accepted || !drag.copy_allowed) { complete(0); return; }
    if (!drag.uris) return;
    motif_reply(5, 0x32, drag.drop_time);
    xdnd(drop, 0, drag.drop_time, 0, 0); drag.drop_sent = 1;
    drag.deadline = now_ms() + 30000;
}
static void convert_reply(XSelectionRequestEvent *request)
{
    int valid = 0;
    Atom prop = request->property ? request->property : request->target;
    if (drag.mode == 2 && request->selection == selection) {
        if (request->target == targets) {
            Atom types[] = {targets, timestamp_atom, uri};
            XChangeProperty(display, request->requestor, prop, XA_ATOM, 32,
                PropModeReplace, (unsigned char *)types, 3); valid = 1;
        } else if (request->target == timestamp_atom) {
            unsigned long time = drag.first_time;
            XChangeProperty(display, request->requestor, prop, XA_INTEGER, 32,
                PropModeReplace, (unsigned char *)&time, 1); valid = 1;
        } else if (request->target == uri) {
            if (!drag.uris && drag.pending_count < 8) {
                drag.pending[drag.pending_count++] = *request; return;
            }
            if (drag.uris && drag.length < (size_t)XMaxRequestSize(display) * 4 - 64) {
                XChangeProperty(display, request->requestor, prop, uri, 8,
                    PropModeReplace, (unsigned char *)drag.uris, drag.length);
                valid = drag.served = 1;
            }
        }
    }
    selection_reply(request, valid);
}
static struct receiver *find_receiver(Window window)
{
    for (struct receiver *r = receivers; r; r = r->next)
        if (r->window == window || r->proxy == window) return r;
    return NULL;
}
static void receiver_info(unsigned char *p, Window proxy)
{
    memset(p, 0, 16); p[0] = 'B'; p[2] = 5; put(p + 4, proxy, 4); put(p + 12, 16, 4);
}
static void watch(Window window)
{
    if (window == owner || find_receiver(window)) return;
    unsigned long n; unsigned char *p = property(window, aware, XA_ATOM, 32, &n);
    if (!p) return;
    unsigned long version = n ? *(unsigned long *)p : 0; XFree(p);
    if (version < 3) return;
    struct receiver *r = calloc(1, sizeof(*r)); if (!r) return;
    p = property(window, receiver, receiver, 8, &n);
    if (p) {
        /* Leave preregistered Motif drop sites and other proxies alone. */
        if (n != 16 || (p[0] != 'B' && p[0] != 'l') || p[1] || p[2] != 5 ||
            wire(p + 4, 4, p[0] == 'l') || wire(p + 8, 2, p[0] == 'l')) {
            XFree(p); free(r); return;
        }
        memcpy(r->original, p, 16); r->had_motif = 1; XFree(p);
    } else {
        Atom actual; int format; unsigned long count, after; unsigned char *other = NULL;
        XGetWindowProperty(display, window, receiver, 0, 0, False, AnyPropertyType,
            &actual, &format, &count, &after, &other);
        if (other) XFree(other);
        if (actual != None) { free(r); return; }
    }
    r->window = window; r->version = version > 5 ? 5 : version;
    r->proxy = XCreateSimpleWindow(display, root, -1, -1, 1, 1, 0, 0, 0);
    unsigned char info[16]; receiver_info(info, r->proxy);
    r->next = receivers; receivers = r;
    XChangeProperty(display, window, receiver, receiver, 8, PropModeReplace, info, 16);
    XSelectInput(display, window, PropertyChangeMask | StructureNotifyMask);
}
static void scan(Window window, unsigned depth)
{
    if (depth > 8 || window == owner || find_receiver(window)) return;
    XSelectInput(display, window, PropertyChangeMask | StructureNotifyMask);
    watch(window);
    Window parent, tree_root, *children = NULL; unsigned count = 0;
    if (XQueryTree(display, window, &tree_root, &parent, &children, &count)) {
        for (unsigned i = 0; i < count; i++) scan(children[i], depth + 1);
        if (children) XFree(children);
    }
}
static void motif_event(XClientMessageEvent *event)
{
    unsigned char *p = (unsigned char *)event->data.b;
    if (event->format != 8 || (p[0] & 128) || (p[1] != 'B' && p[1] != 'l')) return;
    struct receiver *r = find_receiver(event->window); if (!r) return;
    unsigned op = p[0]; int little = p[1] == 'l'; Time time = wire(p + 4, 4, little);
    if (op == 0 || (op == 5 && !drag.mode)) {
        complete(0); drag.source = wire(p + (op == 0 ? 8 : 16), 4, little); drag.dest = r->window;
        drag.version = r->version; drag.first_time = drag.time = time;
        drag.mode = source_has_icons(drag.source, wire(p + 12, 4, little), &drag.selection) ? 2 : 1;
        if (drag.mode == 2) {
            XSetSelectionOwner(display, selection, owner, time);
            if (XGetSelectionOwner(display, selection) != owner) { reset(); return; }
            xdnd(enter, (long)drag.version << 24, uri, 0, 0);
            XConvertSelection(display, drag.selection, sgi_icon, data_property, owner, time);
            drag.requested = 1; drag.deadline = now_ms() + 5000;
        }
    }
    if (!drag.mode || drag.dest != r->window) return;
    if (drag.mode == 1) {
        XEvent forwarded = {0}; forwarded.xclient = *event; forwarded.xclient.window = r->window;
        XSendEvent(display, r->window, False, 0, &forwarded);
        if (op == 1 || op == 5) drag.leave_due = now_ms() + 1000;
        return;
    }
    if (op == 1) { drag.leave_due = now_ms() + 250; return; }
    if (op == 2 || op == 8 || op == 5) {
        drag.leave_due = 0; drag.time = time; drag.operation = op;
        unsigned flags = wire(p + 2, 2, little);
        if (op == 5 && (flags & 0xf000)) {
            /* Motif can finish Escape/help with a cancelled DROP_START. */
            drag.drop_pending = 1; drag.drop_time = time; complete(0); return;
        }
        if (op == 5 || !drag.accepted) drag.copy_allowed = ((flags >> 8) & 2) != 0;
        if (op != 8) { drag.x = (int16_t)wire(p + 8, 2, little); drag.y = (int16_t)wire(p + 10, 2, little); }
        if (op == 5) { drag.drop_pending = 1; drag.drop_time = time; }
        send_position(); maybe_drop();
    }
}
static void stop(int signal_number) { (void)signal_number; stopping = 1; }
static int xerror(Display *d, XErrorEvent *error)
{
    if (error->error_code != BadWindow && error->error_code != BadAtom && error->error_code != BadMatch) {
        char text[160]; XGetErrorText(d, error->error_code, text, sizeof(text));
        fprintf(stderr, "X error: %s request=%u\n", text, error->request_code);
    }
    return 0;
}
static void remove_receiver(Window window, int restore)
{
    if (drag.dest == window) complete(0);
    struct receiver **link = &receivers;
    while (*link) {
        struct receiver *r = *link;
        if (r->window != window) { link = &r->next; continue; }
        if (restore) {
            unsigned long n; unsigned char expected[16]; receiver_info(expected, r->proxy);
            unsigned char *p = property(window, receiver, receiver, 8, &n);
            if (p && n == 16 && !memcmp(p, expected, 16)) {
                if (r->had_motif) XChangeProperty(display, window, receiver, receiver, 8,
                    PropModeReplace, r->original, 16);
                else XDeleteProperty(display, window, receiver);
            }
            if (p) XFree(p);
        }
        XDestroyWindow(display, r->proxy); *link = r->next; free(r); return;
    }
}
int main(void)
{
    if (gethostname(hostname, sizeof(hostname)) || !memchr(hostname, 0, sizeof(hostname))) return 1;
    display = XOpenDisplay(NULL); if (!display) { fputs("Cannot open session display.\n", stderr); return 1; }
    XSetErrorHandler(xerror); root = DefaultRootWindow(display);
    owner = XCreateSimpleWindow(display, root, -1, -1, 1, 1, 0, 0, 0);
#define ATOM(variable, name) variable = XInternAtom(display, name, False)
    ATOM(motif,"_MOTIF_DRAG_AND_DROP_MESSAGE"); ATOM(receiver,"_MOTIF_DRAG_RECEIVER_INFO");
    ATOM(initiator,"_MOTIF_DRAG_INITIATOR_INFO"); ATOM(drag_window,"_MOTIF_DRAG_WINDOW");
    ATOM(drag_targets,"_MOTIF_DRAG_TARGETS"); ATOM(sgi_icon,"_SGI_ICON");
    ATOM(aware,"XdndAware"); ATOM(enter,"XdndEnter"); ATOM(position,"XdndPosition");
    ATOM(status,"XdndStatus"); ATOM(leave,"XdndLeave"); ATOM(drop,"XdndDrop");
    ATOM(finished,"XdndFinished"); ATOM(selection,"XdndSelection"); ATOM(copy,"XdndActionCopy");
    ATOM(uri,"text/uri-list"); ATOM(targets,"TARGETS"); ATOM(timestamp_atom,"TIMESTAMP");
    ATOM(data_property,"_XIRI_DROP_DATA"); ATOM(ack_property,"_XIRI_DROP_ACK");
    ATOM(singleton,"_XIRI_DROP_BRIDGE"); ATOM(success,"XmTRANSFER_SUCCESS"); ATOM(failure,"XmTRANSFER_FAILURE");
#undef ATOM
    XGrabServer(display);
    int existing = XGetSelectionOwner(display, singleton) != None;
    if (!existing) XSetSelectionOwner(display, singleton, owner, CurrentTime);
    XUngrabServer(display);
    if (existing) { XCloseDisplay(display); fputs("A drop bridge already owns this display.\n", stderr); return 1; }
    scan(root, 0); XSelectInput(display, root, SubstructureNotifyMask);
    signal(SIGTERM, stop); signal(SIGINT, stop); signal(SIGHUP, stop);
    fputs("Ready: local SGI file icons to XDND URI lists.\n", stderr);
    while (!stopping) {
        XFlush(display);
        if (!XPending(display)) {
            fd_set fds; FD_ZERO(&fds); FD_SET(ConnectionNumber(display), &fds);
            struct timeval timeout = {0, 100000};
            if (select(ConnectionNumber(display) + 1, &fds, NULL, NULL, &timeout) < 0 && errno != EINTR) break;
        }
        while (!stopping && XPending(display)) {
            XEvent event; XNextEvent(display, &event);
            if (event.type == ClientMessage) {
                if (event.xclient.message_type == motif) motif_event(&event.xclient);
                else if (drag.mode == 2 && event.xclient.format == 32 &&
                    event.xclient.window == owner && (Window)event.xclient.data.l[0] == drag.dest) {
                    if (event.xclient.message_type == status && drag.waiting_status) {
                        int old = drag.accepted;
                        drag.accepted = (event.xclient.data.l[1] & 1) && (Atom)event.xclient.data.l[4] == copy;
                        int op = drag.operation == 8 ? 8 : old == drag.accepted ? 2 : drag.accepted ? 3 : 4;
                        motif_reply(op, drag.accepted && drag.copy_allowed ? 0x32 : 0x10, drag.sent_time);
                        drag.waiting_status = 0;
                        if (drag.x != drag.sent_x || drag.y != drag.sent_y || drag.time != drag.sent_time) send_position();
                        else drag.deadline = drag.uris ? 0 : now_ms() + 5000;
                        maybe_drop();
                    } else if (event.xclient.message_type == finished && drag.drop_sent) {
                        complete(drag.served && (drag.version < 5 ||
                            ((event.xclient.data.l[1] & 1) && (Atom)event.xclient.data.l[2] == copy)));
                    }
                }
            } else if (event.type == SelectionRequest) convert_reply(&event.xselectionrequest);
            else if (event.type == SelectionNotify && event.xselection.target == sgi_icon &&
                event.xselection.selection == drag.selection && event.xselection.time == drag.first_time &&
                drag.mode == 2 && drag.requested) {
                unsigned long n; unsigned char *p = event.xselection.property == data_property ?
                    property(owner, data_property, sgi_icon, 8, &n) : NULL;
                drag.requested = 0;
                if (p) { drag.uris = drop_uris(p, n, hostname, &drag.length, &drag.files); XFree(p); }
                XDeleteProperty(display, owner, data_property);
                if (!drag.uris) { complete(0); continue; }
                unsigned count = drag.pending_count; drag.pending_count = 0;
                for (unsigned i = 0; i < count; i++) convert_reply(&drag.pending[i]);
                if (!drag.waiting_status) drag.deadline = 0;
                maybe_drop();
            } else if (event.type == SelectionClear) {
                if (event.xselectionclear.selection == singleton) stopping = 1;
                else if (event.xselectionclear.selection == selection &&
                    XGetSelectionOwner(display, selection) != owner) complete(0);
            } else if (event.type == CreateNotify && event.xcreatewindow.parent == root) {
                Window w = event.xcreatewindow.window;
                if (w != owner && !find_receiver(w)) {
                    XSelectInput(display, w, PropertyChangeMask | StructureNotifyMask); watch(w);
                }
            } else if (event.type == MapNotify || event.type == PropertyNotify) {
                Window w = event.type == MapNotify ? event.xmap.window : event.xproperty.window;
                if (event.type == PropertyNotify && event.xproperty.atom == aware &&
                    event.xproperty.state == PropertyDelete) remove_receiver(w, 1);
                else if (event.type == PropertyNotify && event.xproperty.atom == receiver) {
                    struct receiver *r = find_receiver(w);
                    if (r) {
                        unsigned long n; unsigned char expected[16]; receiver_info(expected, r->proxy);
                        unsigned char *p = property(w, receiver, receiver, 8, &n);
                        int changed = !p || n != 16 || memcmp(p, expected, 16);
                        if (p) XFree(p);
                        if (changed) { remove_receiver(w, 0); watch(w); }
                    } else watch(w);
                } else if (event.type == MapNotify || event.xproperty.atom == aware) watch(w);
            } else if (event.type == DestroyNotify) {
                Window w = event.xdestroywindow.window;
                if (drag.source == w || drag.dest == w) complete(0);
                remove_receiver(w, 0);
            }
        }
        long long now = now_ms();
        if ((drag.leave_due && now >= drag.leave_due) || (drag.deadline && now >= drag.deadline)) complete(0);
    }
    complete(0);
    while (receivers) remove_receiver(receivers->window, 1);
    XSync(display, False); XCloseDisplay(display); return 0;
}
