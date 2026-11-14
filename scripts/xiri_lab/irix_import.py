"""Build a reproducible vendor payload from a pinned, read-only IRIX donor."""
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import signal
import stat
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256

PREFIX = '/emul/irix'
FONTS = '/usr/local/share/xiri/fonts'
CATALOG = '/usr/lib/desktop/iconcatalog/pages/'


def absolute(path):
    if not isinstance(path, str) or not path.startswith('/') or path.startswith('//') or \
            posixpath.normpath(path) != path or any(c in path for c in '\n\r\x00'):
        raise ValueError('Unsafe absolute path: '+repr(path))
    return path


def destination(path):
    absolute(path)
    if not any(path.startswith(p+'/') for p in (PREFIX, FONTS)):
        raise ValueError('Destination outside the vendor/font namespaces: '+path)
    return path


def selection(profile, requested=()):
    if profile['schema'] != 1:
        raise ValueError('Unsupported import profile schema')
    components = set(profile['default_components']) | set(requested)
    for name in sorted(components):
        item = profile['components'].get(name)
        if item is None:
            raise ValueError('Unknown component: '+name)
        if not item['available']:
            raise ValueError(name+': '+item['reason'])
    rows = {}
    for source, row in profile['paths'].items():
        absolute(source)
        if row['component'] not in components:
            continue
        row = dict(row, source=source)
        dest = destination(row.get('destination', PREFIX+source))
        if dest in rows:
            raise ValueError('Conflicting destination: '+dest)
        if row['type'] not in ('file', 'directory', 'symlink'):
            raise ValueError('Unsupported payload type: '+source)
        rows[dest] = row
    validate_parents(rows)
    return sorted(components), rows


def validate_parents(rows):
    for name in rows:
        destination(name)
        for parent in PurePosixPath(name).parents:
            row = rows.get(str(parent))
            if row and row['type'] != 'directory':
                raise ValueError('Payload entry has a non-directory parent: '+name)


class Donor:
    """An owned guestfish listener; no donor paths are mounted on the host."""
    def __init__(self, raw, work):
        self.raw, self.work, self.pid = raw, work, None
        for name in ('cache', 'tmp'):
            (work/name).mkdir()
        self.env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
                        LIBGUESTFS_CACHEDIR=str(work/'cache'), LIBGUESTFS_TMPDIR=str(work/'tmp'))

    def __enter__(self):
        try:
            with (self.work/'guestfish.log').open('w+') as log:
                subprocess.run(['guestfish', '--ro', '--format=raw', '-a', str(self.raw), '--listen'],
                               env=self.env, stdout=log, stderr=log, check=True, timeout=45)
                log.seek(0)
                self.pid = re.search(r'GUESTFISH_PID=(\d+)', log.read())[1]
            self.call('run')
            self.call('mount-options', 'ro,norecovery', '/dev/sda1', '/')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def call(self, *arguments):
        result = subprocess.run(['guestfish', '--remote='+self.pid, *map(str, arguments)],
                                env=self.env, text=True, capture_output=True, timeout=180)
        if result.returncode:
            detail = result.stderr or (self.work/'guestfish.log').read_text()[-2000:]
            raise RuntimeError(str(arguments)+': '+detail)
        return result.stdout.rstrip('\n')

    def isfile(self, path):
        return self.call('is-file', path, 'followsymlinks:true') == 'true'

    def info(self, path):
        if self.call('exists', path) != 'true' and self.call('is-symlink', path) != 'true':
            raise ValueError('Missing required donor path: '+path)
        fields = dict(re.findall(r'^(\w+): (-?\d+)$', self.call('lstatns', path), re.M))
        mode = int(fields['st_mode'])
        kind = ('file' if stat.S_ISREG(mode) else 'directory' if stat.S_ISDIR(mode)
                else 'symlink' if stat.S_ISLNK(mode) else 'special')
        row = dict(source_type=kind, source_mode=oct(stat.S_IMODE(mode)))
        if kind == 'symlink':
            row['source_target'] = self.call('readlink', path)
        return row

    def __exit__(self, *unused):
        if self.pid:
            try:
                self.call('exit')
            finally:
                self.pid = None


def elf_parser():
    spec = importlib.util.spec_from_file_location('irix_elf', ROOT/'scripts/inventory-irix-desktop.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.elf


def resolve_link(source, target):
    if any(c in target for c in '\n\r\x00'):
        raise ValueError('Invalid link target: '+source)
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), target))


