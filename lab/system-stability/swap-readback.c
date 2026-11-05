/* Native NetBSD disposable-lab control: prove anonymous swap-in with mincore. */
#include <sys/mman.h>
#include <sys/resource.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define MIB ((size_t)1024 * 1024)
#define PRIMARY (96 * MIB)
#define CHUNK (8 * MIB)
#define MAX_CHUNKS 20

static void expired(int sig)
{
    static const char message[] = "SWAP_READBACK_TIMEOUT\n";
    (void)sig;
    (void)write(STDERR_FILENO,message,sizeof(message)-1);
    _exit(124);
}
static long long monotonic_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) { perror("clock"); exit(2); }
    return (long long)t.tv_sec*1000+t.tv_nsec/1000000;
}
static unsigned char pattern(size_t offset)
{
    return (unsigned char)(1 + (offset / 4096) % 255);
}
static void fill(volatile unsigned char *p, size_t bytes)
{
    for (size_t i=0; i<bytes; i+=4096) p[i]=pattern(i);
}
static int verify(volatile unsigned char *p, size_t bytes)
{
    for (size_t i=0; i<bytes; i+=4096) {
        unsigned char value=p[i];
        if (value!=pattern(i)) {
            fprintf(stderr,"SWAP_DATA_MISMATCH offset=%zu expected=%u actual=%u\n",
                i,pattern(i),value);
            return 1;
        }
    }
    return 0;
}
int main(void)
{
    setvbuf(stdout,NULL,_IOLBF,0);
    signal(SIGALRM,expired);
    alarm(900);
    long long began=monotonic_ms();
    long page=sysconf(_SC_PAGESIZE);
    if (page<=0 || PRIMARY%(size_t)page) return 2;
    size_t pages=PRIMARY/(size_t)page, absent=0, chunks=0;
    char *residency=malloc(pages);
    unsigned char *primary=mmap(NULL,PRIMARY,PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANON,-1,0);
    unsigned char *pressure[MAX_CHUNKS]={0};
    if (!residency || primary==MAP_FAILED) { perror("allocate"); return 2; }
    fill(primary,PRIMARY);
    /* NetBSD preserves data for DONTNEED; FREE would invalidate this test. */
    if (madvise(primary,PRIMARY,MADV_DONTNEED)) { perror("madvise"); return 2; }
    for (;;) {
        if (mincore(primary,PRIMARY,residency)) { perror("mincore"); return 2; }
        absent=0;
        for (size_t i=0;i<pages;++i) if (!(residency[i]&1)) ++absent;
        printf("SWAP_RESIDENCY primary_bytes=%zu extra_bytes=%zu pages=%zu absent=%zu elapsed_ms=%lld\n",
            PRIMARY,chunks*CHUNK,pages,absent,monotonic_ms()-began);
        if (absent>=128) break;
        if (chunks==MAX_CHUNKS) {
            fprintf(stderr,"SWAP_PAGEOUT_UNPROVEN\n"); return 3;
        }
        pressure[chunks]=mmap(NULL,CHUNK,PROT_READ|PROT_WRITE,
            MAP_PRIVATE|MAP_ANON,-1,0);
        if (pressure[chunks]==MAP_FAILED) { perror("pressure mmap"); return 2; }
        fill(pressure[chunks],CHUNK);
        ++chunks;
    }
    /* The extra mappings force eviction; release them before readback so
     * verification does not thrash between two competing working sets. */
    for (size_t i=0;i<chunks;++i) if (munmap(pressure[i],CHUNK)) return 2;
    if (mincore(primary,PRIMARY,residency)) { perror("mincore after release"); return 2; }
    absent=0;
    for (size_t i=0;i<pages;++i) if (!(residency[i]&1)) ++absent;
    printf("SWAP_PRESSURE_RELEASED absent=%zu elapsed_ms=%lld\n",absent,monotonic_ms()-began);
    if (absent<128) { fprintf(stderr,"SWAP_PAGEOUT_UNPROVEN\n"); return 3; }
    struct rusage before,after;
    if (getrusage(RUSAGE_SELF,&before)) return 2;
    if (verify(primary,PRIMARY)) return 4;
    if (getrusage(RUSAGE_SELF,&after)) return 2;
    int faults=after.ru_majflt>before.ru_majflt;
    printf("SWAP_READBACK primary_bytes=%zu extra_bytes=%zu absent_before=%zu "
        "major_before=%ld major_after=%ld written_bytes=%zu elapsed_ms=%lld valid=%d\n",
        PRIMARY,chunks*CHUNK,absent,before.ru_majflt,after.ru_majflt,
        PRIMARY/4096,monotonic_ms()-began,faults);
    if (munmap(primary,PRIMARY)) return 2;
    free(residency);
    return faults?0:5;
}
