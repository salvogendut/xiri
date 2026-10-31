/* Native readiness peer: handshake, delayed data/EOF, or an idle open stream. */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc, char **argv)
{
    int count = argc == 2 ? atoi(argv[1]) : 0;
    alarm(900);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = {.sin_len=sizeof(a), .sin_family=AF_INET,
        .sin_port=htons(6116), .sin_addr.s_addr=htonl(INADDR_LOOPBACK)};
    if (count <= 0 || fd < 0 || bind(fd,(struct sockaddr *)&a,sizeof(a)) || listen(fd,4)) return 2;
    puts("RDY"); fflush(stdout);
    for (int i=0; i<count; i++) {
        int client=accept(fd,NULL,NULL); uint32_t header[2]; char byte;
        if (client<0) return 2;
        for (size_t n=0; n<sizeof(header);) {
            ssize_t got=read(client,(char *)header+n,sizeof(header)-n);
            if (got<=0) return 2;
            n+=(size_t)got;
        }
        unsigned mode=ntohl(header[1]);
        if (mode>2 || write(client,"R",1)!=1 || read(client,&byte,1)!=1 || byte!='S') return 2;
        if (mode!=2) {
            usleep(300000);
            if ((mode==0 && write(client,"Q",1)!=1) || shutdown(client,SHUT_WR)) return 2;
        }
        ssize_t got=read(client,&byte,1);
        if ((got!=0 && !(got==-1 && errno==ECONNRESET)) || close(client)) return 2;
        if (fwrite(header,sizeof(header),1,stdout)!=1 || fflush(stdout)) return 2;
    }
    return close(fd)?2:0;
}
