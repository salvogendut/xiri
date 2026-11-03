/* Native XRender regression for Newport XAA clipped/repeated textures.
 * Only opaque ARGB and binary A8 masks are used: coordinate correctness is
 * independent of the driver's separate partial-alpha/Render-op limitations. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xrender.h>
#include <stdio.h>
#include <stdlib.h>

static unsigned long packed(Visual *v, int r, int g, int b)
{
    return r * (v->red_mask & -v->red_mask) |
        g * (v->green_mask & -v->green_mask) |
        b * (v->blue_mask & -v->blue_mask);
}
static int wrap(int n, int size) { n %= size; return n < 0 ? n + size : n; }
static int red(int x,int y) { return (17*x+3*y)&255; }
static int green(int x,int y) { return (5*x+11*y)&255; }
static int blue(int x,int y) { return (7*x+13*y)&255; }
static int mask(int x,int y) { return ((3*x+7*y)%5)<2; }

int main(void)
{
    enum { W=29, H=23, DX=32, DY=32 };
    const struct { int sx,sy,w,h,repeat; } cases[] = {
        {0,0,W,H,0}, {0,0,11,9,0}, {3,5,11,9,0}, {3,5,W-3,H-5,0},
        {7,9,37,31,1}, {-5,-7,38,32,1}
    };
    Display *d=XOpenDisplay(NULL); if (!d) return 2;
    int sn=DefaultScreen(d);Visual *v=DefaultVisual(d,sn);
    Window root=RootWindow(d,sn);
    XSetWindowAttributes wa;wa.override_redirect=True;wa.background_pixel=0;
    Window win=XCreateWindow(d,root,20,20,120,100,0,CopyFromParent,InputOutput,
        CopyFromParent,CWOverrideRedirect|CWBackPixel,&wa);
    XStoreName(d,win,"Xiri Newport XRender regression");XMapWindow(d,win);XSync(d,False);
    GC gc=XCreateGC(d,win,0,NULL);
    Pixmap rgba=XCreatePixmap(d,root,W,H,32), a8=XCreatePixmap(d,root,W,H,8);
    Pixmap solid=XCreatePixmap(d,root,1,1,32);
    GC rgc=XCreateGC(d,rgba,0,NULL), agc=XCreateGC(d,a8,0,NULL);
    XImage *im=XCreateImage(d,v,32,ZPixmap,0,NULL,W,H,32,0);
    XImage *am=XCreateImage(d,v,8,ZPixmap,0,NULL,W,H,8,0);
    if (!im || !am) return 2;
    im->data=calloc(im->bytes_per_line,H);am->data=calloc(am->bytes_per_line,H);
    if (!im->data || !am->data) return 2;
    for (int y=0;y<H;y++) for (int x=0;x<W;x++) {
        XPutPixel(im,x,y,0xff000000UL|(red(x,y)<<16)|(green(x,y)<<8)|blue(x,y));
        XPutPixel(am,x,y,mask(x,y)?255:0);
    }
    XPutImage(d,rgba,rgc,im,0,0,0,0,W,H);XPutImage(d,a8,agc,am,0,0,0,0,W,H);
    XSetForeground(d,rgc,0xffd34f89UL);XFillRectangle(d,solid,rgc,0,0,1,1);
    XRenderPictureAttributes pa;pa.repeat=True;
    Picture sp=XRenderCreatePicture(d,solid,XRenderFindStandardFormat(d,PictStandardARGB32),CPRepeat,&pa);
    Picture rp=XRenderCreatePicture(d,rgba,XRenderFindStandardFormat(d,PictStandardARGB32),0,NULL);
    Picture mp=XRenderCreatePicture(d,a8,XRenderFindStandardFormat(d,PictStandardA8),0,NULL);
    Picture dp=XRenderCreatePicture(d,win,XRenderFindVisualFormat(d,v),0,NULL);
    unsigned total=0,bad=0;
    for (int kind=0;kind<2;kind++) for (unsigned c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        int sx=cases[c].sx,sy=cases[c].sy,cw=cases[c].w,ch=cases[c].h;
        pa.repeat=cases[c].repeat;XRenderChangePicture(d,kind?mp:rp,CPRepeat,&pa);
        XSetForeground(d,gc,0);XFillRectangle(d,win,gc,0,0,120,100);
        XRenderComposite(d,PictOpOver,kind?sp:rp,kind?mp:None,dp,
            kind?0:sx,kind?0:sy,kind?sx:0,kind?sy:0,DX,DY,cw,ch);
        XSync(d,False);
        XImage *actual=XGetImage(d,win,DX-1,DY-1,cw+2,ch+2,AllPlanes,ZPixmap);
        if (!actual) return 2;
        unsigned failed=0;
        for (int y=-1;y<=ch;y++) for (int x=-1;x<=cw;x++) {
            unsigned long expected=0,got=XGetPixel(actual,x+1,y+1);
            if (x>=0 && x<cw && y>=0 && y<ch) {
                int px=wrap(sx+x,W),py=wrap(sy+y,H);
                expected=kind?(mask(px,py)?packed(v,211,79,137):0):packed(v,red(px,py),green(px,py),blue(px,py));
            }
            total++;
            if (got!=expected) {
                if (!failed) printf("RENDER_FAIL kind=%s case=%u xy=%d,%d source=%d,%d expected=%lx actual=%lx\n",kind?"A8":"ARGB",c,x,y,sx,sy,expected,got);
                failed++;bad++;
            }
        }
        printf("RENDER_CASE kind=%s case=%u mismatches=%u\n",kind?"A8":"ARGB",c,failed);
        XDestroyImage(actual);
    }
    printf("RENDER_%s pixels=%u mismatches=%u\n",bad?"FAILED":"PASS",total,bad);
    XDestroyImage(im);XDestroyImage(am);XFreeGC(d,gc);XFreeGC(d,rgc);XFreeGC(d,agc);
    XRenderFreePicture(d,sp);XRenderFreePicture(d,rp);XRenderFreePicture(d,mp);XRenderFreePicture(d,dp);
    XFreePixmap(d,rgba);XFreePixmap(d,a8);XFreePixmap(d,solid);XDestroyWindow(d,win);XCloseDisplay(d);
    return bad?1:0;
}
