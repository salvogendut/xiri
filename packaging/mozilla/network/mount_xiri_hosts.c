/* Publish the IRIX hosts.byname map through the native NetBSD NFSv2 client. */
#include <sys/types.h>
#include <sys/mount.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#define NFS_ARGS_ONLY
#include <nfs/nfsmount.h>
#include <rpcsvc/nfs_prot.h>
#include <err.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <netdb.h>
#include <pwd.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* Handles identify snapshots. An evicted handle returns STALE. */
#define SLOTS 512
#define CACHE_SECONDS 30
struct record {
	uint32_t id;
	time_t created;
	char name[254];
	char line[INET_ADDRSTRLEN + 1 + 253 + 2];
};
static struct record records[SLOTS];
static struct record root = { .id = 1 };
static uint32_t last_id = 1;

static struct record *
from_handle(const nfs_fh *fh)
{
	uint32_t id;
	memcpy(&id, fh->data, sizeof(id));
	if (id == root.id)
		return &root;
	struct record *r = &records[id % SLOTS];
	return id != 0 && r->id == id ? r : NULL;
}

static fattr
attributes(const struct record *r)
{
	fattr a = { .type = r == &root ? NFDIR : NFREG,
	    .mode = r == &root ? S_IFDIR | 0555 : S_IFREG | 0444,
	    .nlink = r == &root ? 2 : 1, .blocksize = 512, .fsid = 1,
	    .fileid = r->id, .size = strlen(r->line), .blocks = 1 };
	/* The NFS client validates both positive and negative names against
	 * directory mtime. Let it recheck them on the next cache interval. */
	time_t timestamp = r->created;
	if (r == &root) {
		time_t now = time(NULL);
		timestamp = now - now % CACHE_SECONDS;
	}
	a.atime.seconds = a.mtime.seconds = a.ctime.seconds = timestamp;
	return a;
}

