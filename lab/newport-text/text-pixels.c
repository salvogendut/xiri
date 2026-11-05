/* Compare window text with the same X11 request rendered to a pixmap. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    enum { W=300,H=60 };
    const char *text="Toolchest Disabled entry 012345";
    const char *pattern=argc>1?argv[1]:"fixed";
    const char bits[]={0x55,(char)0xaa,0x55,(char)0xaa,0x55,(char)0xaa,0x55,(char)0xaa};
    Display *d=XOpenDisplay(NULL);
    if (!d) return 2;
    alarm(30);
    int sn=DefaultScreen(d);
    Window root=RootWindow(d,sn);
    XFontStruct *font=XLoadQueryFont(d,pattern);
    if (!font) return 3;
    XSetWindowAttributes wa;
    wa.override_redirect=True;wa.background_pixel=0xc1c1c1;
    Window w=XCreateWindow(d,root,593,607,W,H,0,CopyFromParent,InputOutput,
        CopyFromParent,CWOverrideRedirect|CWBackPixel,&wa);
    XStoreName(d,w,"Xiri text pixels");XMapRaised(d,w);XSync(d,False);
    Pixmap p=XCreatePixmap(d,root,W,H,DefaultDepth(d,sn));
    Pixmap stipple=XCreateBitmapFromData(d,root,bits,8,8);
    Pixmap tile=XCreatePixmap(d,root,3,2,DefaultDepth(d,sn));
    GC tg=XCreateGC(d,tile,0,NULL);
    XSetForeground(d,tg,0x2473b5);XFillRectangle(d,tile,tg,0,0,3,2);
    XSetForeground(d,tg,0xd34f89);XDrawPoint(d,tile,tg,1,0);XDrawPoint(d,tile,tg,2,1);
    XFreeGC(d,tg);
    Drawable targets[]={w,p};
    unsigned total_bad=0;
    for(int clip=0;clip<3;clip++) for(int style=0;style<5;style++) {
        for(int i=0;i<2;i++) {
            GC gc=XCreateGC(d,targets[i],0,NULL);
            XSetForeground(d,gc,0xc1c1c1);XFillRectangle(d,targets[i],gc,0,0,W,H);
            XSetFont(d,gc,font->fid);XSetForeground(d,gc,0x555555);XSetBackground(d,gc,0xc1c1c1);
            XSetStipple(d,gc,stipple);XSetTile(d,gc,tile);XSetTSOrigin(d,gc,3,5);
            if(clip==1) {
                XRectangle clips[]={{0,0,100,H},{140,12,160,20}};
                XSetClipRectangles(d,gc,0,0,clips,2,Unsorted);
            }
            XSetFillStyle(d,gc,style==1?FillStippled:style==2?FillOpaqueStippled:style==3?FillTiled:FillSolid);
            if (style==4) XDrawImageString(d,targets[i],gc,clip==2?-11:8,clip==2?8:32,text,(int)strlen(text));
            else XDrawString(d,targets[i],gc,clip==2?-11:8,clip==2?8:32,text,(int)strlen(text));
            XFreeGC(d,gc);
        }
        XSync(d,False);
        XImage *a=XGetImage(d,w,0,0,W,H,AllPlanes,ZPixmap);
        XImage *b=XGetImage(d,p,0,0,W,H,AllPlanes,ZPixmap);
        unsigned bad=0,window_ink=0,pixmap_ink=0;
        for(int y=0;y<H;y++) for(int x=0;x<W;x++) {
            unsigned long av=XGetPixel(a,x,y),bv=XGetPixel(b,x,y);
            if(av!=bv) bad++;
            if(av!=0xc1c1c1) window_ink++;
            if(bv!=0xc1c1c1) pixmap_ink++;
        }
        printf("TEXT clip=%d style=%d ascent=%d descent=%d window_ink=%u pixmap_ink=%u mismatch=%u\n",
            clip,style,font->ascent,font->descent,window_ink,pixmap_ink,bad);
        total_bad+=bad;
        if(!window_ink || !pixmap_ink) total_bad++;
        XDestroyImage(a);XDestroyImage(b);
    }
    printf("TEXT_%s mismatches=%u\n",total_bad?"FAILED":"PASS",total_bad);
    XFreeFont(d,font);XFreePixmap(d,tile);XFreePixmap(d,stipple);XFreePixmap(d,p);XDestroyWindow(d,w);XCloseDisplay(d);
    return total_bad?1:0;
}
