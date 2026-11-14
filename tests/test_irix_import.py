"""Import boundaries, dependency completeness and reproducible vendor archives."""
import copy
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from xiri_lab import sha256
from xiri_lab.irix_import import (CATALOG, PREFIX, build, check_source, collect,
                                  selection, validate_parents, write_payload)
from xiri_lab.workflow import main


class FakeDonor:
    def __init__(self, files):
        self.files = files

    def info(self, path):
        if path not in self.files:
            raise ValueError('Missing required donor path: '+path)
        value = self.files[path]
        return dict(source_type='symlink', source_target=value, source_mode='0o755') \
            if isinstance(value, str) else dict(source_type='file', source_mode='0o644')

    def isfile(self, path):
        value = self.files.get(path)
        return isinstance(value, bytes) or isinstance(value, str) and self.isfile(value)

    def call(self, command, path, *args):
        if command == 'realpath':
            return self.files[path] if isinstance(self.files[path], str) else path
        if command == 'download':
            real = self.call('realpath', path)
            Path(args[0]).write_bytes(self.files[real])
        else:
            raise AssertionError(command)


class ImportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.profile = dict(schema=1, id='test-v1', release='test',
                            default_components=['desktop'], components={
                                'desktop': dict(available=True),
                                'missing': dict(available=False, reason='not installed')},
                            paths={'/bin/sh':dict(component='desktop', type='file')},
                            native_prerequisites=[])

    def rows(self, paths):
        return {PREFIX+p:dict(source=p, type='file', component='desktop') for p in paths}

    def test_component_and_destination_rejections(self):
        with self.assertRaisesRegex(ValueError, 'not installed'):
            selection(self.profile, ['missing'])
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            selection(self.profile, ['unknown'])
        for dest in ['/etc/passwd', '/emul/irix/../etc/passwd', '//emul/irix/bin/sh']:
            profile = copy.deepcopy(self.profile)
            profile['paths']['/bin/sh']['destination'] = dest
            with self.subTest(dest=dest), self.assertRaises(ValueError):
                selection(profile)
        self.profile['paths']['/sbin/sh'] = dict(component='desktop', type='file', destination=PREFIX+'/bin/sh')
        with self.assertRaisesRegex(ValueError, 'Conflicting destination'):
            selection(self.profile)

    def test_link_parents_rejected(self):
        rows = {PREFIX+'/usr/lib':dict(type='symlink', target='/tmp'),
                PREFIX+'/usr/lib/file':dict(type='file')}
        with self.assertRaisesRegex(ValueError, 'non-directory parent'):
            validate_parents(rows)

    def test_donor_hash_and_unmerged_overlays_rejected(self):
        raw = self.root/'donor.raw'
        raw.write_bytes(b'original')
        self.profile['donor'] = dict(raw_sha256=sha256(raw))
        self.assertEqual(check_source(raw, self.profile)[1], 'raw')
        overlay = Path(str(raw)+'.overlay')
        overlay.write_bytes(b'changes')
        with self.assertRaisesRegex(ValueError, 'standalone donor'):
            check_source(raw, self.profile)
        overlay.unlink()
        raw.write_bytes(b'wrong version')
        with self.assertRaisesRegex(ValueError, 'hash does not match'):
            check_source(raw, self.profile)

    def test_required_file_and_library_missing(self):
        with self.assertRaisesRegex(ValueError, 'Missing required donor'):
            collect(FakeDonor({}), self.rows(['/bin/sh']), self.root)
        elf = dict(machine=8, abi='n32', interpreter=[], rpath=[], needed=['libmissing.so'])
        elf.update({'class':32, 'endian':'big'})
        with self.assertRaisesRegex(ValueError, 'Missing ELF dependency'):
            collect(FakeDonor({'/bin/sh':b'\x7fELFfake'}), self.rows(['/bin/sh']), self.root, lambda _:elf)

    def test_closure_canonical_alias_catalog_and_determinism(self):
        files = {'/bin/sh':b'\x7fELFmain', '/usr/lib32/libc.so': '/lib32/libc.so',
                 '/lib32/libc.so':b'library', '/usr/sbin/app':b'#!/bin/sh\nexit 0\n',
                 CATALOG+'C/Apps/Available':'/usr/sbin/app',
                 CATALOG+'C/Apps/Absent':'/usr/freeware/bin/absent'}
        rows = self.rows(['/bin/sh','/usr/sbin/app'])
        for p,v in files.items():
            if p.startswith(CATALOG):
                rows[PREFIX+p] = dict(source=p,type='symlink',target=v,component='desktop')
        elf = dict(machine=8,abi='n32',interpreter=[],rpath=[],needed=['libc.so'])
        elf.update({'class':32,'endian':'big'})
        complete, deps, omitted = collect(FakeDonor(files),rows,self.root,lambda _:elf)
        self.assertIn(PREFIX+'/usr/lib32/libc.so', complete)
        self.assertIn(PREFIX+'/lib32/libc.so', complete)
        self.assertEqual(deps[0]['selected'], '/usr/lib32/libc.so')
        self.assertEqual(len(omitted),1)
        a,b = self.root/'a.tar.gz',self.root/'b.tar.gz'
        write_payload(a,complete)
        write_payload(b,dict(reversed(list(complete.items()))))
        self.assertEqual(a.read_bytes(),b.read_bytes())
        with tarfile.open(a) as tar:
            lib = tar.getmember('emul/irix/usr/lib32/libc.so')
            self.assertTrue(lib.isfile())
            self.assertEqual(tar.extractfile(lib).read(),b'library')
            self.assertEqual(tar.getmember('emul/irix/bin/sh').mode,0o555)
            self.assertFalse(any('Absent' in n for n in tar.getnames()))

    def test_data_makefile_and_scoped_launcher_libraries(self):
        files = {'/usr/lib/filetype/Makefile':b'#!smake\nall:\n',
                 '/usr/adobe/bin/app':b'\x7fELFmain',
                 '/usr/adobe/lib/libprivate.so':b'library'}
        elf = dict(machine=8,abi='o32',interpreter=[],rpath=[],needed=['libprivate.so'])
        elf.update({'class':32,'endian':'big'})
        complete,deps,_ = collect(FakeDonor(files),self.rows(list(files)[:2]),self.root,
                                  lambda _:elf,{'/usr/adobe/':['/usr/adobe/lib']})
        self.assertNotIn('interpreter',complete[PREFIX+'/usr/lib/filetype/Makefile'])
        self.assertEqual(deps[0]['selected'],'/usr/adobe/lib/libprivate.so')

    def test_failed_import_cleans_temporary_files_without_publishing(self):
        raw = self.root/'donor.raw'
        raw.write_bytes(b'original')
        self.profile['donor'] = dict(raw_sha256=sha256(raw))
        profile = self.root/'profile.json'
        profile.write_text(json.dumps(self.profile))
        output = self.root/'out'
        with patch('xiri_lab.irix_import.Donor.__enter__', side_effect=RuntimeError('unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                build(profile,raw,output)
        self.assertEqual(list(output.iterdir()),[])
        self.assertEqual(raw.read_bytes(),b'original')

    def test_import_does_not_require_a_selected_netbsd_image(self):
        profile = self.root/'profile.json'
        profile.write_text(json.dumps(self.profile))
        with patch('xiri_lab.workflow.selected_image',side_effect=AssertionError('old image accessed')):
            self.assertEqual(main(['import','--profile',str(profile),'--source','donor.chd',
                                   '--output','new','--dry-run']),0)


if __name__ == '__main__':
    unittest.main()
