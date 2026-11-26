/* Read the original n32 HDSP parameter descriptors and audio device list. */
typedef unsigned int u32;
enum { IRIX_WRITE = 1004, IRIX_OPEN = 1005, IRIX_IOCTL = 1054, IRIX_POLL = 1087 };
enum { SET_PARAMS = 24, GET_PARAMS, QUERY_VALUES, GET_PARAM_INFO };
enum { RESOURCE = 0x10000001, INTERFACE = 0x10000002, GAIN = 0x10000019, MUTE = 0x1000001d };
enum { DEFAULT_OUTPUT = 10, SYSTEM = 11, ANALOG_OUTPUT = 6 };

struct parameter {
    u32 id, pad;
    u32 value[2];
    short size, size2, used, used2;
};

extern int trap3(int number, unsigned long arg0, unsigned long arg1, unsigned long arg2);

void *
memset(void *address, int value, unsigned long length)
{
    unsigned char *p = address;
    while (length--)
        *p++ = value;
    return address;
}

static void
put(const char *s)
{
    unsigned n = 0;
    while (s[n])
        n++;
    trap3(IRIX_WRITE, 1, (unsigned long)s, n);
}

static void
word(u32 n)
{
    char text[10];
    int i;
    for (i = 0; i < 8; i++)
        text[i] = "0123456789abcdef"[(n >> (28 - 4*i)) & 15];
    text[8] = ' ';
    text[9] = 0;
    put(text);
}

static int
info(int fd, u32 resource, u32 param)
{
    /* Includes room for the n32 eight-byte value union and reserved words. */
    u32 data[42] __attribute__((aligned(8))) = {resource, param};
    int rc = trap3(IRIX_IOCTL, fd, GET_PARAM_INFO, (unsigned long)data);
    int i;
    put("INFO "); word(resource); word(param); word(rc);
    if (rc >= 0)
        for (i = 2; i < 26; i++)
            word(data[i]);
    put("\n");
    return rc;
}

static void
value(int fd, u32 id, u32 param, int vector)
{
    u32 buffer[32] __attribute__((aligned(8))) = {0};
    struct parameter batch[3] __attribute__((aligned(8))) = {
        { .id = 3 }, { .id = RESOURCE, .value = {id} }, { .id = param }
    };
    struct parameter *pv = &batch[2];
    int i, rc;
    if (vector) {
        pv->value[0] = (u32)buffer;
        pv->size = param == GAIN ? 2 : 64;
    }
    rc = trap3(IRIX_IOCTL, fd, GET_PARAMS, (unsigned long)batch);
    put("VALUE "); word(id); word(param); word(rc);
    if (rc >= 0) {
        word(((u32)(unsigned short)pv->used << 16) | (unsigned short)pv->used2);
        if (vector) {
            for (i = 0; i < 8; i++)
                word(buffer[i]);
        } else {
            word(pv->value[0]); word(pv->value[1]);
        }
    }
    put("\n");
}

static void
device(int fd, u32 id)
{
    static const int params[] = {1, 2, 4, 13, 18, 19, 20, 22, 23, 25, 27, 29, 30, 31, 36};
    unsigned i;
    for (i = 0; i < sizeof(params)/sizeof(params[0]); i++)
        info(fd, id, 0x10000000u + params[i]);
    value(fd, id, 0x10000002, 0);  /* current interface */
    value(fd, id, 0x1000001b, 0);  /* gain reference */
    value(fd, id, 0x1000001f, 1);  /* label */
    value(fd, id, 0x10000024, 1);  /* short name */
    value(fd, id, 0x10000012, 0);  /* type */
    value(fd, id, 0x10000004, 0);  /* channels */
    value(fd, id, 0x10000013, 1);  /* name */
    value(fd, id, 0x1000001e, 0);  /* containing subsystem */
    value(fd, id, 0x10000019, 1);  /* gain */
    value(fd, id, 0x1000001d, 0);  /* mute */
}

/* The factory panel builds its clock menu from these resource IDs. */
static void
clock_sources(int fd)
{
    const u32 clock = 0x10000011, rate = 0x1000000d;
    u32 ids[24][2] __attribute__((aligned(8))) = {{0}};
    u32 q[14] __attribute__((aligned(8))) = {(u32)ids, 0, 7, ANALOG_OUTPUT, clock, 24};
    int count = trap3(IRIX_IOCTL, fd, QUERY_VALUES, (unsigned long)q);
    put("CLOCKS "); word(count);
    for (int i = 0; i < count && i < 24; i++)
        word(ids[i][0]);
    put("\n");
    info(fd, ANALOG_OUTPUT, clock);
    value(fd, ANALOG_OUTPUT, clock, 0);
    value(fd, ANALOG_OUTPUT, rate, 0);
    for (int i = 0; i < count && i < 24; i++) {
        value(fd, ids[i][0], 0x10000012, 0);
        value(fd, ids[i][0], 0x10000013, 1);
        value(fd, ids[i][0], 0x1000001f, 1);
        value(fd, ids[i][0], 0x10000024, 1);
    }
}

