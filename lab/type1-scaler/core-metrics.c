/* Diagnose core-font metrics independently of IRIX and Newport window drawing. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xatom.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void info(Display *d,const char *kind,XFontStruct *f)
{
 unsigned long value=0;char *name=NULL;
 if(XGetFontProperty(f,XA_FONT,&value))name=XGetAtomName(d,value);
 printf("%s name=%s ascent=%d descent=%d min=%d,%d,%d,%d,%d max=%d,%d,%d,%d,%d per_char=%d\n",kind,name?name:"?",f->ascent,f->descent,
 f->min_bounds.lbearing,f->min_bounds.rbearing,f->min_bounds.width,f->min_bounds.ascent,f->min_bounds.descent,
 f->max_bounds.lbearing,f->max_bounds.rbearing,f->max_bounds.width,f->max_bounds.ascent,f->max_bounds.descent,f->per_char!=NULL);
 if(name)XFree(name);
}
static void render(Display *d,XFontStruct *f)
{
 int s=DefaultScreen(d);unsigned long white=WhitePixel(d,s),black=BlackPixel(d,s);
 Pixmap p=XCreatePixmap(d,RootWindow(d,s),300,80,DefaultDepth(d,s));GC gc=XCreateGC(d,p,0,NULL);
 XSetForeground(d,gc,white);XFillRectangle(d,p,gc,0,0,300,80);XSetForeground(d,gc,black);XSetFont(d,gc,f->fid);
 XDrawString(d,p,gc,10,45,"MMggCourier",11);XSync(d,False);
 XImage *im=XGetImage(d,p,0,0,300,80,AllPlanes,ZPixmap);if(!im)exit(6);
 int xmin=300,xmax=-1,ymin=80,ymax=-1;unsigned ink=0;unsigned long hash=2166136261UL;
 for(int y=0;y<80;y++)for(int x=0;x<300;x++){
  unsigned long v=XGetPixel(im,x,y);hash=((hash^v)*16777619UL)&0xffffffffUL;
  if(v!=white){ink++;if(x<xmin)xmin=x;if(x>xmax)xmax=x;if(y<ymin)ymin=y;if(y>ymax)ymax=y;}
 }
 printf("PIXMAP ink=%u bbox=%d,%d,%d,%d hash=%08lx\n",ink,xmin,ymin,xmax,ymax,hash);
 XDestroyImage(im);XFreeGC(d,gc);XFreePixmap(d,p);
}
int main(int argc,char **argv)
{
 const char *mode=argc>1?argv[1]:"open";
 const char *pattern=argc>2?argv[2]:"-ibm-courier-bold-r-normal--20-145-100-100-m-110-iso8859-1";
 int repeat=argc>3?atoi(argv[3]):1;
 setlocale(LC_ALL,"");Display *d=XOpenDisplay(NULL);if(!d)return 2;alarm(120);
 for(int n=0;n<repeat;n++){
  printf("REPEAT %d mode=%s pattern=%s\n",n,mode,pattern);
  if(!strcmp(mode,"list")){
   XFontStruct *fonts=NULL;int count=0;char **names=XListFontsWithInfo(d,pattern,16,&count,&fonts);
   printf("LIST count=%d\n",count);
   for(int i=0;i<count;i++)info(d,"LIST_FONT",fonts+i);
   if(names)XFreeFontInfo(names,fonts,count);
  }else if(!strcmp(mode,"set")){
   char **missing=NULL,*def=NULL;int count=0;
   XFontSet set=XCreateFontSet(d,pattern,&missing,&count,&def);if(!set)return 4;
   XFontStruct **fonts;char **names;int nf=XFontsOfFontSet(set,&fonts,&names);
   for(int i=0;i<nf;i++)info(d,"SET_FONT",fonts[i]);
   if(missing)XFreeStringList(missing);
   XFreeFontSet(d,set);
  }else{
   XFontStruct *f=XLoadQueryFont(d,pattern);if(!f)return 5;
   info(d,"OPEN_FONT",f);render(d,f);XFreeFont(d,f);
  }
 }
 XCloseDisplay(d);return 0;
}
