/* Native adversarial lifecycle fixtures; do not run outside the guest lab. */
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void hold(const char *file)
{
    signal(SIGTERM, SIG_IGN);
    FILE *f = fopen(file, "a");
    if (!f) _exit(3);
    fprintf(f, "%d\n", getpid()); fclose(f);
    for (;;) pause();
}
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    if (!strcmp(argv[1], "hold")) hold(argv[2]);
    if (!strcmp(argv[1], "live-burst")) {
        for (int i=0; i<24; ++i) {
            pid_t p=fork(); if (p<0) return 3;
            if (!p) hold(argv[2]);
        }
        hold(argv[2]);
    }
    if (!strcmp(argv[1], "burst")) {
        for (int i=0; i<24; ++i) {
            pid_t p=fork(); if (p<0) return 3;
            if (!p) { pid_t q=fork(); if (q<0) _exit(4); if (!q) _exit(0); _exit(0); }
        }
        while (wait(NULL)>0) {}
        return 0;
    }
    if (!strcmp(argv[1], "escape") || !strcmp(argv[1], "fail")) {
        int gate[2]; if (pipe(gate)) return 3;
        pid_t p=fork(); if (p<0) return 3;
        if (!p) {
            close(gate[0]);
            if (setsid()<0) _exit(4);
            pid_t q=fork(); if (q<0) _exit(5);
            if (q) _exit(0);
            signal(SIGTERM,SIG_IGN);
            FILE *f=fopen(argv[2],"a"); if(!f) _exit(6);
            fprintf(f,"%d\n",getpid()); fclose(f);
            if (write(gate[1],"x",1)!=1) _exit(7);
            close(gate[1]); for (;;) pause();
        }
        close(gate[1]); char c;
        if (read(gate[0],&c,1)!=1) return 8;
        close(gate[0]); waitpid(p,NULL,0);
        if (!strcmp(argv[1],"fail")) return 7;
        hold(argv[2]);
    }
    return 2;
}