static void
lookup(int fd, u32 scope, const char *name)
{
    struct { char name[80]; u32 path[8]; int depth; } request = {{0}, {scope}, 0};
    unsigned i;
    int rc;
    for (i = 0; name[i] && i + 1 < sizeof(request.name); i++)
        request.name[i] = name[i];
    rc = trap3(IRIX_IOCTL, fd, 28, (unsigned long)&request);
    put("LOOKUP "); put(name); put(" "); word(scope); word(rc);
    if (rc >= 0 && request.depth >= 0 && request.depth <= 8) {
        word(request.depth);
        for (int n = 0; n < request.depth; n++)
            word(request.path[n]);
    }
    put("\n");
}

static int
set_gain(int fd, int silent)
{
    /* A2's stereo dB equivalents of native mixer levels 64 and 128. */
    u32 levels[4] __attribute__((aligned(8))) = {0x24, 0x1fa4372c, 0x2a, 0x24ea405d};
    struct parameter batch[3] __attribute__((aligned(8))) = {
        { .id = 3 }, { .id = RESOURCE, .value = {DEFAULT_OUTPUT} },
        { .id = GAIN, .value = {(u32)levels}, .size = 2 }
    };
    if (silent) {
        levels[0] = levels[2] = 0x80000000u; /* AL negative infinity */
        levels[1] = levels[3] = 0;
    }
    return trap3(IRIX_IOCTL, fd, SET_PARAMS, (unsigned long)batch) == 1 ? 0 : 1;
}

/* Inspect the original driver's enumerated mute states on a disposable donor. */
static int
mute_test(int fd)
{
    u32 vals[16][2] __attribute__((aligned(8))) = {{0}};
    u32 q[14] __attribute__((aligned(8))) = {(u32)vals, 0, 7, ANALOG_OUTPUT, MUTE, 16};
    struct parameter b[3] __attribute__((aligned(8))) = {
        { .id = 3 }, { .id = RESOURCE, .value = {ANALOG_OUTPUT} }, { .id = MUTE }
    };
    int count = trap3(IRIX_IOCTL, fd, QUERY_VALUES, (unsigned long)q);
    put("MUTE_STATES "); word(count);
    for (int i = 0; i < count && i < 16; i++) {
        word(vals[i][0]); word(vals[i][1]);
    }
    put("\n");
    if (count < 1 || count > 16)
        return 1;
    int events = trap3(IRIX_OPEN, (unsigned long)"/dev/hdsp/hdsp0events", 2, 0);
    u32 sub[4] = {ANALOG_OUTPUT, 0, 0, 1u << 29};
    if (events < 0 || trap3(IRIX_IOCTL, events, 110, 0) < 0 ||
        trap3(IRIX_IOCTL, events, 112, (unsigned long)sub) < 0)
        return 1;
    for (int i = 0; i <= 1; i++) {
        b[2].value[0] = i;
        put("MUTE_WRITE "); word(i);
        word(trap3(IRIX_IOCTL, fd, SET_PARAMS, (unsigned long)b)); put("\n");
        value(fd, ANALOG_OUTPUT, MUTE, 0);
        value(fd, ANALOG_OUTPUT, GAIN, 1);
        int pending = 0;
        if (trap3(IRIX_IOCTL, events, 118, (unsigned long)&pending) >= 0 && pending > 0) {
            u32 event[16] __attribute__((aligned(8))) = {0};
            if (trap3(IRIX_IOCTL, events, 101, (unsigned long)event) < 0)
                return 1;
            put("MUTE_EVENT ");
            for (int n = 0; n < 16; n++) word(event[n]);
            put("\n");
        }
    }
    if (set_gain(fd, 0))
        return 1;
    put("AFTER_GAIN "); value(fd, ANALOG_OUTPUT, MUTE, 0);
    b[2].value[0] = 0;
    return trap3(IRIX_IOCTL, fd, SET_PARAMS, (unsigned long)b) != 1;
}

