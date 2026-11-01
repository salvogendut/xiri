# Fork workflow

Use `xiri` as the integration branch for both the IRIS and NetBSD forks.
IRIS is checked out at `../iris`; the NetBSD checkout is `../NetBSD-nixbench`
and its origin is `salvogendut/NetBSD-xiri`.

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
