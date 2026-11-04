#!/usr/bin/env python3
"""Build the IRIX exec module against an existing isolated N64 kernel build."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from xiri_lab import ROOT, sha256


def output(*command):
    return subprocess.check_output(command, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT/'.work/netbsd-module-build')
    parser.add_argument('--jobs', type=int, default=2, choices=(1, 2))
    args = parser.parse_args()
    build = args.build.resolve()
    source = Path((build/'source-path').read_text().strip())
    assert (build/'build-arch').read_text().strip() == 'mips64eb'
    make = build/'tools/bin/nbmake-sgimips'
    directory = source/'sys/modules/compat_irix_o32'
    with (build/'module-build.log').open('w') as log:
        for targets in [('obj',), ('-j', str(args.jobs), 'all')]:
            subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', str(make), '-C', str(directory), *targets],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    module = build/'obj/sys/modules/compat_irix_o32/compat_irix_o32.kmod'
    kernel = build/'kernel-media/netbsd'
    undefined = sorted({line.split()[-1] for line in output('nm', '-u', str(module)).splitlines()})
    defined = {line.split()[-1] for line in output('nm', '--defined-only', str(kernel)).splitlines()}
    assert not set(undefined)-defined, sorted(set(undefined)-defined)
    assert not any(name.startswith(('irix_', 'emul_irix', 'compat_irix_')) for name in defined)
    relocations = sorted(set(re.findall(r'R_MIPS_\w+', output('readelf', '-rW', str(module)))))
    supported = {'R_MIPS_'+name for name in ('NONE', '32', '26', 'HI16', 'LO16', '64', 'HIGHER', 'HIGHEST')}
    assert set(relocations) <= supported, relocations
    config = ROOT/'lab/irix-module/XIRI_IRIX_MODULE'
    config_dir = build/'obj/sys/arch/sgimips/compile'/config.name
    assert not re.search(r'^#define\s+COMPAT_IRIX_O32\b', (config_dir/'opt_compat_irix_o32.h').read_text(), re.M)
    assert re.search(r'^#define\s+MODULAR\b', (config_dir/'opt_modular.h').read_text(), re.M)
    paths = [str(path.relative_to(source)) for path in sorted((source/'sys/compat/irix_o32').glob('*.[ch]'))]
    paths += ['sys/modules/compat_irix_o32/Makefile', 'sys/modules/Makefile',
              'sys/arch/mips/conf/files.mips',
              'sys/arch/mips/mips/kobj_machdep.c', 'sys/kern/sys_select.c',
              'sys/kern/kern_lwp.c', 'sys/sys/proc.h', 'sys/uvm/uvm_pglist.c']
    result = dict(schema=1, status='built', source=str(source),
                  source_revision=output('git', '-C', str(source), 'rev-parse', 'HEAD').strip(),
                  source_status=output('git', '-C', str(source), 'status', '--short'),
                  source_files={name:sha256(source/name) for name in paths},
                  config_path=str(config.relative_to(ROOT)), config_sha256=sha256(config),
                  sources={'scripts/build-irix-module.py':sha256(Path(__file__))},
                  undefined_symbols=undefined, relocation_types=relocations,
                  core_hooks=['selcommon_kern', 'emul.e_sigmask'], artifacts={})
    for name, path in [('compat_irix_o32.kmod', module), ('netbsd', kernel),
                       ('netbsd.boot', build/'tftp/netbsd-XIRI_INDY')]:
        result['artifacts'][name] = dict(path=str(path.relative_to(build)), sha256=sha256(path))
    result['debug_kernel_sha256'] = sha256(config_dir/'netbsd.gdb')
    (build/'module.json').write_text(json.dumps(result, indent=2)+'\n')
    print(build/'module.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
