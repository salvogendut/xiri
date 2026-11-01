/* Native signal/return and child-wait control beside foreign fixtures. */
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t called, masked;
static void handler(int signo)
{
    sigset_t mask;
    called += signo == SIGUSR1;
    if (sigprocmask(SIG_SETMASK, NULL, &mask) == 0)
        masked = sigismember(&mask, SIGUSR1) && sigismember(&mask, SIGTERM);
    sigaddset(&mask, SIGUSR2);
    (void)sigprocmask(SIG_SETMASK, &mask, NULL);
}

int main(void)
{
    struct sigaction sa;
    sigset_t mask;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = handler;
    sigemptyset(&sa.sa_mask);
    sigemptyset(&mask);
    sigaddset(&mask, SIGTERM);
    if (sigprocmask(SIG_SETMASK, &mask, NULL) ||
        sigaction(SIGUSR1, &sa, NULL) || raise(SIGUSR1)) return 1;
    if (sigprocmask(SIG_SETMASK, NULL, &mask) || called != 1 || !masked ||
        !sigismember(&mask, SIGTERM) || sigismember(&mask, SIGUSR1) ||
        sigismember(&mask, SIGUSR2)) return 2;
    pid_t pid = fork();
    if (pid < 0) return 3;
    if (pid == 0) _exit(37);
    int status;
    if (waitpid(pid, &status, 0) != pid || !WIFEXITED(status) ||
        WEXITSTATUS(status) != 37) return 4;
    puts("NATIVE_SIGNALS handler=1 mask=1 return=1 child=1");
    return 0;
}
