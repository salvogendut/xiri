/* Native Xft window/pixmap comparison with explicit Render and AA controls. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xft/Xft.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    enum { W=300,H=60 };
    const FcChar8 *text=(const FcChar8 *)"Toolchest Disabled 012345";
    Display *d=XOpenDisplay(NULL);
    if (!d) return 2;
    alarm(60);
    int sn=DefaultScreen(d);
    Visual *v=DefaultVisual(d,sn);
    Colormap cmap=DefaultColormap(d,sn);
    Window root=RootWindow(d,sn);
    XSetWindowAttributes wa;
    wa.override_redirect=True;wa.background_pixel=0xc1c1c1;
    Window w=XCreateWindow(d,root,593,607,W,H,0,CopyFromParent,InputOutput,
        CopyFromParent,CWOverrideRedirect|CWBackPixel,&wa);
    XStoreName(d,w,"Xiri Xft pixels");XMapRaised(d,w);XSync(d,False);
    Pixmap p=XCreatePixmap(d,root,W,H,DefaultDepth(d,sn));
    Drawable targets[]={w,p};
    unsigned failures=0;
    for(int clip=0;clip<3;clip++) for(int render=0;render<2;render++) for(int aa=0;aa<2;aa++) for(int color=0;color<2;color++) {
        XftFont *font=XftFontOpen(d,sn,XFT_FAMILY,XftTypeString,"Luxi Sans",
            XFT_PIXEL_SIZE,XftTypeDouble,18.0,XFT_RENDER,XftTypeBool,render,
            XFT_ANTIALIAS,XftTypeBool,aa,NULL);
        if(!font) return 3;
        FcChar8 *file=NULL;
        FcBool actual_render=0,actual_aa=0;
        FcPatternGetString(font->pattern,FC_FILE,0,&file);
        FcPatternGetBool(font->pattern,XFT_RENDER,0,&actual_render);
        FcPatternGetBool(font->pattern,XFT_ANTIALIAS,0,&actual_aa);
        XRenderColor value={color?0xd300:0, color?0x4f00:0, color?0x8900:0,0xffff};
        XftColor foreground;
        if(!XftColorAllocValue(d,v,cmap,&value,&foreground)) return 4;
        for(int i=0;i<2;i++) {
            GC gc=XCreateGC(d,targets[i],0,NULL);
            XSetForeground(d,gc,0xc1c1c1);XFillRectangle(d,targets[i],gc,0,0,W,H);
            XFreeGC(d,gc);
            XftDraw *draw=XftDrawCreate(d,targets[i],v,cmap);
            if(clip==1) {
                XRectangle clips[]={{0,0,100,H},{140,12,160,20}};
                XftDrawSetClipRectangles(draw,0,0,clips,2);
            }
            XftDrawString8(draw,&foreground,font,clip==2?-11:8,clip==2?8:32,text,(int)strlen((const char *)text));
            XftDrawDestroy(draw);
        }
        XSync(d,False);
        XImage *a=XGetImage(d,w,0,0,W,H,AllPlanes,ZPixmap);
        XImage *b=XGetImage(d,p,0,0,W,H,AllPlanes,ZPixmap);
        unsigned bad=0,window_ink=0,pixmap_ink=0,max_delta=0;
        for(int y=0;y<H;y++) for(int x=0;x<W;x++) {
            unsigned long av=XGetPixel(a,x,y),bv=XGetPixel(b,x,y);
            if(av!=bv) bad++;
            for(int shift=0;shift<=16;shift+=8) {
                unsigned delta=(unsigned)abs((int)((av>>shift)&255)-(int)((bv>>shift)&255));
                if(delta>max_delta) max_delta=delta;
            }
            if(av!=0xc1c1c1) window_ink++;
            if(bv!=0xc1c1c1) pixmap_ink++;
        }
        printf("XFT clip=%d render=%d aa=%d color=%d actual=%d,%d ascent=%d descent=%d window_ink=%u pixmap_ink=%u mismatch=%u max_delta=%u file=%s\n",
            clip,render,aa,color,actual_render,actual_aa,font->ascent,font->descent,window_ink,pixmap_ink,bad,max_delta,file?(char *)file:"?");
        if(bad||!window_ink||!pixmap_ink||actual_render!=render||actual_aa!=aa) failures++;
        XDestroyImage(a);XDestroyImage(b);XftColorFree(d,v,cmap,&foreground);XftFontClose(d,font);
    }
    printf("XFT_%s failures=%u\n",failures?"FAILED":"PASS",failures);
    XFreePixmap(d,p);XDestroyWindow(d,w);XCloseDisplay(d);
    return failures?1:0;
}
