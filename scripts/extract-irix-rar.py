#!/usr/bin/env python3
"""Extract the pinned user-provided IRIX system archive into the ignored lab."""

import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / '.work/irix-reference/media')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    expected = manifest['chd']
    destination = args.output / expected['name']
    temporary = destination.with_suffix('.chd.partial')
    if destination.exists() or temporary.exists():
        parser.error('output or partial output already exists; use an unused output directory')
    with args.archive.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive_pin = next(x for x in manifest['archives'] if x['name'] == 'irix65_chd.rar')
    if sha != archive_pin['sha256']:
        parser.error('archive hash differs from the recorded reference image')
    library = ctypes.util.find_library('archive')
    if not library:
        parser.error('libarchive with RAR5 support is required')
    lib = C.CDLL(library)
    for name, ret, params in [
        ('archive_read_new', C.c_void_p, []),
        ('archive_read_support_format_all', C.c_int, [C.c_void_p]),
        ('archive_read_support_filter_all', C.c_int, [C.c_void_p]),
        ('archive_read_open_filename', C.c_int, [C.c_void_p, C.c_char_p, C.c_size_t]),
        ('archive_read_next_header', C.c_int, [C.c_void_p, C.POINTER(C.c_void_p)]),
        ('archive_read_data', C.c_ssize_t, [C.c_void_p, C.c_void_p, C.c_size_t]),
        ('archive_read_free', C.c_int, [C.c_void_p]),
        ('archive_entry_pathname', C.c_char_p, [C.c_void_p]),
        ('archive_entry_filetype', C.c_uint, [C.c_void_p]),
        ('archive_entry_size', C.c_int64, [C.c_void_p]),
        ('archive_error_string', C.c_char_p, [C.c_void_p]),
    ]:
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = ret, params
    archive = lib.archive_read_new()

    def check(code):
        if code < 0:
            raise RuntimeError(lib.archive_error_string(archive))
        return code

    try:
        check(lib.archive_read_support_format_all(archive))
        check(lib.archive_read_support_filter_all(archive))
        check(lib.archive_read_open_filename(archive, bytes(args.archive), 1024 * 1024))
        entry = C.c_void_p()
        if check(lib.archive_read_next_header(archive, C.byref(entry))) != 0:
            raise RuntimeError('archive has no system image')
        if (lib.archive_entry_pathname(entry) != expected['name'].encode() or
                lib.archive_entry_filetype(entry) != 0o100000 or
                lib.archive_entry_size(entry) != expected['bytes']):
            raise RuntimeError('unexpected archive member, type, or size')
        args.output.mkdir(parents=True, exist_ok=True)
        buffer = C.create_string_buffer(1024 * 1024)
        written, progress = 0, 0
        digest = hashlib.sha256()
        with temporary.open('xb') as out:
            while True:
                n = check(lib.archive_read_data(archive, buffer, len(buffer)))
                if not n:
                    break
                written += n
                if written > expected['bytes']:
                    raise RuntimeError('member exceeds declared size')
                block = buffer.raw[:n]
                out.write(block)
                digest.update(block)
                if written - progress >= 256 * 1024**2:
                    print(f'{written}/{expected["bytes"]} bytes', flush=True)
                    progress = written
        if check(lib.archive_read_next_header(archive, C.byref(entry))) != 1:
            raise RuntimeError('unexpected extra archive member')
        if written != expected['bytes'] or digest.hexdigest() != expected['sha256']:
            raise RuntimeError('extracted image size or hash mismatch')
        temporary.rename(destination)
        print(f'Verified {destination}', flush=True)
    finally:
        lib.archive_read_free(archive)


if __name__ == '__main__':
    main()