static int
event_test(int master)
{
    struct { u32 id, pad, maskhi, masklo; } selection = {ANALOG_OUTPUT, 0, 0, 1u << 25};
    u32 event[32] __attribute__((aligned(8))) = {0};
    struct { int fd; short events, revents; } pollfds[2] = {{-1, 1, 0}, {-1, 1, 0}};
    int fd, i, count = -1, rc;

    fd = trap3(IRIX_OPEN, (unsigned long)"/dev/hdsp/hdsp0events", 2, 0);
    put("EVENT_OPEN "); word(fd); put("\n");
    if (fd < 0)
        return 1;
    rc = trap3(IRIX_IOCTL, fd, 110, 0);
    put("EVENT_INIT "); word(rc); put("\n");
    if (rc < 0)
        return 1;
    pollfds[0].fd = fd;
    pollfds[1].fd = trap3(IRIX_OPEN, (unsigned long)"/dev/hdsp/hdsp0events", 2, 0);
    if (pollfds[1].fd < 0 || trap3(IRIX_IOCTL, pollfds[1].fd, 110, 0) < 0 ||
        trap3(IRIX_POLL, (unsigned long)pollfds, 2, 0) != 0)
        return 1;
    rc = trap3(IRIX_IOCTL, fd, 112, (unsigned long)&selection);
    put("EVENT_SELECT "); word(rc); put("\n");
    if (rc < 0 || set_gain(master, 0))
        return 1;
    rc = trap3(IRIX_POLL, (unsigned long)pollfds, 2, 1000);
    put("EVENT_POLL "); word(rc); word(pollfds[0].revents); word(pollfds[1].revents); put("\n");
    if (rc != 1 || pollfds[0].revents != 1 || pollfds[1].revents != 0)
        return 1;
    rc = trap3(IRIX_IOCTL, fd, 118, (unsigned long)&count);
    put("EVENT_PENDING "); word(rc); word(count); put("\n");
    if (rc < 0 || count < 1)
        return 1;
    rc = trap3(IRIX_IOCTL, fd, 101, (unsigned long)event);
    put("EVENT_GAIN "); word(rc);
    for (i = 0; i < 16; i++)
        word(event[i]);
    put("\n");
    if (rc < 0 || event[0] == 0 || event[1] != ANALOG_OUTPUT ||
        event[2] != GAIN || event[3] != 25 || event[9] != 2)
        return 1;
    if (trap3(IRIX_IOCTL, fd, 118, (unsigned long)&count) < 0 || count != 0)
        return 1;
    return trap3(IRIX_POLL, (unsigned long)pollfds, 2, 0) != 0;
}

static int
equal(const char *a, const char *b)
{
    while (*a && *a == *b) {
        a++;
        b++;
    }
    return *a == *b;
}

int
run(int argc, char **argv)
{
    const u32 devices = 0x1000000c;
    u32 ids[24][2] __attribute__((aligned(8))) = {{0}};
    u32 query[14] __attribute__((aligned(8))) = {(u32)ids, 0, 7, SYSTEM, devices, 24};
    int fd, count, i;

    fd = trap3(IRIX_OPEN, (unsigned long)"/dev/hdsp/hdsp0master", 2, 0);
    put("OPEN "); word(fd); put("\n");
    if (fd < 0)
        return 1;
    if (argc == 2 && equal(argv[1], "--set-test-gain"))
        return set_gain(fd, 0);
    if (argc == 2 && equal(argv[1], "--silence-test-gain"))
        return set_gain(fd, 1);
    if (argc == 2 && equal(argv[1], "--mute-test"))
        return mute_test(fd);
    if (argc == 2 && equal(argv[1], "--event-test"))
        return event_test(fd);
    if (argc != 1)
        return 2;
    clock_sources(fd);
    info(fd, SYSTEM, devices);
    count = trap3(IRIX_IOCTL, fd, QUERY_VALUES, (unsigned long)query);
    put("DEVICES "); word(count);
    for (i = 0; i < count && i < 24; i++)
        word(ids[i][0]);
    put("\n");
    if (count <= 0)
        return 1;
    device(fd, DEFAULT_OUTPUT);
    for (i = 0; i < count && i < 24; i++)
        device(fd, ids[i][0]);
    info(fd, SYSTEM, 9);
    info(fd, SYSTEM, 10);
    info(fd, SYSTEM, 0x10000008);
    info(fd, SYSTEM, 0x1000002b);
    value(fd, SYSTEM, 9, 0);
    value(fd, SYSTEM, 10, 0);
    value(fd, SYSTEM, 0x10000008, 0);
    value(fd, SYSTEM, 0x1000002b, 0);
    value(fd, 25, 0x10000012, 0);
    value(fd, 25, 0x10000013, 1);
    value(fd, 25, 0x1000001f, 1);
    lookup(fd, SYSTEM, "DefaultOut");
    lookup(fd, SYSTEM, "DefaultIn");
    lookup(fd, SYSTEM, "Default Output");
    lookup(fd, SYSTEM, "Analog Out");
    lookup(fd, SYSTEM, "AnalogOut");
    lookup(fd, SYSTEM, "A2");
    lookup(fd, SYSTEM, "A2.AnalogOut");
    lookup(fd, SYSTEM, "Speaker");
    lookup(fd, ANALOG_OUTPUT, "Speaker");
    lookup(fd, SYSTEM, "A3.AnalogOut");
    lookup(fd, SYSTEM, "missing");
    query[4] = DEFAULT_OUTPUT;
    count = trap3(IRIX_IOCTL, fd, QUERY_VALUES, (unsigned long)query);
    put("OUTPUTS "); word(count);
    for (i = 0; i < count && i < 24; i++)
        word(ids[i][0]);
    put("\n");
    query[3] = ANALOG_OUTPUT;
    query[4] = INTERFACE;
    count = trap3(IRIX_IOCTL, fd, QUERY_VALUES, (unsigned long)query);
    put("INTERFACES "); word(count);
    for (i = 0; i < count && i < 24; i++)
        word(ids[i][0]);
    put("\n");
    for (i = 0; i < count && i < 24; i++)
        device(fd, ids[i][0]);
    return 0;
}
