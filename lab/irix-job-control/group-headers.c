/* Print the installed public process-group and job-control ABI constants. */
#include <sys/types.h>
#include <sys/syssgi.h>
#include <unistd.h>
#include <stdio.h>
#define SHOW(x) printf(#x "=%ld\n",(long)(x))
int main(void)
{
    SHOW(_SC_JOB_CONTROL); SHOW(_SC_SAVED_IDS); SHOW(_SC_VERSION);
    SHOW(SGI_SYSCONF); SHOW(SGI_SETSID); SHOW(SGI_GETSID);
#ifdef SGI_SETPGID
    SHOW(SGI_SETPGID);
#endif
#ifdef SGI_GETPGID
    SHOW(SGI_GETPGID);
#endif
#ifdef SGI_BSDGETPGRP
    SHOW(SGI_BSDGETPGRP);
#endif
#ifdef SGI_BSDSETPGRP
    SHOW(SGI_BSDSETPGRP);
#endif
    printf("JOB_CONTROL=%ld SAVED_IDS=%ld VERSION=%ld\n",sysconf(_SC_JOB_CONTROL),sysconf(_SC_SAVED_IDS),sysconf(_SC_VERSION));
    return 0;
}