def collect(donor, rows, objects, parse_elf=None, library_paths=None):
    """Download selected files and their ELF/interpreter closure; record omissions."""
    parse_elf = parse_elf or elf_parser()
    queue = list(sorted(rows))
    complete, dependencies, omitted = {}, [], []
    isfile_cache = {}

    def isfile(path):
        if path not in isfile_cache:
            isfile_cache[path] = donor.isfile(path)
        return isfile_cache[path]

    def require(source, reason):
        absolute(source)
        dest = PREFIX+source
        if dest not in rows:
            rows[dest] = dict(source=source, type='file', component='dependency', required_by=reason)
            queue.append(dest)
        elif rows[dest]['type'] != 'file':
            raise ValueError('Dependency is not a regular payload file: '+source)
        return dest

    for dest in queue:
        row = rows[dest]
        source = row['source']
        info = donor.info(source)
        item = dict(row, **info)
        kind = row['type']
        if kind == 'file':
            if not isfile(source):
                raise ValueError('Required file is not readable: '+source)
            local = objects/str(len(complete))
            donor.call('download', source, local)
            digest = sha256(local)
            if row.get('sha256') and digest != row['sha256']:
                raise ValueError('Donor file hash mismatch: '+source)
            item.update(sha256=digest, bytes=local.stat().st_size,
                        canonical_path=donor.call('realpath', source))
            # Retain both names when an executable/library was a donor symlink.
            if item['canonical_path'] != source and dest.startswith(PREFIX+'/'):
                require(item['canonical_path'], source)
            with local.open('rb') as stream:
                head = stream.read(4096)
            executable = bool(int(info['source_mode'], 8) & 0o111)
            item['mode'] = '0555' if executable or head.startswith(b'\x7fELF') else '0444'
            if head.startswith(b'\x7fELF'):
                elf = parse_elf(local)
                if elf['machine'] != 8 or elf['abi'] not in ('n32', 'o32'):
                    raise ValueError('Unsupported ELF ABI: '+source)
                item['elf'] = {k: elf[k] for k in ('class', 'endian', 'machine', 'abi', 'needed', 'interpreter', 'rpath')}
                for interpreter in elf['interpreter']:
                    require(interpreter, source)
                # Some vendor launcher scripts set a private LD_LIBRARY_PATH;
                # these scoped paths are explicit profile inputs, not a global
                # basename search that could select an unrelated ABI/library.
                dirs = [d for prefix, paths in (library_paths or {}).items()
                        if source.startswith(prefix) for d in paths]
                dirs += [d for value in elf['rpath'] for d in value.split(':') if d.startswith('/')]
                dirs += (['/usr/lib32', '/usr/lib32/internal', '/lib32', '/usr/freeware/lib32']
                         if elf['abi'] == 'n32' else
                         ['/usr/lib', '/usr/lib/internal', '/lib', '/usr/freeware/lib'])
                for needed in elf['needed']:
                    if '/' in needed:
                        raise ValueError('Unexpected ELF dependency name: '+needed)
                    found = next((d+'/'+needed for d in dirs if isfile(d+'/'+needed)), None)
                    if not found:
                        raise ValueError('Missing ELF dependency '+needed+' for '+source)
                    require(found, source)
                    dependencies.append(dict(source=source, needed=needed, selected=found))
            elif executable and head.startswith(b'#!'):
                interpreter = head.splitlines()[0][2:].strip().split()[0].decode('ascii')
                if not interpreter.startswith('/'):
                    raise ValueError('Non-absolute executable interpreter '+interpreter+' in '+source)
                require(interpreter, source)
                item['interpreter'] = interpreter
            item['_local'] = local
        elif kind == 'symlink':
            if info['source_type'] != 'symlink' or info['source_target'] != row['target']:
                raise ValueError('Donor symlink mismatch: '+source)
            item['mode'] = '0777'
        else:
            if info['source_type'] != 'directory':
                raise ValueError('Donor directory mismatch: '+source)
            item['mode'] = '0755'
        complete[dest] = item
        if len(complete) % 200 == 0:
            print('Imported', len(complete), 'paths', flush=True)

    def included(source, seen=None):
        seen = set() if seen is None else seen
        if source in seen:
            return False
        seen.add(source)
        row = complete.get(PREFIX+source)
        if row is None:
            return False
        if row['type'] == 'symlink':
            return included(resolve_link(source, row['target']), seen)
        return True

    # Keep original link text for IRIX path lookup, but never advertise missing
    # optional programs from another installation's catalog.
    for dest, row in list(complete.items()):
        if row['source'].startswith(CATALOG) and row['type'] == 'symlink' and not included(row['source']):
            omitted.append(dict(source=row['source'], target=row['target'], reason='target not included'))
            del complete[dest]
    validate_parents(complete)
    return complete, dependencies, omitted


