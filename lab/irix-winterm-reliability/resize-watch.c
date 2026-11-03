/* Native foreground-job witness for foreign terminal resize propagation. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
static volatile sig_atomic_t resized, expired;
static void notice(int sig) { if(sig==SIGWINCH)resized=1;else expired=1; }
int main(int argc,char **argv)
{
    struct winsize ws;
    struct sigaction action={0};
    sigset_t blocked, old;
    FILE *out;
    if(argc!=2 || getpgrp()!=tcgetpgrp(0))return 2;
    action.sa_handler=notice;sigemptyset(&action.sa_mask);
    sigemptyset(&blocked);sigaddset(&blocked,SIGWINCH);sigaddset(&blocked,SIGALRM);
    if(sigaction(SIGWINCH,&action,NULL)||sigaction(SIGALRM,&action,NULL)||
        sigprocmask(SIG_BLOCK,&blocked,&old)||ioctl(0,TIOCGWINSZ,&ws))return 3;
    out=fopen(argv[1],"wx");if(!out)return 4;
    fprintf(out,"READY rows=%u cols=%u foreground=1\n",ws.ws_row,ws.ws_col);fflush(out);
    alarm(20);
    while(!resized && !expired)sigsuspend(&old);
    alarm(0);
    if(!resized || ioctl(0,TIOCGWINSZ,&ws))return 5;
    fprintf(out,"RESIZED rows=%u cols=%u SIGWINCH=1\n",ws.ws_row,ws.ws_col);
    return fclose(out)!=0;
}
