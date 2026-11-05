/* Print public ABI sizes and constants from the installed reference headers. */
#include <sys/types.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <sys/procset.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <time.h>

#define VALUE(x) printf(#x "=%ld\n", (long)(x))
int main(void)
{
    VALUE(_MIPS_SIM);
    VALUE(sizeof(struct timespec));
    VALUE(sizeof(((struct timespec *)0)->tv_sec));
    VALUE(sizeof(((struct timespec *)0)->tv_nsec));
    VALUE(offsetof(struct timespec, tv_nsec));
    VALUE(sizeof(siginfo_t));
    VALUE(P_PID); VALUE(P_PGID); VALUE(P_ALL);
    VALUE(WEXITED); VALUE(WSTOPPED); VALUE(WTRAPPED);
    VALUE(WCONTINUED); VALUE(WNOHANG); VALUE(WNOWAIT);
    VALUE(SA_NOCLDSTOP); VALUE(SA_NOCLDWAIT); VALUE(SA_SIGINFO);
    VALUE(CLD_EXITED); VALUE(CLD_KILLED); VALUE(CLD_DUMPED);
    VALUE(CLD_TRAPPED); VALUE(CLD_STOPPED); VALUE(CLD_CONTINUED);
    VALUE(SIGCHLD); VALUE(SIGSTOP); VALUE(SIGCONT);
    VALUE(SIGTSTP); VALUE(SIGTTIN); VALUE(SIGTTOU);
    return 0;
}
