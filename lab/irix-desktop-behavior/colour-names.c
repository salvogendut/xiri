/* Native Xlib observer: compare imported SGI names with their source RGBs.
 * Run with the desktop's DISPLAY, XAUTHORITY and XCMSDB environment. */
#include <X11/Xlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

int
main(int argc, char **argv)
{
    alarm(60);
    if (argc != 2) return 2;
    FILE *file = fopen(argv[1], "r");
    Display *d = XOpenDisplay(NULL);
    if (!file || !d) return 2;
    Colormap map = DefaultColormap(d, DefaultScreen(d));
    char line[512], name[256], numeric[32];
    unsigned r, g, b, count = 0, failures = 0;
    while (fgets(line, sizeof(line), file)) {
        if (sscanf(line, "%u %u %u %255[^\n]", &r, &g, &b, name) != 4 ||
            strncasecmp(name, "sgi", 3)) continue;
        if (r > 255 || g > 255 || b > 255) return 2;
        /* The source database, not our generated Xcms file, is the oracle. */
        r *= 257; g *= 257; b *= 257;
        XColor exact = {0}, screen = {0}, parsed = {0}, reference = {0};
        int lookup = XLookupColor(d, map, name, &exact, &screen);
        int parse = XParseColor(d, map, name, &parsed);
        int ok = lookup && parse && exact.red == r && exact.green == g &&
            exact.blue == b && parsed.red == r && parsed.green == g && parsed.blue == b;
        snprintf(numeric, sizeof(numeric), "rgb:%04x/%04x/%04x", r, g, b);
        if (!XParseColor(d, map, numeric, &reference) ||
            !XAllocColor(d, map, &reference) ||
            !XAllocNamedColor(d, map, name, &screen, &exact)) ok = 0;
        if (screen.pixel != reference.pixel) ok = 0;
        printf("%s name=%s rgb=%04x/%04x/%04x pixel=%lx numeric=%lx\n",
            ok ? "PASS" : "FAIL", name, r, g, b, screen.pixel, reference.pixel);
        failures += !ok;
        count++;
    }
    XColor exact = {0}, screen = {0};
    if (XLookupColor(d, map, "XiriInvalidColourName", &exact, &screen) ||
        !XLookupColor(d, map, "white", &exact, &screen) ||
        exact.red != 65535 || exact.green != 65535 || exact.blue != 65535)
        failures++;
    printf("COLOUR_NAMES entries=%u failures=%u\n", count, failures);
    fclose(file);
    XCloseDisplay(d);
    return !count || failures ? 1 : 0;
}
