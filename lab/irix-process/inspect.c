/* Native supervisor: snapshot real masks/IDs while each foreign process waits
 * for a pipe token, then verify exit and process-group cleanup. */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static long long now(void) {struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))exit(2);return (long long)t.tv_sec*1000+t.tv_nsec/1000000;}
static void dump(const char *label,const unsigned char *p,size_t n) {printf("%s bytes=%zu hex=",label,n);for(size_t i=0;i<n;i++)printf("%02x",p[i]);putchar('\n');}
int main(int argc,char **argv) {
    if(argc!=4)return 2;
    char *end;errno=0;unsigned long uid=strtoul(argv[1],&end,10);
    if(errno || *end || (uid!=0 && uid!=1234))return 2;
    int kind=atoi(argv[2]);if(kind!=0 && kind!=1)return 2;
    int in[2],out[2],err[2],status=0,finished=0,released=0,timedout=0,valid=1;
    unsigned char data[4096],errors[4096];size_t used=0,eused=0;
    if(pipe(in)||pipe(out)||pipe(err))return 2;
    if(fcntl(out[0],F_SETFL,O_NONBLOCK)<0 || fcntl(err[0],F_SETFL,O_NONBLOCK)<0)return 2;
    pid_t pid=fork();if(pid<0)return 2;
    if(pid==0) {
        close(in[1]);close(out[0]);close(err[0]);
        if(setpgid(0,0) || dup2(in[0],0)<0 || dup2(out[1],1)<0 || dup2(err[1],2)<0)_exit(125);
        close(in[0]);close(out[1]);close(err[1]);
        sigset_t mask;sigemptyset(&mask);sigaddset(&mask,SIGINFO);sigaddset(&mask,SIGRTMIN);
        if(sigprocmask(SIG_SETMASK,&mask,NULL) || setgroups(0,NULL) || setgid(uid) || setuid(uid))_exit(125);
        char *av[]={argv[3],NULL},*env[]={NULL};execve(argv[3],av,env);perror("execve");_exit(126);
    }
    close(in[0]);close(out[1]);close(err[1]);
    signal(SIGPIPE,SIG_IGN);
    if(setpgid(pid,pid) && errno!=EACCES && errno!=ESRCH)valid=0;
    long long deadline=now()+10000;
    struct pollfd pfd[2]={{out[0],POLLIN,0},{err[0],POLLIN,0}};
    while(!finished) {
        if(poll(pfd,2,10)<0 && errno!=EINTR){valid=0;break;}
        ssize_t n;
        while(used<sizeof(data) && (n=read(out[0],data+used,sizeof(data)-used))>0)used+=(size_t)n;
        while(eused<sizeof(errors) && (n=read(err[0],errors+eused,sizeof(errors)-eused))>0)eused+=(size_t)n;
        if(!released && used>=(size_t)(kind?512:256)) {
            for(int i=0;i<(kind?2:1);i++) {
                uint32_t rec[64];memcpy(rec,data+i*256,sizeof(rec));
                struct kinfo_proc2 k;size_t size=sizeof(k);
                int mib[6]={CTL_KERN,KERN_PROC2,KERN_PROC_PID,(int)rec[60],sizeof(k),1};
                if(rec[0]!=0x58505243 || sysctl(mib,6,&k,&size,NULL,0) || size!=sizeof(k) || k.p_uid!=uid || k.p_ruid!=uid || k.p__pgid!=pid){valid=0;break;}
                uint32_t bits[4];memcpy(bits,&k.p_sigmask,sizeof(bits));
                printf("SNAP role=%u pid=%d ppid=%d pgid=%d ids=%u,%u,%u,%u groups=%d mask=%08x,%08x,%08x,%08x\n",rec[55],k.p_pid,k.p_ppid,k.p__pgid,k.p_ruid,k.p_uid,k.p_rgid,k.p_gid,k.p_ngroups,bits[0],bits[1],bits[2],bits[3]);
            }
            if(write(in[1],"xx",kind?2:1)!=(kind?2:1))valid=0;
            close(in[1]);released=1;
        }
        pid_t got=waitpid(pid,&status,WNOHANG);
        if(got==pid)finished=1;
        else if(got<0 && errno!=EINTR){valid=0;break;}
        if(!valid || now()>deadline || used==sizeof(data) || eused==sizeof(errors)) {timedout=now()>deadline;break;}
    }
    if(kill(-pid,SIGKILL) && errno!=ESRCH)valid=0;
    if(!finished){if(kill(pid,SIGKILL) && errno!=ESRCH)valid=0;while(waitpid(pid,&status,0)<0)if(errno!=EINTR){valid=0;break;}}
    if(!released)close(in[1]);
    ssize_t n;
    while(used<sizeof(data) && (n=read(out[0],data+used,sizeof(data)-used))>0)used+=(size_t)n;
    while(eused<sizeof(errors) && (n=read(err[0],errors+eused,sizeof(errors)-eused))>0)eused+=(size_t)n;
    close(out[0]);close(err[0]);
    deadline=now()+5000;int absent=0;
    do {if(kill(-pid,0)<0 && errno==ESRCH){absent=1;break;}poll(NULL,0,10);}while(now()<deadline);
    printf("OBS pid=%d exit=%d signal=%d timeout=%d valid=%d released=%d group_absent=%d\n",pid,WIFEXITED(status)?WEXITSTATUS(status):-1,WIFSIGNALED(status)?WTERMSIG(status):0,timedout,valid,released,absent);
    dump("STDOUT",data,used);dump("STDERR",errors,eused);
    return valid && released && absent && !timedout ? 0 : 1;
}
