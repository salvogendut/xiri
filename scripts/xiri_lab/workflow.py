"""Manifest-led entry points for the maintained desktop workflow."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from . import ROOT, sha256


def read_json(path):
    return json.loads(path.read_text())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def integration_worktree(checkout, branch):
    """Find the branch owner without switching another task's checkout."""
    for record in git(checkout, 'worktree', 'list', '--porcelain').split('\n\n'):
        fields = dict(line.split(' ', 1) for line in record.splitlines() if ' ' in line)
        if fields.get('branch') == 'refs/heads/'+branch:
            return Path(fields['worktree'])
    raise ValueError(f'No worktree owns {branch} in {checkout}; create one before building')


def selected_image(root, config):
    pointer = read_json(root/config['image_pointer'])
    bundle = (root/pointer['bundle']).resolve()
    manifest = read_json(bundle/'manifest.json')
    if manifest['status'] != 'chd-roundtrip-verified':
        raise ValueError('Selected image has not passed CHD round-trip verification')
    if pointer['chd_sha256'] != manifest['chd_sha256']:
        raise ValueError('Selected image pointer and bundle disagree')
    return pointer, bundle, manifest


def verify_image(root, pointer, bundle, manifest):
    files = {
        'netbsd-xiri.chd': manifest['chd_sha256'],
        'seed-result.json': manifest['source_result_sha256'],
        'iris.toml': manifest['config_sha256'],
        'copy-ledger.json': manifest['copy_ledger_sha256'],
        'permissions.json': manifest['permission_manifest_sha256'],
        'tftp/netbsd-XIRI_INDY': manifest['pin']['boot_kernel_sha256'],
        **manifest['emulator_files'],
    }
    if manifest['pin'].get('module_build_manifest'):
        files['irix-module-build.json'] = manifest['pin']['module_build_manifest_sha256']
    if manifest.get('qualification_nvram'):
        files[manifest['qualification_nvram']] = manifest['qualification_nvram_sha256']
    if files.get('emulator/iris') != manifest['pin']['emulator_sha256'] or \
       files.get('emulator/iris-ci') != manifest['pin']['ci_client_sha256']:
        raise ValueError('Bundled emulator hashes disagree with the qualification pin')
    for relative, digest in files.items():
        if sha256(bundle/relative) != digest:
            raise ValueError('Artifact hash mismatch: '+str(bundle/relative))
    if sha256(root/pointer['qualification']) != pointer['qualification_sha256']:
        raise ValueError('Selected qualification record hash mismatch')
    # Both serial and graphical NVRAM, overlays and snapshots are mutable.
    # Their original digests remain provenance, not a reason to reset user state.
    return len(files)+1


