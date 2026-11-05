/* A bounded foreground/background job for tests through real terminals. */
#include <sys/types.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int report=-1;
static void event(int sig)
{
    if(sig==SIGCONT) {
        (void)write(report,"CONT\n",5);
        return;
    }
    if(sig==SIGINT)(void)write(report,"INT\n",4);
    else if(sig==SIGHUP)(void)write(report,"HUP\n",4);
    else if(sig==SIGTERM)(void)write(report,"TERM\n",5);
    else (void)write(report,"TIMEOUT\n",8);
    _exit(sig==SIGINT?42:sig==SIGALRM?124:43);
}

int main(int argc,char **argv)
{
    struct sigaction action;
    char line[256];int length;
    if(argc<2||argc>3)return 2;
    report=open(argv[1],O_WRONLY|O_CREAT|O_EXCL,0600);
    if(report<0)return 3;
    memset(&action,0,sizeof(action));action.sa_handler=event;
    sigemptyset(&action.sa_mask);
    if(sigaction(SIGINT,&action,NULL)||sigaction(SIGHUP,&action,NULL)||
        sigaction(SIGTERM,&action,NULL)||sigaction(SIGCONT,&action,NULL)||
        sigaction(SIGALRM,&action,NULL))return 4;
    length=snprintf(line,sizeof(line),"READY pid=%ld pgid=%ld sid=%ld tpgid=%ld uid=%ld foreground=%d\n",
        (long)getpid(),(long)getpgrp(),(long)getsid(0),(long)tcgetpgrp(0),
        (long)getuid(),tcgetpgrp(0)==getpgrp());
    if(length<0||(size_t)length>=sizeof(line)||write(report,line,(size_t)length)!=length)return 5;
    alarm(180);
    if(argc==3&&!strcmp(argv[2],"exit")) {
        (void)write(report,"EXIT37\n",7);
        return 37;
    }
    if(argc==3&&!strcmp(argv[2],"read")) {
        char byte;ssize_t n;
        do {n=read(0,&byte,1);} while(n<0&&errno==EINTR);
        if(n!=1)return 6;
        (void)write(report,"READ\n",5);
        return 0;
    }
    for(;;)pause();
}
