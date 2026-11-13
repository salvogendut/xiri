/* Independent wire-level source/receiver for the live X bridge.
 * No filesystem operation is requested: success means exact URI transfer.
 */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <assert.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include <time.h>
static Display *d;
static Window source, target, proxy;
static Atom motif, sgisel, sgi, receiver, uri, xdsel, data;
static Atom xdenter, xdpos, xdstatus, xddrop, xdleave, xdfinish, copy;
static Atom good, bad;
static Time stamp;
static int little, version=5, plain, cancel_case, reject_case, gone_case, drop_only;
static unsigned completion;
static int sent_drop, received_enter, received_drop, received_data, replies, passthrough;
static Window xdsource;
static char payload[1024];
static const char expected[]="file:///tmp/a%20%22quoted%22%20%5C%20%25%20%23.txt\r\nfile:///tmp/b.txt\r\n";
static void put(unsigned char *p,unsigned n,int width)
{ for(int i=0;i<width;i++){p[little?i:width-1-i]=n;n>>=8;} }
static unsigned get(const unsigned char *p,int width,int le)
{ unsigned n=0;for(int i=0;i<width;i++)n=(n<<8)|p[le?width-1-i:i];return n; }
static long long now(void)
{ struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (long long)t.tv_sec*1000+t.tv_nsec/1000000; }
static void send_motif(int op)
{
 XEvent e={0};e.xclient.type=ClientMessage;e.xclient.window=target;e.xclient.message_type=motif;e.xclient.format=8;
 unsigned char *b=(unsigned char *)e.xclient.data.b;b[0]=op;b[1]=little?'l':'B';put(b+4,stamp,4);
 if(op==0){put(b+8,source,4);put(b+12,sgisel,4);}
 else if(op==1)put(b+8,source,4);
 else {put(b+2,0x0711+(op==5?completion:0),2);put(b+8,700,2);put(b+10,300,2);if(op==5){put(b+12,sgisel,4);put(b+16,source,4);}}
 XSendEvent(d,proxy,False,0,&e);XFlush(d);
}
static void send_xdnd(Atom kind,long flags,long action)
{
 XEvent e={0};e.xclient.type=ClientMessage;e.xclient.window=xdsource;e.xclient.message_type=kind;e.xclient.format=32;
 e.xclient.data.l[0]=target;e.xclient.data.l[1]=flags;
 e.xclient.data.l[kind==xdstatus?4:2]=action;
 XSendEvent(d,xdsource,False,0,&e);XFlush(d);
}
static void notify(XSelectionRequestEvent *q,Atom type,int format,const unsigned char *value,int count)
{
 Atom prop=q->property?q->property:q->target;
 XChangeProperty(d,q->requestor,prop,type,format,PropModeReplace,value,count);
 XEvent e={0};e.xselection.type=SelectionNotify;e.xselection.requestor=q->requestor;
 e.xselection.selection=q->selection;e.xselection.target=q->target;e.xselection.property=prop;e.xselection.time=q->time;
 XSendEvent(d,q->requestor,False,0,&e);XFlush(d);
}
static void stopped(int sig){(void)sig;fputs("Protocol deadline\n",stderr);_exit(124);}
int main(int argc,char **argv)
{
 assert(argc==2 || argc==3);const char *which=argv[1];
 little=strstr(which,"little")!=NULL;version=strstr(which,"v3")?3:5;
 plain=!strcmp(which,"passthrough");cancel_case=!strcmp(which,"cancel");
 reject_case=!strcmp(which,"reject");gone_case=!strcmp(which,"target-gone");drop_only=!strcmp(which,"drop-only");
 completion=!strcmp(which,"cancel-drop")?0x2000:!strcmp(which,"drop-help")?0x1000:0;
 d=XOpenDisplay(NULL);assert(d);signal(SIGALRM,stopped);alarm(12);
 Window root=DefaultRootWindow(d);
 source=XCreateSimpleWindow(d,root,0,0,1,1,0,0,0);target=XCreateSimpleWindow(d,root,650,100,600,500,0,0,0xffffff);
 XSelectInput(d,source,PropertyChangeMask);XSelectInput(d,target,PropertyChangeMask|StructureNotifyMask);
#define A(v,n) v=XInternAtom(d,n,False)
 A(motif,"_MOTIF_DRAG_AND_DROP_MESSAGE");A(sgisel,"_XIRI_TEST_DRAG");A(sgi,"_SGI_ICON");A(receiver,"_MOTIF_DRAG_RECEIVER_INFO");
 A(uri,"text/uri-list");A(xdsel,"XdndSelection");A(data,"_XIRI_TEST_DATA");
 A(xdenter,"XdndEnter");A(xdpos,"XdndPosition");A(xdstatus,"XdndStatus");A(xddrop,"XdndDrop");A(xdleave,"XdndLeave");A(xdfinish,"XdndFinished");A(copy,"XdndActionCopy");
 A(good,"XmTRANSFER_SUCCESS");A(bad,"XmTRANSFER_FAILURE");
#undef A
 Atom initiator=XInternAtom(d,"_MOTIF_DRAG_INITIATOR_INFO",False),table=XInternAtom(d,"_MOTIF_DRAG_TARGETS",False);
 Atom dw=XInternAtom(d,"_MOTIF_DRAG_WINDOW",False),aware=XInternAtom(d,"XdndAware",False);
 unsigned char original[16]={0};original[0]=little?'l':'B';original[2]=5;put(original+12,16,4);
 if(strcmp(which,"native"))XChangeProperty(d,target,receiver,receiver,8,PropModeReplace,original,16);
 unsigned long v=version;XChangeProperty(d,target,aware,XA_ATOM,32,PropModeReplace,(unsigned char *)&v,1);
 XMapWindow(d,target);XFlush(d);
 long long until=now()+3000;
 while(now()<until){
  Atom type;int format;unsigned long n,left;unsigned char *p=NULL;
  XGetWindowProperty(d,target,receiver,0,16,False,receiver,&type,&format,&n,&left,&p);
  if(p && format==8 && n==16)proxy=get(p+4,4,p[0]=='l');
  if(p)XFree(p);
  if(proxy)break;
  usleep(10000);
 }
 assert(proxy);
 if(!strcmp(which,"restore")){
  assert(argc==3);pid_t pid=(pid_t)strtol(argv[2],NULL,10);assert(pid>1);assert(!kill(pid,SIGTERM));
  until=now()+3000;
  while(now()<until){
   Atom type;int format;unsigned long n,left;unsigned char *p=NULL;
   XGetWindowProperty(d,target,receiver,0,16,False,receiver,&type,&format,&n,&left,&p);
   int restored=p && format==8 && n==16 && !memcmp(p,original,16);
   if(p)XFree(p);
   if(restored){puts("PASS restore");XCloseDisplay(d);return 0;}
   usleep(10000);
  }
  assert(0);
 }
 unsigned char init[8]={0},list[14]={0};init[0]=list[0]=little?'l':'B';put(init+4,sgisel,4);
 put(list+2,1,2);put(list+4,14,4);put(list+8,1,2);put(list+10,plain?XA_STRING:sgi,4);
 XChangeProperty(d,source,sgisel,initiator,8,PropModeReplace,init,8);
 XChangeProperty(d,source,table,table,8,PropModeReplace,list,14);
 XChangeProperty(d,root,dw,XA_WINDOW,32,PropModeReplace,(unsigned char *)&source,1);
 XSetSelectionOwner(d,sgisel,source,CurrentTime);
 XChangeProperty(d,source,data,XA_STRING,8,PropModeReplace,(unsigned char *)"x",1);XFlush(d);
 XEvent event;
 do{XNextEvent(d,&event);}while(event.type!=PropertyNotify || event.xproperty.atom!=data);
 stamp=event.xproperty.time;
 char host[256];assert(!gethostname(host,sizeof(host)));host[sizeof(host)-1]=0;
 int first=snprintf(payload,sizeof(payload),"Category:File Name:\"/tmp/a \"\"quoted\"\" \\ %% #.txt\" Host:%s ",host);
 int second=snprintf(payload+first+1,sizeof(payload)-first-1,"Category:File Name:\"/tmp/b.txt\" Host:%s ",host);
 int bytes=first+second+2;
 if(drop_only){sent_drop=1;send_motif(5);}else{send_motif(0);send_motif(2);}
 until=now()+8000;
 while(now()<until){
  if(!XPending(d)){
   fd_set f;FD_ZERO(&f);FD_SET(ConnectionNumber(d),&f);struct timeval tv={0,100000};
   if(select(ConnectionNumber(d)+1,&f,NULL,NULL,&tv)<=0)continue;
  }
  XNextEvent(d,&event);
  if(event.type==SelectionRequest){
   XSelectionRequestEvent *q=&event.xselectionrequest;
   if(q->target==sgi)notify(q,sgi,8,(unsigned char *)payload,bytes);
   else if(q->target==good || q->target==bad){
    int expected_ok=!reject_case&&!gone_case&&!completion;
    assert((q->target==good)==expected_ok);assert(received_data==expected_ok);
    if(expected_ok)assert(received_enter && received_drop);
    notify(q,q->target,32,NULL,0);printf("PASS %s\n",which);XCloseDisplay(d);return 0;
   }else assert(0);
  }else if(event.type==SelectionNotify && event.xselection.target==uri){
   Atom type;int format;unsigned long n,left;unsigned char *p;
   assert(event.xselection.property==data);
   XGetWindowProperty(d,target,data,0,1024,True,uri,&type,&format,&n,&left,&p);
   assert(type==uri && format==8 && left==0 && n==strlen(expected) && !memcmp(p,expected,n));XFree(p);
   received_data=1;send_xdnd(xdfinish,version>=5?1:0,version>=5?copy:0);
  }else if(event.type==ClientMessage){
   XClientMessageEvent *e=&event.xclient;
   if(e->message_type==motif){
    unsigned char *p=(unsigned char *)e->data.b;
    if(e->window==target){assert(plain);passthrough++;if(passthrough==2){send_motif(1);}if(passthrough==3){puts("PASS passthrough");XCloseDisplay(d);return 0;}}
    else {
     assert(e->window==source);replies++;
     if((p[0]&127)!=5 && !sent_drop){
      if(cancel_case){send_motif(1);sent_drop=1;}
      else {send_motif(1);send_motif(5);sent_drop=1;}
     }
    }
   }else if(e->message_type==xdenter){assert(!plain);received_enter=1;xdsource=e->data.l[0];assert((Atom)e->data.l[2]==uri);}
   else if(e->message_type==xdpos){assert(received_enter);send_xdnd(xdstatus,reject_case?0:3,reject_case?0:copy);}
   else if(e->message_type==xddrop){
    assert(!cancel_case && !reject_case && !completion);received_drop=1;
    if(gone_case){XDestroyWindow(d,target);XFlush(d);}else XConvertSelection(d,xdsel,uri,data,target,e->data.l[2]);
   }else if(e->message_type==xdleave && cancel_case){assert(!received_drop && !received_data && replies);puts("PASS cancel");XCloseDisplay(d);return 0;}
  }
  XFlush(d);
 }
 fprintf(stderr,"FAIL %s enter=%d drop=%d data=%d replies=%d\n",which,received_enter,received_drop,received_data,replies);return 1;
}
