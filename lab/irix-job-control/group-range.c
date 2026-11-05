#include <sys/types.h>
#include <sys/syssgi.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
int main(void) {
 unsigned lo=100000, hi=2147483647, mid;long rc;int e;
 while(hi-lo>1){mid=lo+(hi-lo)/2;errno=0;rc=getpgid(mid);e=errno;if(rc==-1&&e==22)hi=mid;else lo=mid;}
 printf("GET boundary: valid=%u invalid=%u\n",lo,hi);
 for(mid=lo-1;mid<=hi+1;mid++){errno=0;rc=getpgid(mid);printf("GET %u rc=%ld errno=%d\n",mid,rc,errno);errno=0;rc=syssgi(SGI_SETPGID,2147483647,mid);printf("SET %u rc=%ld errno=%d\n",mid,rc,errno);}
 return 0;
}
