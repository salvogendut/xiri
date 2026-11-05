/* Bound one probe and its inherited process group on the reference system. */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static volatile sig_atomic_t owned, expired;
static void timeout(int sig)
{
    (void)sig;
    expired=1;
    if(owned>0)kill(-(pid_t)owned,SIGKILL);
}

int main(int argc,char **argv)
{
    struct sigaction action={0};
    pid_t pid, got;
    int status=0, absent=0, i, descriptor;
    FILE *log;
    if(argc<3 || argv[2][0]=='-')return 2;
    /* Reserve a new log before starting the child; never truncate a path. */
    descriptor=open(argv[1],O_WRONLY|O_CREAT|O_EXCL,0600);
    if(descriptor<0)return 8;
    log=fdopen(descriptor,"w");if(!log)return 8;
    action.sa_handler=timeout;
    action.sa_flags=0;
    sigemptyset(&action.sa_mask);
    if(sigaction(SIGALRM,&action,NULL))return 3;
    pid=fork();if(pid<0)return 4;
    if(!pid) {
        close(descriptor);
        if(setpgid(0,0))_exit(125);
        execv(argv[2],argv+2);
        _exit(126);
    }
    if(setpgid(pid,pid) && errno!=EACCES && errno!=ESRCH)return 5;
    owned=pid;
    alarm(10);
    do {got=waitpid(pid,&status,0);} while(got<0 && errno==EINTR);
    alarm(0);
    if(kill(-pid,SIGKILL) && errno!=ESRCH)return 6;
    for(i=0;i<500;i++) {
        if(kill(-pid,0)<0 && errno==ESRCH){absent=1;break;}
        if(usleep(10000) && errno!=EINTR)return 7;
    }
    fprintf(log,"GUARD reaped=%d exit=%d signal=%d timeout=%d absent=%d\n",
        got==pid,WIFEXITED(status)?WEXITSTATUS(status):-1,
        WIFSIGNALED(status)?WTERMSIG(status):0,(int)expired,absent);
    if(fclose(log))return 9;
    return got!=pid || expired || !absent ||
        !WIFEXITED(status) || WEXITSTATUS(status)!=0;
}