def run_step(root, directory, name, command, env=None):
    """Record commands/status and let the existing probe own guest cleanup."""
    record = dict(command=[str(v) for v in command], environment=env or {}, status='running')
    record_path = directory/(name+'.json')
    record_path.write_text(json.dumps(record, indent=2)+'\n')
    log_path = directory/(name+'.log')
    child = None
    interrupted = False
    previous = {}

    def interrupt(signum, frame):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            print('\nWaiting for the command to clean up its owned processes…', flush=True)

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, interrupt)
        with log_path.open('w') as log, log_path.open(errors='backslashreplace') as reader:
            child = subprocess.Popen(record['command'], cwd=root, env=dict(os.environ, **(env or {})),
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            record['pid'] = child.pid
            record_path.write_text(json.dumps(record, indent=2)+'\n')
            while child.poll() is None:
                if interrupted:
                    # Also covers a signal received during Popen itself.
                    os.killpg(child.pid, signal.SIGINT)
                    child.wait()
                    break
                text = reader.read()
                if text:
                    print(text, end='', flush=True)
                time.sleep(.2)
            print(reader.read(), end='', flush=True)
        record.update(status='interrupted' if interrupted else 'complete', exit_status=child.returncode)
        if interrupted:
            raise KeyboardInterrupt
        if child.returncode:
            raise subprocess.CalledProcessError(child.returncode, record['command'])
        return log_path.read_text()
    except BaseException as error:
        if record['status'] == 'running':
            record.update(status='failed', error=str(error))
        raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        record_path.write_text(json.dumps(record, indent=2)+'\n')


def build_command(root, config, target):
    source = integration_worktree(root/config[target+'_checkout'], config['integration_branch'])
    if git(source, 'diff', '--name-only', '--diff-filter=U'):
        raise ValueError('Resolve the merge in '+str(source)+' before building')
    output = root/'.work/builds'/target
    # Fixed output directories intentionally cannot alias qualified artifacts.
    if output.resolve() != output.absolute() or (root/'.work/builds').is_symlink():
        raise ValueError('Build output must not be redirected through a symlink')
    if target == 'netbsd':
        env = dict(XIRI_NETBSD_SOURCE_DIR=str(source), XIRI_NETBSD_BUILD_DIR=str(output),
                   XIRI_NETBSD_TFTP_DIR=str(output/'tftp'), XIRI_NETBSD_CONFIG=str(root/config['kernel_config']),
                   XIRI_NETBSD_ARCH=config['kernel_arch'], XIRI_BUILD_JOBS=str(config['build_jobs']))
        return ['bash', root/'scripts/build-netbsd-kernel.sh', 'all'], env
    env = dict(RUSTUP_HOME=str(root/'.work/rustup'), CARGO_HOME=str(root/'.work/cargo'),
               CARGO_TARGET_DIR=str(output), CARGO_BUILD_JOBS=str(config['build_jobs']))
    command = ['toolbox', 'run', '-c', 'xiri-iris', 'env',
               *[key+'='+value for key, value in env.items()], root/'.work/cargo/bin/cargo',
               '+'+config['rust_toolchain'], 'build', '--locked', '--offline', '--release',
               '--manifest-path', source/'Cargo.toml', '--bin', 'iris', '--bin', 'iris-ci']
    return command, {}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    status = sub.add_parser('status', help='show selected artifacts and current source branches')
    status.add_argument('--json', action='store_true')
    sub.add_parser('doctor', help='verify selected immutable artifacts and host prerequisites')
    run = sub.add_parser('run', help='open the selected manual image, preserving its user state')
    check = sub.add_parser('check', help='cold-boot a disposable copy and qualify the desktop')
    seed = sub.add_parser('seed', help='materialize a reusable raw automation seed')
    seed.add_argument('--output', type=Path)
    build = sub.add_parser('build', help='build the current integration branch in isolated output')
    build.add_argument('target', choices=['kernel', 'iris'])
    image = sub.add_parser('image', help='package a halted qualified seed into a new CHD bundle')
    image.add_argument('--seed-run', required=True, type=Path)
    image.add_argument('--output', required=True, type=Path)
    image.add_argument('--baseline', type=Path)
    image.add_argument('--kernel', type=Path)
    image.add_argument('--iris-bin-dir', type=Path)
    for command in [run, check, seed, build, image]:
        command.add_argument('--dry-run', action='store_true', help='print commands without executing')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    root = ROOT
    config = read_json(root/'config/development.json')
    if config['schema'] != 1:
        raise ValueError('Unsupported development configuration schema')
    if config['build_jobs'] not in (1, 2):
        raise ValueError('Use one or two build jobs for fork builds')
    if args.action == 'build':
        command, env = build_command(root, config, 'netbsd' if args.target == 'kernel' else 'iris')
    else:
        pointer, bundle, manifest = selected_image(root, config)
        if args.action == 'status':
            data = dict(bundle=str(bundle), available=(bundle/'netbsd-xiri.chd').is_file(),
                        image_pin=manifest['pin'], kernel_source_equivalent=pointer.get('kernel_source_equivalent_commit'),
                        qualification=pointer['qualification'], sources={})
            for project in ['netbsd', 'iris']:
                try:
                    source = integration_worktree(root/config[project+'_checkout'], config['integration_branch'])
                    data['sources'][project] = dict(path=str(source), revision=git(source, 'rev-parse', 'HEAD'),
                                                    status=git(source, 'status', '--short'))
                except (OSError, ValueError, subprocess.CalledProcessError) as error:
                    data['sources'][project] = dict(error=str(error))
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print('Selected image:', bundle)
                print('Image IRIS:', manifest['pin']['emulator_revision'])
                print('Image kernel source equivalent:', data['kernel_source_equivalent'])
                print('Qualification:', pointer['qualification'])
                for project, source in data['sources'].items():
                    print(project+':', source.get('revision', source.get('error')), source.get('path', ''))
                    if source.get('status'):
                        print(source['status'])
            return 0
        if args.action == 'doctor':
            count = verify_image(root, pointer, bundle, manifest)
            missing = [tool for tool in ['git', 'toolbox', 'genisoimage', 'magick', 'cp'] if not shutil.which(tool)]
            if missing:
                raise ValueError('Missing host tools: '+', '.join(missing))
            subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'sh', '-c',
                            'command -v chdman && command -v Xvfb'], check=True)
            print(f'Verified {count} immutable artifacts; host tools and Toolbox available.')
            print('NVRAM and manual overlays are preserved as mutable user state.')
            return 0
        env = {}
        if args.action == 'run':
            command = [bundle/'run-iris.sh']
        elif args.action == 'check':
            if manifest.get('session_manager') == 'xdm':
                command = [sys.executable, root/'scripts/probe-xiri-xdm.py', '--bundle', bundle]
                if manifest.get('winterm_checks'):
                    command.append('--winterm')
            else:
                command = [sys.executable, root/'scripts/probe-xiri-image.py', bundle,
                           '--iris-bin-dir', bundle/'emulator', '--arrange-winterm']
        elif args.action == 'seed':
            output = (args.output or root/'.work/xiri-image'/('seed-'+manifest['chd_sha256'][:12])).resolve()
            if output == bundle or output.is_relative_to(bundle):
                raise ValueError('A seed must be outside the manual image bundle')
            command = [sys.executable, root/'scripts/prepare-xiri-seed.py', bundle, '--output-directory', output]
        else:
            output = args.output.resolve()
            if output == bundle or output.is_relative_to(bundle):
                raise ValueError('A new image must be outside the selected manual bundle')
            if output.exists():
                raise ValueError('Image output already exists; choose a new directory')
            seed = args.seed_run.resolve()
            baseline = (args.baseline or root/manifest['baseline']).resolve()
            pin = read_json(baseline)
            if read_json(seed/'result.json')['pin'] != pin:
                raise ValueError('Seed and baseline pins differ; provide the matching --baseline, --kernel and --iris-bin-dir')
            kernel = (args.kernel or bundle/'tftp/netbsd-XIRI_INDY').resolve()
            emulator = (args.iris_bin_dir or bundle/'emulator').resolve()
            for path, key in [(kernel,'boot_kernel_sha256'), (emulator/'iris','emulator_sha256'),
                              (emulator/'iris-ci','ci_client_sha256')]:
                if sha256(path) != pin[key]:
                    raise ValueError('Build input differs from the seed pin: '+str(path))
            command = [sys.executable, root/'scripts/build-xiri-image.py', '--seed-run', seed,
                       '--output-directory', output, '--baseline', baseline, '--kernel', kernel,
                       '--iris-bin-dir', emulator]
    print(shlex.join([*[key+'='+value for key,value in env.items()], *map(str,command)]), flush=True)
    if args.dry_run:
        if args.action == 'check':
            print('Then qualify the returned run into a new .work/workflows/check-* directory (no promotion).')
        return 0
    if args.action in ('run', 'check'):
        verify_image(root, pointer, bundle, manifest)
    if args.action == 'run':
        os.execv(str(command[0]), list(map(str,command)))
    runs = root/'.work/workflows'
    runs.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.action+'-', dir=runs))
    print('Workflow:', directory, flush=True)
    output = run_step(root, directory, args.action, command, env)
    if args.action == 'check':
        line = next((line[9:] for line in output.splitlines() if line.startswith('Results: ')), None)
        if line is None:
            raise ValueError('Probe did not report a result directory; inspect '+str(directory))
        run_step(root, directory, 'qualify', [sys.executable, root/'scripts/qualify-xiri-image.py', root/line,
                 '--output', directory/'qualification.json', '--png', directory/'desktop.png'])
    print('Completed:', directory)
    return 0


def entrypoint():
    try:
        return main()
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print('xiri:', error, file=sys.stderr)
        return 1
