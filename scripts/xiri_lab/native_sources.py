"""Resolve and prepare the native Indy installer inputs in disposable Git checkouts."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'src': ('https://github.com/NetBSD/src.git', 'trunk'),
    'fork': ('https://github.com/salvogendut/NetBSD-xiri.git', 'xiri'),
    'xsrc': ('https://github.com/NetBSD/xsrc.git', 'trunk'),
}
SAVER = Path('external/mit/xorg-server.old/dist')
INPUTS = ('lab/native-iso/newport-current.patch', 'lab/sgi-saver/saver.patch',
          'lab/sgi-saver/sgi-saver.inc', 'lab/native-iso/indy-sysinst.patch')
RECIPE = ('scripts/build-xiribsd-iso.py', 'scripts/xiri_lab/native_sources.py',
          'scripts/xiri_lab/native_iso.py', 'lab/ip28-kernel/build.sh',
          'lab/ip28-kernel/build-module.sh', 'lab/irix-module/XIRI_IRIX_MODULE',
          'lab/newport-accel/xorg.conf', 'runtime/etc/xdm-Xservers',
          'runtime/etc/xdm-Xresources', 'runtime/etc/xiri-logo.xpm',
          'packaging/xiriprep/CMakeLists.txt', 'packaging/xiriprep/donor-read.c',
          'packaging/xiriprep/xiriprep', 'packaging/xiriprep/select-desktop.sh', 'scripts/setup-xiri-user.sh',
          'profiles/irix-6.5.22f-v1.json', 'profiles/irix-6.5.30f-v1.json')


def git(directory, *args):
    return subprocess.check_output(['git', '-C', directory, *args], text=True).strip()


def revision(value):
    if not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError(f'Invalid Git object name: {value!r}')
    return value


def resolve():
    pins = {}
    for name, (url, branch) in SOURCES.items():
        output = git(ROOT, 'ls-remote', '--exit-code', url, 'refs/heads/' + branch)
        pins[name] = revision(output.split()[0])
    return pins


def materialize(gitdir, name, commit):
    if subprocess.run(['git', '-C', gitdir, 'cat-file', '-e', commit + '^{commit}'],
                      stderr=subprocess.DEVNULL).returncode:
        args = ['fetch', '--no-tags']
        if name == 'xsrc':
            args.append('--depth=1')
        git(gitdir, *args, SOURCES[name][0], commit)


def prepare_tree(name, work, pins, reference, expected):
    target = work / name
    if target.exists():
        if not expected or git(target, 'rev-parse', 'HEAD^{tree}') != expected:
            raise ValueError(f'Unexpected source tree at {target}. Choose a new build directory.')
        if git(target, 'status', '--porcelain', '--untracked-files=all'):
            raise ValueError(f'Source checkout has local changes: {target}')
        return expected
    with tempfile.TemporaryDirectory(prefix='.' + name + '-', dir=work) as tmp:
        repo = Path(tmp) / name
        if reference:
            subprocess.run(['git', 'clone', '-q', '--no-checkout', '--shared',
                            str(reference.resolve()), repo], check=True)
        else:
            git(work, 'init', '-q', str(repo))
        materialize(repo, name, pins[name])
        parents = [pins[name]]
        if name == 'src':
            materialize(repo, 'fork', pins['fork'])
            merged = subprocess.run(['git', '-C', repo, 'merge-tree', '--write-tree',
                                     pins['src'], pins['fork']], text=True, stdout=subprocess.PIPE)
            if merged.returncode:
                raise ValueError('NetBSD fork merge failed:\n' + merged.stdout)
            tree = revision(merged.stdout.strip())
            git(repo, 'read-tree', '--reset', '-u', tree)
            git(repo, 'apply', '--index', str(ROOT / 'lab/native-iso/indy-sysinst.patch'))
            tree = revision(git(repo, 'write-tree'))
            parents.append(pins['fork'])
        else:
            git(repo, 'checkout', '-q', '--detach', pins[name])
            git(repo, 'apply', '--index', str(ROOT / INPUTS[0]))
            git(repo, 'apply', '--index', '--directory=' + str(SAVER), str(ROOT / INPUTS[1]))
            include = SAVER / 'Xext/sgi-saver.inc'
            if (repo / include).exists():
                raise ValueError(f'Upstream already supplies {include}. Review the saver patch.')
            shutil.copyfile(ROOT / INPUTS[2], repo / include)
            git(repo, 'add', str(include))
            tree = revision(git(repo, 'write-tree'))
        if expected and tree != expected:
            raise ValueError(f'{name} tree differs from the recorded input: {tree}')
        date = git(repo, 'show', '-s', '--format=%cI', pins[name])
        env = os.environ.copy()
        for role in ('AUTHOR', 'COMMITTER'):
            env.update({f'GIT_{role}_NAME': 'XiriBSD build', f'GIT_{role}_EMAIL': 'build@localhost',
                        f'GIT_{role}_DATE': date})
        cmd = ['git', '-C', repo, 'commit-tree', tree, '-m', 'Prepare native XiriBSD ' + name]
        for parent in dict.fromkeys(parents):
            cmd += ['-p', parent]
        commit = subprocess.check_output(cmd, env=env, text=True).strip()
        git(repo, 'checkout', '-q', '--detach', commit)
        repo.rename(target)
        return tree


def prepare(work, lock_path=None, src_reference=None, xsrc_reference=None):
    work.mkdir(parents=True, exist_ok=True)
    saved = work / 'sources.json'
    record = json.loads(saved.read_text()) if saved.exists() else None
    if lock_path:
        requested = json.loads(lock_path.read_text())
        if record and record != requested:
            raise ValueError('The build directory already contains a different source lock.')
        record = requested
    inputs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INPUTS}
    recipe = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in RECIPE}
    if record:
        if record['schema'] != 1 or record['patch_sha256'] != inputs or record.get('recipe_sha256') != recipe:
            raise ValueError('Source lock differs from the installer recipe. Use the recorded Xiri revision.')
        pins = {name: revision(record['commits'][name]) for name in SOURCES}
        for name in ('src', 'xsrc'):
            revision(record['trees'][name])
        revision(record['xiri'])
    else:
        git(ROOT, 'ls-files', '--error-unmatch', '--', *INPUTS, *RECIPE)
        if git(ROOT, 'status', '--porcelain', '--', *INPUTS, *RECIPE):
            raise ValueError('Commit installer inputs before resolving a new source lock.')
        pins = resolve()
    trees = {}
    # Retrying a failed source preparation must never discard a user's checkout.
    # Prepare both trees together before publishing either one on a first run.
    with tempfile.TemporaryDirectory(prefix='.sources-', dir=work) as tmp:
        for name, reference in [('src', src_reference), ('xsrc', xsrc_reference)]:
            directory = work if (work / name).exists() else Path(tmp)
            trees[name] = prepare_tree(name, directory, pins, reference,
                                       record['trees'][name] if record else None)
        result = record or dict(schema=1, commits=pins, trees=trees, patch_sha256=inputs, recipe_sha256=recipe,
                                xiri=git(ROOT, 'rev-parse', 'HEAD'))
        if not saved.exists():
            draft = Path(tmp) / 'sources.json'
            draft.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
            draft.replace(saved)
        for name in trees:
            if (Path(tmp) / name).exists():
                (Path(tmp) / name).rename(work / name)
    return result
