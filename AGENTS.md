# Fork workflow

Use `xiri` as the integration branch for both the IRIS and NetBSD forks.
IRIS is checked out at `../iris`; the NetBSD checkout is `../NetBSD-xiri`
and its origin is `salvogendut/NetBSD-xiri`. The older `../NetBSD-nixbench`
path remains a compatibility symlink.

Make routine changes on `xiri`. When needed, create a temporary topic branch,
merge it into that project's `xiri` branch at the end of the work cycle, and
remove the completed topic branch after the merge is pushed. Use names such
as `topic/<name>`; Git cannot keep `xiri` and `xiri/<name>` branches together.

Check IRIS `upstream/main` at the start of each development cycle and once per
active day during longer cycles. Fetch from `https://github.com/techomancer/iris.git`,
review new commits, and integrate them into the IRIS `xiri` branch. Use a
temporary topic branch when needed, preserve our fork changes when resolving
conflicts, and run the affected build/regression checks before pushing.
Record the checked upstream revision, integration result and validation in
the project documentation. These checks happen during active work, not through
an unattended background job.

Keep existing detached lab worktrees at their pinned commits for reproduction.
Do new development in the fork checkout or a topic worktree, and preserve
qualified artifacts until the replacement has been tested. See
[fork development](docs/FORKS.md) for the layout and reproduction instructions.

# Creating a Xiri system

Install the native XiriBSD ISO, boot the installed system, then run `xiriprep` there as
root with the owner's IRIX donor image and the target login. Use this path
for new installation work and end-to-end qualification. Existing prepared
CHDs and full desktop CDs are references for regression testing and recovery.
[Installation workflow and current coverage](docs/XIRI-INSTALLATION.md)

When IRIX behavior is uncertain, run the same application or probe on a
disposable copy of the matching original IRIX installation. Record the
observable result alongside the XiriBSD result.

Build the project's two reference IRIX installations from original media.
Also exercise `xiriprep` with an independently supplied installed IRIX disk.
Record the provenance, detected release and first desktop login separately
from the original-media tests.

# Release lines

Name every new XiriBSD installer ISO `xiribsd-OO.RR.rr-vv-YYYY-MM-DD.iso`.
Use the numeric NetBSD major, minor and patch release from the build sources,
the two-digit XiriBSD installer revision, and the build date. Use the
[workstation builder](docs/XIRI-INSTALLATION.md#build-the-native-indy-iso) to generate the name.

Always maintain both IRIX 6.5.22 and IRIX 6.5.30 versions. Keep their donor
images, import profiles, qualification records and test CHDs separate. Shared
native components require validation with both vendor releases. Never replace
the last qualified artifact for either release with an untested candidate.
