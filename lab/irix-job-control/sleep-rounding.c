/* Original libc timing control at the 100 Hz conversion boundary. */
#include <sys/time.h>
#include <stdio.h>
#include <time.h>
int main(void)
{
    static const long values[]={0,1,1000000,5000000,9999999,10000000,
        10000001,15000000,19999999,20000000,25000000};
    for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++) {
        for(unsigned repeat=0;repeat<4;repeat++) {
            struct timespec request={0,0};struct timeval before,after;
            request.tv_nsec=values[i];
            if(gettimeofday(&before,0)||nanosleep(&request,0)||gettimeofday(&after,0))return 1;
            printf("ROUND ns=%ld elapsed_us=%ld\n",values[i],
                (long)(after.tv_sec-before.tv_sec)*1000000+after.tv_usec-before.tv_usec);
        }
    }
    return 0;
}
