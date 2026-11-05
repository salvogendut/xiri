/* Original libc calls used to distinguish missing IDs from range errors. */
#include <sys/types.h>
#include <sys/syssgi.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
int main(void)
{
    const int values[]={-1,(-2147483647-1),1,9999,29999,30000,30001,32767,32768,65535,100000,2147483647};
    unsigned i;
    for(i=0;i<sizeof(values)/sizeof(values[0]);i++) {
        long rc;int error;
        errno=0;rc=getpgid(values[i]);error=errno;
        printf("GET pid=%d rc=%ld errno=%d\n",values[i],rc,error);
        errno=0;rc=syssgi(SGI_SETPGID,2147483647,values[i]);error=errno;
        printf("SET missing-pid pgid=%d rc=%ld errno=%d\n",values[i],rc,error);
    }
    return 0;
}
