#define main metrics_main
#include "core-metrics.c"
#undef main

int main(int argc, char **argv)
{
    const int sizes[] = {8, 12, 14, 16, 20, 24, 32};
    const char *styles[] = {"bold-r", "medium-r", "bold-i", "medium-i"};
    XFontStruct *held[41] = {0};
    XFontSet sets[9] = {0};
    Display *d = XOpenDisplay(NULL);
    int iterations = argc > 1 ? atoi(argv[1]) : 300;
    if (!d) return 2;
    setlocale(LC_ALL, "C");
    alarm(600);
    for (int n = 0; n < iterations; n++) {
        char pattern[160];
        int size = sizes[(n / 4) % 7];
        snprintf(pattern, sizeof(pattern), "-ibm-courier-%s-normal--%d-*-100-100-m-*-iso8859-1", styles[n % 4], size);
        if (n % 3 == 0) {
            int count = 0;
            XFontStruct *fi = NULL;
            char **names = XListFontsWithInfo(d, pattern, 16, &count, &fi);
            for (int j = 0; j < count; j++) if (fi[j].ascent + fi[j].descent < size / 2) {
                printf("FAIL iteration=%d query=%s\n", n, pattern);
                info(d, "LIST_BAD", fi+j); return 7;
            }
            if (names) XFreeFontInfo(names, fi, count);
        }
        int slot = n % 41;
        if (held[slot]) XFreeFont(d, held[slot]);
        held[slot] = XLoadQueryFont(d, pattern);
        if (!held[slot]) { printf("MISSING %s\n", pattern); return 3; }
        if (held[slot]->ascent + held[slot]->descent < size / 2) {
            printf("FAIL iteration=%d open=%s\n", n, pattern);
            info(d, "OPEN_BAD", held[slot]); render(d, held[slot]); return 7;
        }
        if (n % 5 == 0) {
            char **missing = NULL, *def = NULL; int count = 0;
            int si = (n / 5) % 9;
            if (sets[si]) XFreeFontSet(d, sets[si]);
            sets[si] = XCreateFontSet(d, pattern, &missing, &count, &def);
            if (missing) XFreeStringList(missing);
            if (!sets[si]) return 4;
            XFontSetExtents *ex = XExtentsOfFontSet(sets[si]);
            if (ex->max_logical_extent.height < size / 2) {
                printf("FAIL iteration=%d set=%s height=%u\n", n, pattern, ex->max_logical_extent.height); return 7;
            }
        }
        if (n % 28 == 16) {
            printf("COURIER20 iteration=%d\n", n);
            info(d, "OPEN_FONT", held[slot]); render(d, held[slot]); fflush(stdout);
        }
        if (argc > 2 && n % 28 == 27) {
            for(int j=0;j<41;j++) if(held[j]) { XFreeFont(d,held[j]);held[j]=NULL; }
            for(int j=0;j<9;j++) if(sets[j]) { XFreeFontSet(d,sets[j]);sets[j]=NULL; }
        }
    }
    for (int n=0;n<41;n++) if (held[n]) XFreeFont(d,held[n]);
    for (int n=0;n<9;n++) if (sets[n]) XFreeFontSet(d,sets[n]);
    XCloseDisplay(d);
    printf("STRESS_PASS iterations=%d\n", iterations);
    return 0;
}