def write_payload(path, rows):
    """Never materialize donor symlinks on the host; normalize tar and gzip."""
    validate_parents(rows)
    members = dict(rows)
    for dest in rows:
        for parent in PurePosixPath(dest).parents:
            if str(parent) != '/':
                members.setdefault(str(parent), dict(type='directory', mode='0755'))
    with path.open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
            for dest, row in sorted(members.items()):
                member = tarfile.TarInfo(dest.lstrip('/'))
                member.mode = int(row['mode'], 8)
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ''
                if row['type'] == 'directory':
                    member.type = tarfile.DIRTYPE
                    tar.addfile(member)
                elif row['type'] == 'symlink':
                    member.type = tarfile.SYMTYPE
                    member.linkname = row['target']
                    tar.addfile(member)
                else:
                    member.size = row['bytes']
                    with row['_local'].open('rb') as stream:
                        tar.addfile(member, stream)


def check_source(source, profile):
    source = source.resolve(strict=True)
    for suffix in ('.overlay', '.overlay.dirty', '.diff', '.diff.chd'):
        if Path(str(source)+suffix).exists():
            raise ValueError('Export a standalone donor before importing: '+str(source)+suffix)
    kind = 'chd' if source.suffix.lower() == '.chd' else 'raw'
    digest = sha256(source)
    if digest != profile['donor'][kind+'_sha256']:
        raise ValueError('Source '+kind+' hash does not match profile '+profile['id'])
    return source, kind, digest


def build(profile_path, source, output, components=(), chdman='chdman'):
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    selected, rows = selection(profile, components)
    source, kind, digest = check_source(source, profile)
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    try:
        with tempfile.TemporaryDirectory(prefix='.import-', dir=output) as temp:
            work = Path(temp)
            raw = source
            if kind == 'chd':
                raw = work/'donor.raw'
                with (output/'extract.log').open('w') as log:
                    subprocess.run([chdman, 'extracthd', '-i', str(source), '-o', str(raw)],
                                   stdout=log, stderr=log, check=True)
                if sha256(raw) != profile['donor']['raw_sha256']:
                    raise ValueError('Extracted donor hash mismatch')
            objects = work/'objects'
            objects.mkdir()
            with Donor(raw, work) as donor:
                complete, dependencies, omitted = collect(donor, rows, objects,
                                                          library_paths=profile.get('library_paths'))
            if sha256(source) != digest or sha256(raw) != profile['donor']['raw_sha256']:
                raise ValueError('Source changed during import')
            archive = output/'payload.tar.gz'
            write_payload(archive, complete)
            ledger = dict(schema=1, status='payload-verified', profile=profile['id'],
                          profile_sha256=hashlib.sha256(profile_bytes).hexdigest(), release=profile['release'],
                          donor=profile['donor'], components=selected,
                          payload_sha256=sha256(archive),
                          files={p:{k:v for k,v in row.items() if k != '_local'} for p,row in sorted(complete.items())},
                          dependencies=dependencies, omitted_catalog_entries=omitted,
                          native_prerequisites=profile['native_prerequisites'])
            (output/'manifest.json').write_text(json.dumps(ledger, indent=2, sort_keys=True)+'\n')
            print('Payload:', archive, '\nSHA256:', ledger['payload_sha256'], flush=True)
            return ledger
    except BaseException:
        # Keep diagnostics, but never leave a failed package looking installable.
        for name in ('manifest.json', 'payload.tar.gz'):
            (output/name).unlink(missing_ok=True)
        raise


def add_arguments(parser):
    parser.add_argument('--profile', type=Path, default=ROOT/'profiles/irix-6.5.22f-v1.json')
    parser.add_argument('--source', type=Path, required=True, help='verified standalone CHD or raw donor')
    parser.add_argument('--output', type=Path, required=True, help='new output directory')
    parser.add_argument('--component', action='append', default=[], help='include an optional component')
    parser.add_argument('--chdman', default='chdman')
    parser.add_argument('--dry-run', action='store_true', help='validate profile/selection without opening media')


def run(args):
    if args.dry_run:
        profile = json.loads(args.profile.read_text())
        selected, rows = selection(profile, args.component)
        print(json.dumps(dict(profile=profile['id'], components=selected, paths=len(rows),
                              source=str(args.source), output=str(args.output),
                              native_prerequisites=profile['native_prerequisites']), indent=2))
    else:
        previous = signal.getsignal(signal.SIGTERM)

        def interrupted(signum, frame):
            raise KeyboardInterrupt('Import interrupted; cleaning up the owned appliance and temporary files')

        signal.signal(signal.SIGTERM, interrupted)
        try:
            build(args.profile, args.source, args.output, args.component, args.chdman)
        finally:
            signal.signal(signal.SIGTERM, previous)
    return 0
