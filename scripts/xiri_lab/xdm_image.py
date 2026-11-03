"""Shared inventories for xdm image preparation and cold-boot checks."""
import json

from . import sha256


def support_files(bundle, seed):
    files = {f['netbsd_destination']: f['sha256'] for f in
             json.loads((bundle/'copy-ledger.json').read_text())['files']
             if f['type'] == 'file'}
    files.update(seed['staged'])
    if seed.get('desktop_services'):
        assert sha256(bundle/'bitmap-copy-ledger.json') == seed['bitmap_ledger_sha256']
        files.update({f['netbsd_destination']: f['sha256'] for f in
                      json.loads((bundle/'bitmap-copy-ledger.json').read_text())['files']
                      if f['type'] == 'file'})
    files.update(seed['installed_files'])
    # Native rc.d regenerates the kernel-version prefix at each boot. The
    # preparation record retains its initial hash, not an immutable contract.
    files.pop('/etc/motd', None)
    return files


def runtime_files():
    paths = ['/usr/local/bin/'+s for s in ('xiri-desktop','xiri-session','xiri-launch','xiri-logout')]
    paths += ['/usr/local/libexec/xiri/'+s for s in ('session-guard','x11-check','desktop-clients.sh','setup-pty.sh')]
    paths += ['/usr/libexec/xiri-shell','/etc/xiri/session.conf','/etc/xiri/fam.conf',
              '/etc/xiri/xdm/Xservers','/etc/xiri/xdm/Xresources',
              '/usr/local/share/xiri/xdm.xsession','/usr/people/xiritest/.xsession',
              '/etc/ttys','/etc/motd']
    paths += ['/etc/rc.d/'+s for s in ('xiri_devices','xiri_famd')]
    paths += ['/etc/rc.conf.d/'+s for s in ('xiri_devices','xiri_famd','rpcbind','xdm')]
    return paths
