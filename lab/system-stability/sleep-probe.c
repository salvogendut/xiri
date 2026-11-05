/* Native diagnostic: an ordinary child sleeps while its parent independently
 * records clocks, scheduler state and VM counters. No Xlib or foreign calls. */
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/select.h>
#include <sys/sysctl.h>
#include <sys/wait.h>
#include <uvm/uvm_extern.h>
#include <uvm/uvm_param.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stop;
static void request_stop(int sig) { stop = sig; }
static void expired(int sig)
{
    static const char text[] = "SLEEP_TIMEOUT\n";
    (void)sig;
    (void)write(STDERR_FILENO, text, sizeof(text)-1);
    _exit(124);
}
static long long clock_ns(clockid_t id)
{
    struct timespec t;
    if (clock_gettime(id, &t)) { perror("clock_gettime"); exit(2); }
    return (long long)t.tv_sec*1000000000 + t.tv_nsec;
}
static void worker(const char *method, unsigned count)
{
    signal(SIGALRM, expired);
    for (unsigned i=1; i<=count; ++i) {
        alarm(10);
        long long begin = clock_ns(CLOCK_MONOTONIC);
        printf("SLEEP_BEGIN pid=%d method=%s iteration=%u mono_ns=%lld\n",
            getpid(), method, i, begin);
        int rc;
        errno=0;
        if (!strcmp(method,"usleep")) rc=usleep(200000);
        else if (!strcmp(method,"nanosleep")) {
            struct timespec delay={0,200000000}; rc=nanosleep(&delay,NULL);
        } else {
            struct timeval delay={0,200000}; rc=select(0,NULL,NULL,NULL,&delay);
        }
        int error=errno;
        long long end=clock_ns(CLOCK_MONOTONIC);
        alarm(0);
        printf("SLEEP_END pid=%d method=%s iteration=%u mono_ns=%lld elapsed_ns=%lld rc=%d errno=%d\n",
            getpid(), method, i, end, end-begin, rc, error);
        if (rc || end-begin<200000000 || end-begin>=10000000000LL) _exit(3);
    }
    _exit(0);
}
static int observe(pid_t child)
{
    long long mono=clock_ns(CLOCK_MONOTONIC), real=clock_ns(CLOCK_REALTIME);
    struct kinfo_lwp l;
    int mib[]={CTL_KERN,KERN_LWP,child,sizeof(l),1};
    size_t size=sizeof(l);
    memset(&l,0,sizeof(l));
    if (sysctl(mib,5,&l,&size,NULL,0)) {
        /* proc_find excludes zombies; an exit can race the preceding
         * WNOHANG check. A disappearing LWP is a missing sample, never a
         * completion verdict. Only waitpid below decides the child's result. */
        if (errno==ESRCH || errno==EAGAIN) {
            printf("SAMPLE_UNAVAILABLE mono_ns=%lld pid=%d errno=%d\n",mono,child,errno);
            return 0;
        }
        perror("KERN_LWP"); return 1;
    }
    struct uvmexp_sysctl vm;
    int vmmib[]={CTL_VM,VM_UVMEXP2};
    size_t vmsize=sizeof(vm);
    if (sysctl(vmmib,2,&vm,&vmsize,NULL,0) || vmsize!=sizeof(vm)) {
        perror("VM_UVMEXP2"); return 1;
    }
    uint64_t cpu[5];
    int cpumib[]={CTL_KERN,KERN_CP_TIME};
    size_t cpusize=sizeof(cpu);
    if (sysctl(cpumib,2,cpu,&cpusize,NULL,0) || cpusize!=sizeof(cpu)) {
        perror("KERN_CP_TIME"); return 1;
    }
    printf("SAMPLE mono_ns=%lld real_ns=%lld pid=%d present=%d state=%d flags=%x schedflags=%x "
        "wmesg=%.*s lwp=%llx uarea=%llx wchan=%llx slptime=%u "
        "free=%lld active=%lld inactive=%lld paging=%lld swap=%lld pageins=%lld pgwait=%lld "
        "intrs=%lld switches=%lld cpu=%llu,%llu,%llu,%llu,%llu\n",
        mono,real,child,size==sizeof(l),l.l_stat,l.l_flag,l.l_schedflags,
        (int)sizeof(l.l_wmesg),l.l_wmesg,(unsigned long long)l.l_laddr,
        (unsigned long long)l.l_addr,(unsigned long long)l.l_wchan,l.l_slptime,
        (long long)vm.free,(long long)vm.active,(long long)vm.inactive,
        (long long)vm.paging,(long long)vm.swpginuse,(long long)vm.pageins,
        (long long)vm.fltpgwait,(long long)vm.intrs,(long long)vm.swtch,
        (unsigned long long)cpu[0],(unsigned long long)cpu[1],
        (unsigned long long)cpu[2],(unsigned long long)cpu[3],(unsigned long long)cpu[4]);
    return 0;
}
int main(int argc,char **argv)
{
    if (argc!=3 || (strcmp(argv[1],"usleep") && strcmp(argv[1],"nanosleep") &&
        strcmp(argv[1],"select") && strcmp(argv[1],"exit-control"))) return 2;
    char *end;
    unsigned long count=strtoul(argv[2],&end,10);
    if (!*argv[2] || *end || count<1 || count>1000) return 2;
    setvbuf(stdout,NULL,_IOLBF,0);
    setvbuf(stderr,NULL,_IONBF,0);
    pid_t child=fork();
    if (child<0) return 2;
    if (!child) {
        if (!strcmp(argv[1],"exit-control")) _exit(37);
        worker(argv[1],(unsigned)count);
    }
    signal(SIGALRM,request_stop); signal(SIGTERM,request_stop); signal(SIGINT,request_stop);
    alarm(300);
    if (!strcmp(argv[1],"exit-control")) {
        siginfo_t info;
        memset(&info,0,sizeof(info));
        int rc;
        do rc=waitid(P_PID,child,&info,WEXITED|WNOWAIT); while (rc<0 && errno==EINTR);
        if (rc || info.si_pid!=child || info.si_status!=37) return 2;
        int observation=observe(child), status;
        pid_t done;
        do done=waitpid(child,&status,0); while (done<0 && errno==EINTR);
        int valid=done==child && WIFEXITED(status) && WEXITSTATUS(status)==37 && !observation;
        printf("EXIT_CONTROL child=%d observed_exit=37 reaped=%d valid=%d\n",child,done==child,valid);
        return valid?0:2;
    }
    int status=0, failed=0;
    for (;;) {
        pid_t done=waitpid(child,&status,WNOHANG);
        if (done==child) break;
        if (done<0 && errno!=EINTR) { perror("waitpid"); failed=1; break; }
        if (stop || observe(child)) {
            failed=1;
            kill(child,SIGKILL);
            do done=waitpid(child,&status,0); while (done<0 && errno==EINTR);
            break;
        }
        struct timespec delay={0,100000000};
        nanosleep(&delay,NULL);
    }
    alarm(0);
    int rc=WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
    struct rusage usage;
    if (getrusage(RUSAGE_CHILDREN,&usage)) return 2;
    printf("SLEEP_RESULT method=%s iterations=%lu child=%d rc=%d observer_failed=%d "
        "minor_faults=%ld major_faults=%ld voluntary=%ld involuntary=%ld\n",
        argv[1],count,child,rc,failed,usage.ru_minflt,usage.ru_majflt,
        usage.ru_nvcsw,usage.ru_nivcsw);
    return failed?2:rc;
}
