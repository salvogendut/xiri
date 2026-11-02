/* SPDX-License-Identifier: GPL-2.0-only
 * NetBSD polling fallback for FAMExecuting/FAMExited. Include in one TU.
 * A snapshot describes executable files, not process names or argv strings.
 */
#ifndef XIRI_FAM_EXEC_STATE_H
#define XIRI_FAM_EXEC_STATE_H
#include <sys/types.h>
#include <sys/stat.h>
#include <cstdlib>
#ifdef __NetBSD__
#include <sys/param.h>
#include <sys/sysctl.h>
#include <cerrno>
#include <set>
#include <utility>
#include <vector>
#include "emul-path.h"

class XiriExecState {
    typedef std::pair<dev_t, ino_t> Identity;
    std::set<Identity> executing;
    bool valid;
public:
    XiriExecState() : valid(false) {}
    static bool enabled() {
        const char *value = std::getenv("XIRI_FAM_EXEC");
        return value && value[0] == '1' && value[1] == '\0';
    }
    bool ready() const { return valid; }
    bool contains(const struct stat &st) const {
        return S_ISREG(st.st_mode) &&
            executing.count(Identity(st.st_dev, st.st_ino)) != 0;
    }
    bool refresh() {
        int mib[6] = { CTL_KERN, KERN_PROC2, KERN_PROC_ALL, 0,
            sizeof(struct kinfo_proc2), 0 };
        std::vector<struct kinfo_proc2> processes;
        size_t size = 0;
        bool complete = false;
        for (int attempt = 0; attempt < 4; ++attempt) {
            mib[5] = 0;
            size = 0;
            if (sysctl(mib, 6, NULL, &size, NULL, 0) == -1) return false;
            processes.resize(size / sizeof(processes[0]) + 32);
            mib[5] = processes.size();
            size = processes.size() * sizeof(processes[0]);
            if (sysctl(mib, 6, &processes[0], &size, NULL, 0) == 0) {
                complete = true;
                break;
            }
            if (errno != ENOMEM) return false;
        }
        if (!complete || size % sizeof(processes[0])) return false;
        processes.resize(size / sizeof(processes[0]));
        std::set<Identity> next;
        for (size_t i = 0; i < processes.size(); ++i) {
            if (processes[i].p_pid <= 0) continue;
            int path_mib[4] = { CTL_KERN, KERN_PROC_ARGS,
                processes[i].p_pid, KERN_PROC_PATHNAME };
            char path[MAXPATHLEN];
            size_t len = sizeof(path);
            if (sysctl(path_mib, 4, path, &len, NULL, 0) == -1) {
                if (errno == ESRCH || errno == ENOENT) continue;
                return false;
            }
            if (!len || len > sizeof(path) || path[len-1] != '\0')
                return false;
            struct stat st;
            if (stat(path, &st) == -1) {
                if (errno != ENOENT && errno != ENOTDIR) return false;
                // Foreign exec through a catalog link can retain a logical
                // IRIX pathname. Prefer a valid native path before fallback,
                // so native /bin/sh is never mistaken for IRIX /bin/sh.
                const std::string physical = xiri_fam_path(
                    std::getenv("XIRI_FAM_ROOT"), path, true);
                if (stat(physical.c_str(), &st) == -1) {
                    if (errno == ENOENT || errno == ENOTDIR) continue;
                    return false;
                }
            }
            if (S_ISREG(st.st_mode)) next.insert(Identity(st.st_dev, st.st_ino));
        }
        executing.swap(next);
        valid = true;
        return true;
    }
};
#else
class XiriExecState {
public:
    static bool enabled() { return false; }
    bool ready() const { return false; }
    bool contains(const struct stat &) const { return false; }
    bool refresh() { return false; }
};
#endif
#endif
