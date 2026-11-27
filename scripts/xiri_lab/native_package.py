"""Assemble pinned native artifacts and a newly cross-built session runtime."""
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import shlex
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256
from .irix_import import absolute, elf_parser


def rooted(root, name):
    """Resolve target symlinks inside a sysroot, including absolute links."""
    absolute(name)
    todo = list(PurePosixPath(name).parts[1:])
    parts, links = [], 0
    while todo:
        part = todo.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                raise ValueError('Link escapes target root: '+name)
            parts.pop()
            continue
        p = root.joinpath(*parts, part)
        if p.is_symlink():
            links += 1
            if links > 40:
                raise ValueError('Symlink loop: '+name)
            target = os.readlink(p)
            if target.startswith('/'):
                parts = []
            todo = list(PurePosixPath(target).parts[1:] if target.startswith('/')
                        else PurePosixPath(target).parts) + todo
        else:
            parts.append(part)
    return root.joinpath(*parts)


def pins(profile, artifacts, compiler, sets):
    if profile['schema'] != 1:
        raise ValueError('Unsupported native package profile')
    if set(artifacts) != set(profile['artifacts']):
        raise ValueError('Supply exactly the named native artifacts')
    destinations=[row['destination'] for row in profile['artifacts'].values()]
    if len(set(destinations)) != len(destinations):
        raise ValueError('Conflicting native artifact destinations')
    for key, row in profile['artifacts'].items():
        absolute(row['destination'])
        if sha256(artifacts[key]) != row['sha256']:
            raise ValueError('Native artifact mismatch: '+key)
        for name, digest in row['provenance'].items():
            if sha256(ROOT/name) != digest:
                raise ValueError('Artifact provenance changed: '+name)
    if sha256(compiler) != profile['compiler_sha256']:
        raise ValueError('Cross compiler does not match the qualified toolchain')
    manifest = ROOT/profile['sets_manifest']['path']
    if sha256(manifest) != profile['sets_manifest']['sha256']:
        raise ValueError('NetBSD set manifest changed')
    hashes = {line.split()[1].lstrip('*'):line.split()[0]
              for line in manifest.read_text().splitlines() if line.strip()}
    selected = {}
    for name in profile['target_sets'] + profile['build_sets']:
        expected = hashes['sgimips/binary/sets/'+name]
        with (sets/name).open('rb') as stream:
            observed = hashlib.file_digest(stream, 'sha512').hexdigest()
        if expected != observed:
            raise ValueError('NetBSD distribution set mismatch: '+name)
        selected[name] = expected
    return selected


def prerequisites(sysroot, payload, programs, resources):
    """Audit the native ELF closure without executing target binaries."""
    parse = elf_parser()
    queue = [(name, rooted(sysroot, name)) for name in programs]
    queue += [(name, p) for name,p in payload.items() if p.read_bytes()[:4] == b'\x7fELF']
    required, edges, seen = {}, [], set()

    def require(name):
        absolute(name)
        p = rooted(sysroot, name)
        if not p.is_file():
            raise ValueError('Missing native prerequisite: '+name)
        required[name] = dict(sha256=sha256(p), canonical_path='/'+str(p.relative_to(sysroot)),
                              executable=bool(p.stat().st_mode & 0o111))
        queue.append((name,p))
        return p

    for name in programs + resources:
        require(name)
    for name, p in queue:
        if name in seen:
            continue
        seen.add(name)
        if p.read_bytes()[:4] != b'\x7fELF':
            continue
        elf = parse(p)
        if elf['abi'] != 'o32':
            raise ValueError('Expected native o32 userland: '+name)
        for interpreter in elf['interpreter']:
            require(interpreter)
        directories = [d for paths in elf['rpath'] for d in paths.split(':') if d.startswith('/')]
        directories += ['/lib','/usr/lib','/usr/X11R7/lib']
        for library in elf['needed']:
            if '/' in library:
                raise ValueError('Non-basename native dependency: '+library)
            selected = next((d+'/'+library for d in directories if rooted(sysroot,d+'/'+library).is_file()),None)
            if selected is None:
                raise ValueError('Unresolved native library '+library+' for '+name)
            require(selected)
            edges.append(dict(source=name,needed=library,selected=selected))
    return dict(sorted(required.items())), edges


