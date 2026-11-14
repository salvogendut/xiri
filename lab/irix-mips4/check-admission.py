#!/usr/bin/env python3
"""Compile the actual module image validator against both donor ELF layouts."""
import argparse
from pathlib import Path
import struct
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--payload-22', required=True, type=Path)
    parser.add_argument('--payload-30', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.read_text()
    start = source.index('enum irix_o32_image_kind {')
    end = source.index('\nstatic int\nirix_o32_runtime_probe(', start)
    validator = source[start:end]
    prefix = r'''
#include <sys/types.h>
#include <elf.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#define PAGE_SIZE 8192U
#define PAGE_MASK (PAGE_SIZE - 1)
#define round_page(x) (((x) + PAGE_MASK) & ~PAGE_MASK)
#define powerof2(x) (((x) & ((x) - 1)) == 0)
#define __arraycount(x) (sizeof(x) / sizeof((x)[0]))
#define IO_NODELOCKED 0
#define CPU_ARCH_MIPS3 (1 << 2)
#define CPU_ARCH_MIPS4 (1 << 3)
struct { unsigned mips_cpu_arch; } mips_options;
struct lwp { int unused; };
struct vnode { Elf32_Phdr *ph; unsigned count; };
static int exec_read(struct lwp *l, struct vnode *v, off_t off,
    void *out, size_t size, int flags) {
    (void)l; (void)flags;
    if (off != sizeof(Elf32_Ehdr) || size != v->count * sizeof(Elf32_Phdr))
        return EIO;
    memcpy(out, v->ph, size);
    return 0;
}
'''
    cases = []
    for release, path in [('22', args.payload_22), ('30', args.payload_30)]:
        with tarfile.open(path) as archive:
            for name, kind in [('bin/sh', 'STATIC'), ('usr/sbin/fftr', 'DYNAMIC'),
                               ('usr/bin/X11/4Dwm', 'DYNAMIC'),
                               ('usr/lib32/libc.so.1', 'INTERPRETER')]:
                data = archive.extractfile('emul/irix/' + name).read()
                values = struct.unpack_from('>16sHHIIIIIHHHHHH', data)
                ident, *header = values
                phoff, phnum = values[5], values[10]
                ph = [struct.unpack_from('>8I', data, phoff + i * 32) for i in range(phnum)]
                for cpu in (3, 4):
                    expected = 0 if cpu == 4 or header[6] >> 28 < 3 else 'ENOEXEC'
                    cases.append((release+'/'+name+'/mips'+str(cpu), ident, header, ph,
                                  len(data), kind, cpu, expected, ''))
                    if release == '30' and kind == 'INTERPRETER' and cpu == 4:
                        for label, mutation in [
                            ('extra-flags', 'eh.e_flags |= 0x100;'),
                            ('wrong-class', 'eh.e_ident[EI_CLASS] = ELFCLASS64;'),
                            ('wrong-endian', 'eh.e_ident[EI_DATA] = ELFDATA2LSB;'),
                            ('writable-text', 'ph[3].p_flags |= PF_W;'),
                        ]:
                            cases.append((label, ident, header, ph, len(data), kind,
                                          cpu, 'ENOEXEC', mutation))
    body = ['int main(void) { int failures = 0;']
    for label, ident, header, ph, length, kind, cpu, expected, mutation in cases:
        init = '{' + ','.join(str(v) for v in ident) + '},' + ','.join(str(v) for v in header)
        rows = ','.join('{' + ','.join(str(v) for v in row) + '}' for row in ph)
        body.append('''{
    Elf32_Ehdr eh = {EH}; Elf32_Phdr ph[] = {ROWS}, loads[2];
    struct vnode vnode = {ph, sizeof(ph) / sizeof(ph[0])};
    mips_options.mips_cpu_arch = CPU_ARCH_MIPSCPU;
    MUTATION
    int got = irix_o32_runtime_image(NULL, &vnode, LENGTH, &eh,
        IRIX_IMAGE_KIND, loads);
    if (got != EXPECTED) {
        printf("FAIL LABEL: got %d, expected %d\\n", got, EXPECTED);
        failures++;
    }
}'''.replace('EH', init).replace('ROWS', rows).replace('CPU;', str(cpu)+';')
            .replace('MUTATION', mutation).replace('LENGTH', str(length))
            .replace('KIND', kind).replace('EXPECTED', str(expected)).replace('LABEL', label))
    body.append('printf("%d failures in '+str(len(cases))+' admission cases\\n", failures); return failures != 0; }')
    with tempfile.TemporaryDirectory(prefix='xiri-mips4-admission-') as tmp:
        root = Path(tmp)
        (root/'check.c').write_text(prefix + validator + '\n' + '\n'.join(body))
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(root/'check.c'), '-o', str(root/'check')], check=True)
        subprocess.run([str(root/'check')], check=True)


if __name__ == '__main__':
    main()
