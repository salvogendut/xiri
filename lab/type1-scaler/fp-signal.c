#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <unistd.h>
static volatile sig_atomic_t signals;
static volatile double source = 14.5;
static void tick(int sig) { (void)sig; signals++; }
__attribute__((noinline)) static int convert(double scale)
{
    (void)getpid();
    return (int)(scale * 64.0 + 0.5);
}
int main(int argc,char **argv)
{
    int count=argc>1?atoi(argv[1]):1000000;
    struct sigaction action = {0};
    struct itimerval timer = {{0,1000},{0,1000}};
    action.sa_handler=tick;sigemptyset(&action.sa_mask);
    if(sigaction(SIGALRM,&action,NULL) || setitimer(ITIMER_REAL,&timer,NULL))return 2;
    for(int n=0;n<count;n++) {
        double scale=source;
        int value=convert(scale);
        if(value!=928) {
            printf("FP_FAIL iteration=%d scale=%.17g result=%d signals=%d\n",n,scale,value,(int)signals);
            return 1;
        }
    }
    printf("FP_PASS iterations=%d signals=%d\n",count,(int)signals);
    return 0;
}
