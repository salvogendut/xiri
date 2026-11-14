#!/usr/bin/env python3
"""Exercise the R10K secondary-cache alignment macros from NetBSD source."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
args = parser.parse_args()
source = args.source.read_text().replace('\\\n', '')
macros = '\n'.join(re.findall(r'^#define\s+(?:round_line|trunc_line)\(x\).*mci_sdcache_line_size.*$', source, re.M))
assert len(macros.splitlines()) == 2
for bits in (32, 64):
    program = '''#include <assert.h>
#include <stdint.h>
typedef uintBITS_t register_t;
typedef register_t vaddr_t;
typedef register_t vsize_t;
struct cache_info { unsigned mci_sdcache_line_size; } info, *mci = &info;
MACROS
int main(void) {
    const uint64_t bases[] = {0x80000000, 0xffffffff80000000ULL,
        0x9800000000000000ULL, 0xc000000010000000ULL};
    for (unsigned i = 0; i < sizeof bases / sizeof bases[0]; i++) {
        for (unsigned line = 64; line <= 128; line *= 2) {
            mci->mci_sdcache_line_size = line;
            register_t base = (register_t)bases[i];
            for (unsigned offset = 0; offset < 2 * line; offset++) {
                register_t va = base + offset;
                assert(trunc_line(va) == base + (offset / line) * line);
                assert(round_line(va) == base + ((offset + line - 1) / line) * line);
            }
        }
    }
}
'''.replace('BITS', str(bits)).replace('MACROS', macros)
    with tempfile.TemporaryDirectory(prefix='xiri-cache-alignment-') as tmp:
        path = Path(tmp)
        (path/'test.c').write_text(program)
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(path/'test.c'), '-o', str(path/'test')], check=True)
        subprocess.run([str(path/'test')], check=True)
    print(str(bits)+'-bit address alignment passed')
