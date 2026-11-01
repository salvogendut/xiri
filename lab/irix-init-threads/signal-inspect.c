/* Observe the native mask and pending queue independently of foreign queries.
 * SIGSTOP is an acknowledged barrier: if it arrived before the user store,
 * resume and retry. After the store the fixture spins without any syscall. */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <grp.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static long long now(void) {
    struct timespec ts;if(clock_gettime(CLOCK_MONOTONIC,&ts))exit(2);
    return (long long)ts.tv_sec*1000+ts.tv_nsec/1000000;
}
static int snapshot(pid_t pid,struct kinfo_proc2 *k) {
    int mib[6]={CTL_KERN,KERN_PROC2,KERN_PROC_PID,pid,sizeof(*k),1};
    size_t n=sizeof(*k);return sysctl(mib,6,k,&n,NULL,0) || n!=sizeof(*k);
}
static int waitfor(pid_t pid,int *status,int options,int ms) {
    long long end=now()+ms;
    do {
        pid_t got=waitpid(pid,status,options|WNOHANG);
        if(got==pid)return 0;
        if(got<0 && errno!=EINTR)return 1;
        poll(NULL,0,10);
    } while(now()<end);
    return 1;
}
int main(int argc,char **argv) {
    if(argc!=4)return 2;
    unsigned uid=(unsigned)strtoul(argv[1],NULL,10);int mode=atoi(argv[2]);
    if((uid!=0 && uid!=1234) || (mode!=0 && mode!=1))return 2;
    int in[2],out[2],status=0,valid=1,finished=0,stopped=0,observed=0;
    unsigned tries=0;uint32_t ready=0,mask[4]={0},pending[4]={0};
    if(pipe(in)||pipe(out))return 2;
    pid_t pid=fork();if(pid<0)return 2;
    if(!pid) {
        close(in[1]);close(out[0]);
        if(setpgid(0,0)||dup2(in[0],0)<0||dup2(out[1],1)<0)_exit(125);
        close(in[0]);close(out[1]);
        sigset_t mask;sigemptyset(&mask);sigaddset(&mask,SIGINFO);sigaddset(&mask,SIGRTMIN);
        if(sigprocmask(SIG_SETMASK,&mask,NULL)||setgroups(0,NULL)||setgid(uid)||setuid(uid))_exit(125);
        char *av[]={argv[3],NULL},*env[]={NULL};execve(argv[3],av,env);_exit(126);
    }
    close(in[0]);close(out[1]);signal(SIGPIPE,SIG_IGN);
    if(setpgid(pid,pid) && errno!=EACCES && errno!=ESRCH)valid=0;
    struct pollfd pfd={out[0],POLLIN,0};
    if(poll(&pfd,1,10000)<=0 || read(out[0],&ready,4)!=4 || ready!=0x58505453)valid=0;
    if(valid && write(in[1],"x",1)!=1)valid=0;
    close(in[1]);close(out[0]);
    uint32_t expected[4]={0x10000000U|(mode?0:0x4000U),1,0,0};
    struct kinfo_proc2 k;
    for(;valid && tries<50;tries++) {
        poll(NULL,0,20);
        if(kill(pid,SIGSTOP)||waitfor(pid,&status,WUNTRACED,5000)){valid=0;break;}
        if(!WIFSTOPPED(status)){finished=1;valid=0;break;}
        stopped=1;
        if(snapshot(pid,&k)){valid=0;break;}
        memcpy(mask,&k.p_sigmask,sizeof(mask));
        if(k.p_ruid!=uid || k.p_uid!=uid || k.p_rgid!=uid || k.p_gid!=uid || k.p__pgid!=pid){valid=0;break;}
        if(!memcmp(mask,expected,sizeof(mask))){observed=1;break;}
        if(kill(pid,SIGCONT)){valid=0;break;}
        stopped=0;
    }
    if(!observed)valid=0;
    if(valid) {
        if(kill(pid,SIGCONT)||kill(pid,SIGTERM))valid=0;
        stopped=0;
        if(valid && mode) {
            if(waitfor(pid,&status,0,5000))valid=0;
            else {finished=1;if(!WIFSIGNALED(status)||WTERMSIG(status)!=SIGTERM)valid=0;}
        } else if(valid) {
            long long end=now()+5000;
            do {
                if(snapshot(pid,&k)){valid=0;break;}
                memcpy(pending,&k.p_siglist,sizeof(pending));
                if(pending[0]&0x4000U)break;
                poll(NULL,0,10);
            } while(now()<end);
            if(!(pending[0]&0x4000U))valid=0;
        }
    }
    if(!finished) {
        if(kill(pid,SIGKILL) && errno!=ESRCH)valid=0;
        if(stopped)(void)kill(pid,SIGCONT);
        if(waitfor(pid,&status,0,5000))return 3;
        finished=1;
        if(!mode && (!WIFSIGNALED(status)||WTERMSIG(status)!=SIGKILL))valid=0;
    }
    int absent=kill(pid,0)<0 && errno==ESRCH;
    printf("SIGNAL uid=%u mode=%d observed=%d tries=%u mask=%08x,%08x,%08x,%08x pending=%08x,%08x,%08x,%08x exit=%d signal=%d absent=%d valid=%d\n",
        uid,mode,observed,tries+1,mask[0],mask[1],mask[2],mask[3],pending[0],pending[1],pending[2],pending[3],
        WIFEXITED(status)?WEXITSTATUS(status):-1,WIFSIGNALED(status)?WTERMSIG(status):0,absent,valid);
    return valid && absent ? 0 : 1;
}
