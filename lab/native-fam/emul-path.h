/* Xiri's optional pathname view for the native FAM service. GPL-2.0. */
#ifndef XIRI_FAM_EMUL_PATH_H
#define XIRI_FAM_EMUL_PATH_H
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>
#include <string>

/* Resolve intermediate symlinks inside the foreign root. File watches keep
 * the final symlink itself; directory watches follow it. Event names remain
 * in the client's namespace and are handled separately by ClientInterest. */
static std::string
xiri_fam_path(const char *root_arg, const char *path_arg, bool directory)
{
    const std::string path(path_arg);
    if (!root_arg || root_arg[0] != '/' || path.empty() || path[0] != '/')
        return path;
    std::string root(root_arg);
    while (root.size() > 1 && root[root.size()-1] == '/')
        root.erase(root.size()-1);
    if (root == "/" || path == root || path.compare(0, root.size()+1, root+"/") == 0)
        return path;

    std::string pending(path), resolved;
    unsigned links = 0;
    int failure = 0;
    while (!pending.empty()) {
        const std::string::size_type begin = pending.find_first_not_of('/');
        if (begin == std::string::npos) break;
        pending.erase(0, begin);
        const std::string::size_type slash = pending.find('/');
        const std::string part = pending.substr(0, slash);
        pending = slash == std::string::npos ? "" : pending.substr(slash);
        if (part == ".") continue;
        if (part == "..") {
            const std::string::size_type last = resolved.rfind('/');
            resolved = last == std::string::npos ? "" : resolved.substr(0, last);
            continue;
        }
        const std::string candidate = root + resolved + "/" + part;
        struct stat st;
        if (lstat(candidate.c_str(), &st) != 0) {
            failure = errno;
            resolved += "/" + part + pending;
            break;
        }
        if (S_ISLNK(st.st_mode) && (directory || !pending.empty())) {
            char target[PATH_MAX+1];
            const ssize_t length = readlink(candidate.c_str(), target, PATH_MAX);
            if (length < 0 || length == PATH_MAX || ++links > 32) {
                failure = length < 0 ? errno : ELOOP;
                resolved += "/" + part + pending;
                break;
            }
            target[length] = '\0';
            if (target[0] == '/') resolved.clear();
            pending = std::string(target) + pending;
        } else {
            resolved += "/" + part;
        }
    }
    const std::string candidate = root + (resolved.empty() ? "/" : resolved);
    if (!failure || (failure != ENOENT && failure != ENOTDIR))
        return candidate;
    struct stat native;
    if (lstat(path.c_str(), &native) == 0)
        return path;
    /* Keep a missing imported entry attached to its existing parent, so a
     * later creation is observed. Native-only home directories fall back. */
    const std::string parent = candidate.substr(0, candidate.rfind('/'));
    if (stat(parent.c_str(), &native) == 0 && S_ISDIR(native.st_mode))
        return candidate;
    return path;
}
#endif
