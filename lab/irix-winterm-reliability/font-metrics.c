/* Compare native and vendor Xlib's core-font/font-set metrics. */
#include <X11/Xlib.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>

static void rectangle(const char *name, const XRectangle *r)
{
    printf(" %s=%d,%d,%u,%u", name, r->x, r->y, r->width, r->height);
}

int main(int argc, char **argv)
{
    Display *display;
    int repeat;
    const char *pattern = argc > 1 ? argv[1] :
        "-*-courier-bold-r-normal--20-*-*-*-m-110-iso8859-1";
    if (!setlocale(LC_ALL, "")) return 2;
    display = XOpenDisplay(NULL);
    if (!display) return 3;
    for (repeat = 0; repeat < 6; repeat++) {
        char **missing = NULL, *default_string = NULL;
        char **names;
        XFontStruct **fonts;
        XFontSetExtents *extents;
        int missing_count = 0, count, i;
        XFontSet set = XCreateFontSet(display, pattern, &missing,
            &missing_count, &default_string);
        if (!set) { printf("NO_FONT_SET missing=%d\n", missing_count); return 4; }
        extents = XExtentsOfFontSet(set);
        count = XFontsOfFontSet(set, &fonts, &names);
        printf("SET repeat=%d count=%d missing=%d width=%d", repeat, count,
            missing_count, XmbTextEscapement(set, "MMMM", 4));
        rectangle("ink", &extents->max_ink_extent);
        rectangle("logical", &extents->max_logical_extent);
        putchar('\n');
        for (i = 0; i < count; i++)
            printf("FONT %s ascent=%d descent=%d width=%d,%d glyph=%d,%d\n",
                names[i], fonts[i]->ascent, fonts[i]->descent,
                fonts[i]->min_bounds.width, fonts[i]->max_bounds.width,
                fonts[i]->max_bounds.ascent, fonts[i]->max_bounds.descent);
        if (missing) XFreeStringList(missing);
        XFreeFontSet(display, set);
    }
    XCloseDisplay(display);
    return 0;
}
