/* Identify the client half of a local FAM v1 TCP connection on NetBSD.
 * The request's UID/GID fields are deliberately not involved. */
#ifndef XIRI_NATIVE_PEER_H
#define XIRI_NATIVE_PEER_H
#include <sys/types.h>
#include <sys/param.h>
#include <sys/queue.h>
#include <sys/socket.h>
#include <sys/sysctl.h>
#include <netinet/in.h>
#include <netinet/ip_var.h>
#include <netinet/tcp.h>
#include <netinet/tcp_timer.h>
#include <netinet/tcp_var.h>
#include <errno.h>
#include <string.h>

static int xiri_native_peer_uid(int fd, uid_t *uid)
{
    struct sockaddr_storage ends[2];
    socklen_t len = sizeof(ends[0]);
    memset(ends, 0, sizeof(ends));
    /* TCPCTL_IDENT expects remote, local. Reverse the accepted socket's
     * endpoints to query the connecting socket, not famd's accepted socket. */
    if (getsockname(fd, (struct sockaddr *)&ends[0], &len) < 0)
        return -1;
    len = sizeof(ends[1]);
    if (getpeername(fd, (struct sockaddr *)&ends[1], &len) < 0)
        return -1;
    for (unsigned i = 0; i < 2; ++i) {
        const struct sockaddr_in *addr = (const struct sockaddr_in *)&ends[i];
        if (addr->sin_family != AF_INET || addr->sin_len != sizeof(*addr) ||
            addr->sin_addr.s_addr != htonl(INADDR_LOOPBACK)) {
            errno = EACCES;
            return -1;
        }
    }
    int mib[] = { CTL_NET, PF_INET, IPPROTO_TCP, TCPCTL_IDENT };
    size_t size = sizeof(*uid);
    if (sysctl(mib, 4, uid, &size, ends, sizeof(ends)) < 0)
        return -1;
    if (size != sizeof(*uid) || *uid == (uid_t)-1) {
        errno = EACCES;
        return -1;
    }
    return 0;
}
#endif
