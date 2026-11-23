"""Native packaging boundaries and prerequisites, without a prepared image."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from xiri_lab import ROOT, sha256
from xiri_lab.native_package import archive_tree, build, ledger, pins, prerequisites, rooted


class NativePackageTests(unittest.TestCase):
    def test_clean_indy_supplies_toolchest_menu(self):
        profile = json.loads((ROOT/'profiles/netbsd-sgimips-indy-11.99.11-v1.json').read_text())
        menu = '/usr/local/share/xiri/toolchest.chestrc'
        self.assertIn(menu, (ROOT/'runtime/libexec/desktop-clients.sh').read_text())
        contents = (ROOT/profile['configuration_sources'][menu]).read_text()
        self.assertIn('include /usr/lib/X11/system.chestrc', contents)
        self.assertIn('/usr/local/bin/xiri-logout', contents)

    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def test_rooted_absolute_links_and_parent_resolution(self):
        (self.root/'lib').mkdir();(self.root/'usr/lib').mkdir(parents=True)
        (self.root/'lib/c.so.1').write_bytes(b'target library')
        (self.root/'usr/lib/c.so').symlink_to('/lib/c.so.1')
        self.assertEqual(rooted(self.root,'/usr/lib/c.so'),self.root/'lib/c.so.1')
        (self.root/'usr/lib/c.so.2').symlink_to('../../lib/c.so.1')
        self.assertEqual(rooted(self.root,'/usr/lib/c.so.2'),self.root/'lib/c.so.1')
        (self.root/'loop').symlink_to('/loop')
        with self.assertRaisesRegex(ValueError,'loop'):rooted(self.root,'/loop')
        (self.root/'outside').symlink_to('../../etc/passwd')
        with self.assertRaisesRegex(ValueError,'escapes'):rooted(self.root,'/outside')

    def test_native_pins_reject_mixed_kernel_module_and_modified_sets(self):
        module=self.root/'module';module.write_bytes(b'module paired with kernel')
        cc=self.root/'cc';cc.write_bytes(b'compiler')
        dist=self.root/'base.tgz';dist.write_bytes(b'pinned distribution')
        sums=self.root/'sums';sums.write_text(hashlib.sha512(dist.read_bytes()).hexdigest()+'  sgimips/binary/sets/base.tgz\n')
        profile=dict(schema=1,artifacts={'module':dict(destination='/stand/module',sha256=sha256(module),provenance={})},
                     compiler_sha256=sha256(cc),sets_manifest=dict(path='sums',sha256=sha256(sums)),
                     target_sets=['base.tgz'],build_sets=[])
        with patch('xiri_lab.native_package.ROOT',self.root):
            self.assertEqual(len(pins(profile,{'module':module},cc,self.root)),1)
            module.write_bytes(b'different module')
            with self.assertRaisesRegex(ValueError,'artifact mismatch'):pins(profile,{'module':module},cc,self.root)
            module.write_bytes(b'module paired with kernel');dist.write_bytes(b'wrong set')
            with self.assertRaisesRegex(ValueError,'set mismatch'):pins(profile,{'module':module},cc,self.root)

    def test_missing_native_libraries_stop_packaging(self):
        (self.root/'bin').mkdir();app=self.root/'bin/app';app.write_bytes(b'\x7fELF app')
        (self.root/'lib').mkdir()
        def elf(p):return dict(abi='o32',interpreter=[],rpath=[],needed=['libtest.so.1'] if p==app else [])
        with patch('xiri_lab.native_package.elf_parser',return_value=elf):
            with self.assertRaisesRegex(ValueError,'Unresolved native library'):prerequisites(self.root,{},['/bin/app'],[])
            lib=self.root/'lib/libtest.so.1';lib.write_bytes(b'\x7fELF library')
            required,edges=prerequisites(self.root,{},['/bin/app'],[])
            self.assertEqual(required['/lib/libtest.so.1']['sha256'],sha256(lib))
            self.assertEqual(edges,[dict(source='/bin/app',needed='libtest.so.1',selected='/lib/libtest.so.1')])

    def test_archive_reproducibility_and_separate_kernel_configuration(self):
        stage=self.root/'stage';(stage/'kernel').mkdir(parents=True)
        (stage/'kernel/netbsd').write_bytes(b'kernel');(stage/'kernel/netbsd').chmod(0o555)
        (stage/'root/etc/xiri').mkdir(parents=True)
        config=stage/'root/etc/xiri/session.conf';config.write_bytes(b'defaults');config.chmod(0o644)
        example=stage/'root/etc/xiri/session.conf.example';example.write_bytes(b'defaults');example.chmod(0o444)
        (stage/'root/shell').symlink_to('/bin/sh')
        rows=ledger(stage)
        self.assertEqual(rows['kernel/netbsd']['policy'],'separate-kernel-activation')
        self.assertEqual(rows['root/etc/xiri/session.conf']['policy'],'preserve-config')
        self.assertEqual(rows['root/etc/xiri/session.conf.example']['policy'],'replace-owned-file')
        a=self.root/'a.tgz';b=self.root/'b.tgz';archive_tree(stage,a)
        os.utime(config,(12345,67890));archive_tree(stage,b)
        self.assertEqual(a.read_bytes(),b.read_bytes())
        with tarfile.open(a) as archive:
            self.assertEqual(archive.getmember('root/shell').linkname,'/bin/sh')
            self.assertEqual(archive.getmember('kernel/netbsd').mode,0o555)
            self.assertTrue(all(m.uid==m.gid==m.mtime==0 for m in archive))

    def test_failed_compilation_cleans_scratch_and_publishes_no_package(self):
        profile=self.root/'profile.json';profile.write_text('{"configuration_sources":{}}')
        inputs=self.root/'inputs.json';inputs.write_text('{}')
        cc=self.root/'cc';cc.touch();out=self.root/'output'
        with patch('xiri_lab.native_package.pins',return_value={'base.tgz':'pin'}), \
             patch('xiri_lab.native_package.subprocess.run',side_effect=RuntimeError('compile failed')):
            with self.assertRaisesRegex(RuntimeError,'compile failed'):build(profile,inputs,cc,self.root,out)
        self.assertEqual([p.name for p in out.iterdir()],['build.log'])


if __name__=='__main__':unittest.main()