def archive_tree(source, archive):
    """Normalize package metadata without following links in the payload."""
    with archive.open('xb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT) as tar:
            for path in sorted(source.rglob('*')):
                name = str(path.relative_to(source))
                info = tarfile.TarInfo(name)
                info.uid = info.gid = info.mtime = 0
                info.mode = stat.S_IMODE(path.lstat().st_mode)
                if path.is_symlink():
                    info.type = tarfile.SYMTYPE
                    info.linkname = os.readlink(path)
                    tar.addfile(info)
                elif path.is_dir():
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    tar.addfile(info)
                else:
                    info.size = path.stat().st_size
                    with path.open('rb') as stream:
                        tar.addfile(info,stream)


def ledger(tree):
    result = {}
    for path in sorted(tree.rglob('*')):
        if path.is_dir() and not path.is_symlink():
            continue
        name = str(path.relative_to(tree))
        if any(c in name for c in '|\n\r\t'):
            raise ValueError('Invalid package member: '+name)
        if path.is_symlink():
            row = dict(type='symlink',target=os.readlink(path),mode='0777')
        elif path.is_file():
            row = dict(type='file',sha256=sha256(path),bytes=path.stat().st_size,
                       mode=format(stat.S_IMODE(path.stat().st_mode),'04o'))
        else:
            raise ValueError('Unsupported package member: '+name)
        if name.startswith('kernel/'):
            row.update(destination='/'+path.name,policy='separate-kernel-activation')
        elif name.startswith('root/'):
            dest='/'+name[5:]
            row.update(destination=dest,policy='preserve-config' if dest.startswith('/etc/xiri/') and
                       not dest.endswith('.example') else 'replace-owned-file')
        result[name] = row
    return result


def source_inputs(profile):
    runtime=ROOT/'runtime'
    names={'Makefile','install.sh','bin','sbin','etc','libexec','rc.d'}
    sources={str(p.relative_to(ROOT)):sha256(p) for p in sorted(runtime.rglob('*'))
             if p.is_file() and p.relative_to(runtime).parts[0] in names}
    sources.update({p:sha256(ROOT/p) for p in ['scripts/xiri_lab/native_package.py',
                    'packaging/native/preflight.sh','packaging/native/README.md',
                    *profile['configuration_sources'].values(), *profile.get('boot_services', {}).values()]})
    return sources


def build(profile_path, inputs_path, compiler, sets, output):
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    artifacts = {k:Path(v).resolve(strict=True) for k,v in json.loads(inputs_path.read_text()).items()}
    compiler,sets,output = compiler.resolve(strict=True),sets.resolve(strict=True),output.absolute()
    selected_sets = pins(profile,artifacts,compiler,sets)
    sources_before = source_inputs(profile)
    output.mkdir(parents=True,exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix='.build-',dir=output) as temporary:
            work=Path(temporary);sysroot=work/'sysroot';sysroot.mkdir()
            tree=work/'package';tree.mkdir();stage=tree/'root';stage.mkdir()
            binary=work/'runtime'
            with (output/'build.log').open('w') as log:
                def run(*command, **kwargs):
                    log.write(shlex.join(map(str,command))+'\n');log.flush()
                    subprocess.run(list(map(str,command)),check=True,stdout=log,stderr=subprocess.STDOUT,**kwargs)
                # Only verified public NetBSD distribution sets enter this root.
                for name in selected_sets:
                    prefixes = ['./usr/include','./usr/lib'] if name=='comp.tgz' else \
                               ['./usr/X11R7'] if name=='xcomp.tgz' else []
                    run('tar','--no-same-owner','-xzf',sets/name,'-C',sysroot,*prefixes)
                machine=sysroot/'usr/include/machine'
                if not machine.exists():
                    machine.symlink_to('sgimips')
                cc=shlex.join([str(compiler),'--sysroot='+str(sysroot)])
                run('make','-j2','BUILDDIR='+str(binary),'CC='+cc,
                    'X11_CPPFLAGS=-I'+str(sysroot/'usr/X11R7/include'),
                    'X11_LDFLAGS=-L'+str(sysroot/'usr/X11R7/lib')+' -Wl,-rpath,/usr/X11R7/lib',
                    cwd=ROOT/'runtime')
                env=dict(os.environ,DESTDIR=str(stage),BUILDDIR=str(binary))
                run('sh','install.sh',cwd=ROOT/'runtime',env=env)
                run(compiler,'--version')
            for key,row in profile['artifacts'].items():
                relative = 'kernel/'+Path(row['destination']).name if row['component']=='kernel' else 'root'+row['destination']
                target=tree/relative;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(artifacts[key],target)
                target.chmod(int(row['mode'], 8) if 'mode' in row else (0o444 if key=='module' else 0o555))
                if sha256(target)!=row['sha256']:
                    raise ValueError('Native artifact changed while packaging: '+key)
            for dest,src in profile['configuration_sources'].items():
                absolute(dest)
                target=stage/dest.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/src,target);target.chmod(0o444)
            for name, src in profile.get('boot_services', {}).items():
                target = stage / 'etc/rc.d' / name
                shutil.copyfile(ROOT / src, target)
                target.chmod(0o555)
            for dest, link in profile.get('native_links', {}).items():
                absolute(dest)
                target = stage / dest.lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(link)
            examples=stage/'usr/local/share/xiri/examples';(examples/'rc.conf.d').mkdir(parents=True, exist_ok=True)
            for name,text in {'rpcbind':'rpcbind=YES\nrpcbind_flags="-h 127.0.0.1"\n',
                              'xiri_devices':'xiri_devices=YES\n',
                              'xiri_famd':'xiri_famd=YES\n#xiri_famd_logfile="/var/log/xiri-fam.log"\n',
                              'xiri_sessions':'xiri_sessions=YES\n',
                              'xiri_cdrom':'xiri_cdrom=YES\n',
                              'xdm':'xdm=YES\nxdm_flags="-server /etc/xiri/xdm/Xservers -resources /etc/xiri/xdm/Xresources"\n'}.items():
                (examples/'rc.conf.d'/name).write_text(text);(examples/'rc.conf.d'/name).chmod(0o444)
            (examples/'modules.conf').write_text('compat_irix_o32\n');(examples/'modules.conf').chmod(0o444)
            payload={ '/'+str(p.relative_to(stage)):p for p in stage.rglob('*') if p.is_file() and not p.is_symlink()
                      and not str(p.relative_to(stage)).startswith('stand/') }
            required,edges=prerequisites(sysroot,payload,profile['native_programs'],profile['native_resources'])
            files=ledger(tree)
            # Keep stock replacements outside the install ledger for CD rollback.
            for row in profile['artifacts'].values():
                if 'stock_sha256' in row:
                    original = rooted(sysroot, row['destination'])
                    if sha256(original) != row['stock_sha256']:
                        raise ValueError('Stock display artifact differs: ' + row['destination'])
                    backup = tree / ('stock' + row['destination'])
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, backup)
                    backup.chmod(0o444)
            (tree/'files.tsv').write_text(''.join('|'.join([name,row['type'],row['mode'],row.get('sha256',row.get('target','')),row['policy']])+'\n' for name,row in files.items()))
            (tree/'prerequisites.tsv').write_text(''.join(name+'|'+row['sha256']+'\n' for name,row in required.items()))
            target=dict(profile['target'],kernel_sha256=profile['artifacts']['kernel']['sha256'])
            (tree/'target.conf').write_text(''.join(k+'='+shlex.quote(v)+'\n' for k,v in sorted(target.items())))
            shutil.copyfile(ROOT/'packaging/native/preflight.sh',tree/'preflight.sh');(tree/'preflight.sh').chmod(0o555)
            shutil.copyfile(ROOT/'packaging/native/README.md',tree/'README.md')
            for p in tree.iterdir():
                if p.is_file() and p.name!='preflight.sh':p.chmod(0o444)
            sums=''.join('SHA256 ('+str(p.relative_to(tree))+') = '+sha256(p)+'\n'
                         for p in sorted(tree.rglob('*')) if p.is_file() and not p.is_symlink())
            (tree/'SHA256').write_text(sums);(tree/'SHA256').chmod(0o444)
            archive_tree(tree,output/'native.tar.gz')
            if source_inputs(profile) != sources_before:
                raise ValueError('Native build inputs changed during packaging')
            result=dict(schema=1,status='native-package-built',profile=profile['id'],
                        profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),target=target,
                        archive_sha256=sha256(output/'native.tar.gz'),files=files,
                        prerequisites=required,dependencies=edges,sets=selected_sets,
                        artifacts=profile['artifacts'],sources=sources_before,compiler_sha256=profile['compiler_sha256'],
                        required_aliases=profile['required_aliases'],generated_state=profile['generated_state'],
                        preservation_policy=profile['preserve'],
                        release_lines=profile['release_lines'],
                        limits=['Assembly and read-only preflight; managed installation/recovery and clean-target boot qualification are separate.',
                                'Pinned kernel, module and patched service/driver artifacts are supplied explicitly, not rebuilt by this packager.',
                                'No IRIX files, accounts, passwords, homes or machine-wide configuration are copied from a prepared image.'])
            (output/'manifest.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
            print('Native package:',output/'native.tar.gz',flush=True)
            return result
    except BaseException:
        for name in ('manifest.json','native.tar.gz'):(output/name).unlink(missing_ok=True)
        raise


def add_arguments(parser):
    parser.add_argument('--profile',type=Path,default=ROOT/'profiles/netbsd-sgimips-native-v1.json')
    parser.add_argument('--artifacts',required=True,type=Path,help='JSON mapping artifact names to explicit local binary paths')
    parser.add_argument('--compiler',required=True,type=Path,help='qualified mipseb cross compiler')
    parser.add_argument('--sets',required=True,type=Path,help='pinned NetBSD 11.0 sgimips distribution sets directory')
    parser.add_argument('--output',required=True,type=Path,help='new package directory')


def run(args):
    previous=signal.getsignal(signal.SIGTERM)
    def interrupted(signum,frame):
        raise KeyboardInterrupt('Native packaging interrupted; cleaning temporary files')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        build(args.profile,args.artifacts,args.compiler,args.sets,args.output)
    finally:
        signal.signal(signal.SIGTERM,previous)
    return 0
