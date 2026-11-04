#!/usr/bin/env python3
"""Stage original GNOME application data and VFS modules from read-only IRIX.

Only ignored local artifacts are written. This does not modify a test image
or copy a user's GNOME configuration; resource presence is not qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'.work/irix-gnome-resources'
BASES = ['/usr/freeware/share/gedit', '/usr/freeware/lib32/gedit',
         '/usr/freeware/lib32/vfs', '/usr/freeware/etc/vfs',
         '/usr/freeware/share/gnome-terminal']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(pid):
    def guest(*args):
        return subprocess.check_output(['guestfish', '--remote='+pid, *args], text=True, timeout=180).strip()
    records, archives = {}, {}
    local = WORK/'root'
    for base in BASES:
        archive = WORK/(base.strip('/').replace('/', '_')+'.tar')
        guest('tar-out', base, str(archive))
        archives[base] = dict(sha256=sha(archive), bytes=archive.stat().st_size)
        with tarfile.open(archive) as tar:
            for item in tar:
                relative = PurePosixPath(item.name)
                assert not relative.is_absolute() and '..' not in relative.parts
                path = posixpath.normpath(base+'/'+str(relative))
                assert path == base or path.startswith(base+'/')
                destination = '/emul/irix'+path
                record = dict(irix_source=path, netbsd_destination=destination,
                              original_mode=oct(item.mode), type='directory' if item.isdir()
                              else 'symlink' if item.issym() else 'file' if item.isfile() else 'unsupported')
                if item.isfile():
                    data = tar.extractfile(item).read()
                    target = local/path.lstrip('/');target.parent.mkdir(parents=True, exist_ok=True)
                    assert not target.is_symlink()
                    target.write_bytes(data)
                    record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                                  mode=oct(0o755 if item.mode & 0o111 else 0o644))
                elif item.issym():
                    record.update(target=item.linkname, mode='0o777')
                elif item.isdir():
                    record['mode']='0o755'
                else:
                    raise ValueError('unsupported archive member '+path)
                records[path]=record
        print('Collected',base,flush=True)
    # GNOME VFS loads its threading backend dynamically; DT_NEEDED alone
    # does not identify it. Gedit also reports a missing application icon.
    for path in ['/usr/freeware/lib32/libgnomevfs-pthread.so',
                 '/usr/freeware/share/pixmaps/gedit-icon.png']:
        target=local/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
        guest('download',path,str(target))
        mode=int(re.search(r'^st_mode: (\d+)$',guest('statns',path),re.M)[1])
        records[path]=dict(irix_source=path,netbsd_destination='/emul/irix'+path,type='file',
            canonical_source=guest('realpath',path),original_mode=oct(mode & 0o7777),
            mode='0o644',bytes=target.stat().st_size,sha256=sha(target))
    spec=importlib.util.spec_from_file_location('elf_inventory', ROOT/'scripts/inventory-irix-desktop.py')
    elf_inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(elf_inventory)
    existing=json.loads((ROOT/'.work/irix-installed-desktop/inventory.json').read_text())['files']
    gimp=json.loads((ROOT/'.work/irix-gimp-resources/manifest.json').read_text())
    existing={**existing, **gimp['paths']}
    dependencies=[];queue=list(records);analyzed=set();resolved={}
    while queue:
        path=queue.pop(0)
        if path in analyzed or records[path]['type']!='file':continue
        analyzed.add(path);source=local/path.lstrip('/')
        if source.read_bytes()[:4]!=b'\x7fELF':continue
        info=elf_inventory.elf(source)
        # SGI_ELFMAP currently checks execute permission even for libraries.
        # Match the qualified desktop import's documented ELF mode policy.
        records[path]['mode']='0o555'
        assert info['abi']=='n32',path
        dirs=[d for value in info['rpath'] for d in value.split(':') if d.startswith('/')]
        dirs += ['/usr/lib32','/usr/lib32/internal','/lib32','/usr/freeware/lib32']
        for name in info['needed']:
            assert '/' not in name
            key=(tuple(dirs),name)
            if key not in resolved:
                candidates=list(dict.fromkeys(d+'/'+name for d in dirs))
                selected=next((p for p in candidates if p in records or p in existing),None)
                if selected is None:
                    selected=next((p for p in candidates if guest('is-file',p,'followsymlinks:true')=='true'),None)
                assert selected is not None,(path,name)
                resolved[key]=selected
            selected=resolved[key]
            dependencies.append(dict(source=path,needed=name,selected=selected,in_existing_payload=selected in existing))
            if selected in existing or selected in records:continue
            assert len([v for v in records if not any(v==b or v.startswith(b+'/') for b in BASES)])<64
            target=local/selected.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
            guest('download',selected,str(target))
            mode=int(re.search(r'^st_mode: (\d+)$',guest('statns',selected),re.M)[1])
            records[selected]=dict(irix_source=selected,netbsd_destination='/emul/irix'+selected,type='file',
                canonical_source=guest('realpath',selected),original_mode=oct(mode & 0o7777),
                mode=oct(0o755 if mode & 0o111 else 0o644),bytes=target.stat().st_size,sha256=sha(target))
            queue.append(selected)
    payload=WORK/'payload.tgz'
    with tarfile.open(payload,'w:gz') as tar:
        for path, record in sorted(records.items(), key=lambda pair:(len(PurePosixPath(pair[0]).parts),pair[0])):
            assert all(records.get(str(parent),{}).get('type','directory')=='directory' for parent in PurePosixPath(path).parents)
            item=tarfile.TarInfo(record['netbsd_destination'].lstrip('/'))
            item.uid=item.gid=item.mtime=0;item.uname=item.gname='root';item.mode=int(record['mode'],8)
            if record['type']=='file':
                source=local/path.lstrip('/');assert sha(source)==record['sha256']
                item.size=record['bytes']
                with source.open('rb') as stream:tar.addfile(item,stream)
            elif record['type']=='directory':
                item.type=tarfile.DIRTYPE;tar.addfile(item)
            else:
                item.type=tarfile.SYMTYPE;item.linkname=record['target'];tar.addfile(item)
    manifest=dict(schema=1,status='staged-unqualified',source_image_manifest_sha256=sha(ROOT/'lab/irix-reference/manifest.json'),
        extraction='guestfish --ro, mount ro,norecovery; no host symlinks created',
        script_sha256=sha(Path(__file__)),gimp_manifest_sha256=sha(ROOT/'.work/irix-gimp-resources/manifest.json'),bases=BASES,archives=archives,payload_sha256=sha(payload),
        paths=records,dependencies=dependencies,elf_parser_sha256=sha(ROOT/'scripts/inventory-irix-desktop.py'),limitations=['Original application resources only; user settings and package database are excluded.',
          'Plugin execution and additional dynamic dependencies require separate qualification.'])
    (WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(len(records),'paths;',payload.stat().st_size,'payload bytes',flush=True)


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=WORK)
    args = parser.parse_args()
    WORK = args.output_directory.resolve()
    WORK.mkdir(exist_ok=True)
    reference=ROOT/'.work/irix-reference'
    raw=reference/'media/irix65.raw'
    assert raw.stat().st_size==json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())['logical_disk_bytes']
    env=dict(os.environ,LIBGUESTFS_BACKEND='direct',LIBGUESTFS_CACHEDIR=str(reference/'guestfs-cache'),LIBGUESTFS_TMPDIR=str(reference/'tmp'))
    listener=WORK/'listener.log'
    with listener.open('w') as stream:
        subprocess.run(['guestfish','--ro','-a',str(raw),'--listen'],env=env,stdout=stream,stderr=stream,check=True,timeout=30)
    pid=re.search(r'GUESTFISH_PID=(\d+)',listener.read_text())[1]
    try:
        subprocess.run(['guestfish','--remote='+pid,'run'],check=True,timeout=180)
        subprocess.run(['guestfish','--remote='+pid,'mount-options','ro,norecovery','/dev/sda1','/'],check=True,timeout=120)
        collect(pid)
    finally:
        subprocess.run(['guestfish','--remote='+pid,'exit'],check=True,timeout=120)


if __name__=='__main__':
    main()
