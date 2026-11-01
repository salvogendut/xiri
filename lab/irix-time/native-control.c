/* Native time/select remain coherent before and after foreign probes. */
#include <sys/types.h>
#include <sys/time.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
int main(void)
{
    struct timeval a,b,delay={0,100000};
    time_t before=time(NULL), stored=0, now=time(&stored);
    if(before==(time_t)-1 || now<before || now!=stored)return 1;
    if(gettimeofday(&a,NULL) || a.tv_sec<now || a.tv_usec<0 || a.tv_usec>=1000000)return 2;
    if(select(0,NULL,NULL,NULL,&delay))return 3;
    if(gettimeofday(&b,NULL) || b.tv_usec<0 || b.tv_usec>=1000000)return 4;
    long long elapsed=(long long)(b.tv_sec-a.tv_sec)*1000000+b.tv_usec-a.tv_usec;
    if(elapsed<90000 || elapsed>5000000 || time(NULL)<b.tv_sec)return 5;
    printf("NATIVE_TIME uid=%lu seconds=1 microseconds=1 progression=1 select=1\n",(unsigned long)getuid());
    return 0;
}
