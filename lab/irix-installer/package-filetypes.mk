# The Freeware CD 4 exit command invokes SGI make -u here inside its chroot.
# Compile from install/ so the package's relative icon includes resolve.
all:
	cd install && /usr/sbin/fftr -o /var/inst/xiri-xmahjongg/lock/game.otr xmahjongg.ftr