static nfsstat
lookup(const diropargs *args, diropokres *out)
{
	char ip[INET_ADDRSTRLEN];
	const char *name = args->name;
	struct record *r = from_handle(&args->dir);
	struct addrinfo hints = { .ai_family = AF_INET, .ai_socktype = SOCK_STREAM };
	struct addrinfo *result;

	if (r == NULL)
		return NFSERR_STALE;
	if (r != &root)
		return NFSERR_NOTDIR;
	if (!strcmp(name, ".") || !strcmp(name, ".."))
		goto found;
	size_t length = strlen(name);
	if (!length || length >= sizeof(r->name) || name[0] == '.' ||
	    strspn(name, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._") != length)
		return NFSERR_NOENT;
	time_t now = time(NULL);
	for (size_t i = 0; i < SLOTS; i++) {
		r = &records[i];
		if (r->id && now >= r->created && now - r->created < CACHE_SECONDS &&
		    strcmp(r->name, name) == 0)
			goto found;
	}
	int error = getaddrinfo(name, NULL, &hints, &result);
	if (error)
		return error == EAI_NONAME || error == EAI_NODATA ? NFSERR_NOENT : NFSERR_IO;
	const struct sockaddr_in *sin = (const void *)result->ai_addr;
	const char *address = inet_ntop(AF_INET, &sin->sin_addr, ip, sizeof(ip));
	freeaddrinfo(result);
	if (address == NULL)
		return NFSERR_IO;
	if (++last_id < 2)
		last_id = 2;
	r = &records[last_id % SLOTS];
	r->id = last_id;
	r->created = now;
	strlcpy(r->name, name, sizeof(r->name));
	snprintf(r->line, sizeof(r->line), "%s\t%s\n", ip, name);
found:
	memcpy(out->file.data, &r->id, sizeof(r->id));
	out->attributes = attributes(r);
	return NFS_OK;
}

static bool_t
xdr_empty(XDR *stream, const void *data)
{
	(void)stream;
	(void)data;
	return TRUE;
}

static void
serve(struct svc_req *req, SVCXPRT *transport)
{
	union { nfs_fh fh; diropargs lookup; readargs read; readdirargs dir; } args = {0};
	union { attrstat attr; diropres lookup; readres read; readdirres dir; statfsres fs; } res = {0};
	xdrproc_t decode, encode;
	struct record *r;
#define XDR(type) ((xdrproc_t)xdr_ ## type)
	const struct sockaddr_in *caller = svc_getrpccaller(transport)->buf;
	if (caller->sin_family != AF_INET || caller->sin_addr.s_addr != htonl(INADDR_LOOPBACK) ||
	    ntohs(caller->sin_port) >= IPPORT_RESERVED) {
		svcerr_weakauth(transport);
		return;
	}
	switch (req->rq_proc) {
	case NFSPROC_NULL:    decode = xdr_empty;     encode = xdr_empty; break;
	case NFSPROC_GETATTR: decode = XDR(nfs_fh);   encode = XDR(attrstat); break;
	case NFSPROC_LOOKUP:  decode = XDR(diropargs);encode = XDR(diropres); break;
	case NFSPROC_READ:    decode = XDR(readargs); encode = XDR(readres); break;
	case NFSPROC_READDIR: decode = XDR(readdirargs); encode = XDR(readdirres); break;
	case NFSPROC_STATFS:  decode = XDR(nfs_fh);   encode = XDR(statfsres); break;
	default:
		svcerr_noproc(transport);
		return;
	}
	if (!svc_getargs(transport, decode, (void *)&args)) {
		svcerr_decode(transport);
		goto done;
	}
	switch (req->rq_proc) {
	case NFSPROC_GETATTR:
		r = from_handle(&args.fh);
		if (r)
			res.attr.attrstat_u.attributes = attributes(r);
		else
			res.attr.status = NFSERR_STALE;
		break;
	case NFSPROC_LOOKUP:
		res.lookup.status = lookup(&args.lookup, &res.lookup.diropres_u.diropres);
		break;
	case NFSPROC_READ:
		r = from_handle(&args.read.file);
		if (!r)
			res.read.status = NFSERR_STALE;
		else if (r == &root)
			res.read.status = NFSERR_ISDIR;
		else {
			readokres *reply = &res.read.readres_u.reply;
			reply->attributes = attributes(r);
			size_t size = strlen(r->line);
			size_t offset = MIN(size, args.read.offset);
			reply->data.data_val = r->line + offset;
			reply->data.data_len = MIN(size - offset, args.read.count);
		}
		break;
	case NFSPROC_READDIR:
		r = from_handle(&args.dir.dir);
		if (r == &root)
			res.dir.readdirres_u.reply.eof = TRUE;
		else
			res.dir.status = r ? NFSERR_NOTDIR : NFSERR_STALE;
		break;
	case NFSPROC_STATFS:
		res.fs.statfsres_u.reply.bsize = 512;
		res.fs.statfsres_u.reply.tsize = 512;
		break;
	}
	if (!svc_sendreply(transport, encode, (void *)&res))
		svcerr_systemerr(transport);
done:
	svc_freeargs(transport, decode, (void *)&args);
}

int
main(int argc, char **argv)
{
	if (argc != 2)
		errx(1, "usage: %s mountpoint", getprogname());
	struct passwd *pw = getpwnam("nobody");
	if (pw == NULL || !pw->pw_uid || !pw->pw_gid)
		errx(1, "missing unprivileged nobody account");
	uid_t uid = pw->pw_uid;
	gid_t gid = pw->pw_gid;
	struct sockaddr_in addr = { .sin_len = sizeof(addr), .sin_family = AF_INET,
	    .sin_addr.s_addr = htonl(INADDR_LOOPBACK) };
	socklen_t len = sizeof(addr);
	int fd = socket(AF_INET, SOCK_DGRAM, 0);
	if (fd == -1 || bind(fd, (void *)&addr, sizeof(addr)) || getsockname(fd, (void *)&addr, &len))
		err(1, "bind loopback");
	SVCXPRT *transport = svc_dg_create(fd, 0, 0);
	if (!transport || !svc_reg(transport, NFS_PROGRAM, NFS_VERSION, serve, NULL))
		errx(1, "initialize private NFS transport");
	root.created = time(NULL);
	pid_t child = fork();
	if (child == -1)
		err(1, "fork");
	if (child == 0) {
		if (setsid() == -1 || chdir("/") || setgroups(1, &gid) || setgid(gid) || setuid(uid))
			err(1, "start resolver");
		int nullfd = open("/dev/null", O_RDWR);
		if (nullfd == -1)
			err(1, "open /dev/null");
		for (int i = 0; i < 3; i++)
			if (dup2(nullfd, i) == -1)
				_exit(1);
		if (nullfd > 2)
			close(nullfd);
		svc_run();
		_exit(1);
	}
	close(fd);
	nfs_fh root_fh = {0};
	memcpy(root_fh.data, &root.id, sizeof(root.id));
	struct nfs_args args = { .version = NFS_ARGSVERSION, .addr = (void *)&addr,
	    .addrlen = sizeof(addr), .sotype = SOCK_DGRAM, .proto = IPPROTO_UDP,
	    .fh = (void *)&root_fh, .fhsize = sizeof(root_fh), .hostname = "xiri-hosts",
	    .flags = NFSMNT_SOFT | NFSMNT_RESVPORT | NFSMNT_NOAC | NFSMNT_TIMEO |
	    NFSMNT_RETRANS, .timeo = 10, .retrans = 4 };
	if (mount(MOUNT_NFS, argv[1], MNT_RDONLY | MNT_NOSUID | MNT_NODEV | MNT_NOEXEC,
	    &args, sizeof(args)) == -1) {
		int error = errno;
		kill(child, SIGTERM);
		waitpid(child, NULL, 0);
		errno = error;
		err(1, "mount %s", argv[1]);
	}
	printf("%ld\n", (long)child);
	return 0;
}
