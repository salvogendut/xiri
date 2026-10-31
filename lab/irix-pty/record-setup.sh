#!/bin/sh
# Only in the disposable record fixture directory; reset before each case.
set -eu
umask 022
printf XIRI_OWNED >owned
printf XIRI_ROOT >root
chown 1234 owned
chgrp 1234 owned
chown 0 root
chgrp 0 root
chmod 0644 owned root
