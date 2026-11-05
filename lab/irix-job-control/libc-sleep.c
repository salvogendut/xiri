/* Exercise the original libc wrappers as well as the raw trap observers. */
#include <sys/types.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t notices;
static void notice(int sig){(void)sig;notices++;}

int main(int argc,char **argv)
{
    int mode=argc>1?atoi(argv[1]):0,rc,error,status=0;
    pid_t child=0,parent=getpid();
    struct sigaction action;
    struct timespec request={0,20000000},remaining={123,456};
    struct timeval before,after;
    if(mode<0||mode>2)return 2;
    if(usleep(1000))return 3;
    memset(&action,0,sizeof(action));action.sa_handler=notice;
    action.sa_flags=mode==2?SA_RESTART:0;sigemptyset(&action.sa_mask);
    if(sigaction(SIGUSR1,&action,NULL))return 4;
    if(mode) {
        request.tv_sec=1;request.tv_nsec=0;
        child=fork();if(child<0)return 5;
        if(!child) {
            if(usleep(100000)||kill(parent,SIGUSR1))_exit(80);
            _exit(0);
        }
    }
    if(gettimeofday(&before,NULL))return 6;
    errno=0;rc=nanosleep(&request,&remaining);error=errno;
    if(gettimeofday(&after,NULL))return 7;
    if(child) {
        pid_t got;
        do {got=waitpid(child,&status,0);} while(got<0&&errno==EINTR);
        if(got!=child||!WIFEXITED(status)||WEXITSTATUS(status))return 8;
    }
    printf("LIBC_SLEEP mode=%d rc=%d errno=%d notices=%d remaining=%ld,%ld elapsed_us=%ld helper_reaped=%d\n",
        mode,rc,error,(int)notices,(long)remaining.tv_sec,(long)remaining.tv_nsec,
        (long)(after.tv_sec-before.tv_sec)*1000000+after.tv_usec-before.tv_usec,mode!=0);
    return mode==1 ? rc!=-1||error!=EINTR||notices!=1 : rc!=0||notices!=(mode!=0);
}
