/* Reuse the measured foreign exec fixture with a native target as argv[0]. */
#include <signal.h>
#include <unistd.h>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    sigset_t mask;sigemptyset(&mask);sigaddset(&mask,SIGINFO);sigaddset(&mask,SIGRTMIN);
    if(sigprocmask(SIG_BLOCK,&mask,NULL))return 3;
    char *av[]={"/tmp/xiri-shell/after-init",NULL},*env[]={NULL};
    execve(argv[1],av,env);return 4;
}
