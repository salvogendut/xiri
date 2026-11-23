"""Read NetBSD's message ring and verify halt when the console is graphical.

The address must come from the matching, hash-verified kernel symbols.
"""
import re
import time


class KernelLog:
    def __init__(self, lab, address, word_bytes=8):
        if word_bytes not in (4, 8):
            raise ValueError('unsupported kernel long size')
        self.lab=lab
        self.address=address
        self.word_bytes=word_bytes

    def read(self):
        self.lab.monitor_command('stop')
        try:
            def words(address,count):
                if self.word_bytes == 4:
                    # Indy kernel pointers are sign-extended KSEG addresses.
                    address |= 0xffffffff00000000
                unit='w' if self.word_bytes == 4 else 'd'
                out=self.lab.monitor_command(f'mem 0x{address:x} {count} {unit}')
                values=[int(v,16) for v in re.findall(r'^0x[0-9a-f]+: (0x[0-9a-f]+)',out,re.M)]
                if len(values)!=count:raise RuntimeError('Short kernel memory read: '+out[:300])
                return values
            address=words(self.address,1)[0]
            # PROM clears KX after halt; access the equivalent KSEG0 RAM alias.
            if address>>62==2:
                physical=address&((1<<59)-1)
                assert physical<0x20000000
                address=0xffffffff80000000|physical
            magic,write,read,size=words(address,4)
            assert magic==0x63061 and 0<=write<size<=131072
            data=b''
            for offset in range(0,size,2048):
                width=self.word_bytes
                values=words(address+4*width+offset,(min(2048,size-offset)+width-1)//width)
                data+=b''.join(value.to_bytes(width,'big') for value in values)
            data=data[:size]
            return (data[write:]+data[:write]).replace(b'\0',b'').decode(errors='backslashreplace')
        finally:
            self.lab.monitor_command('start')

    def halt(self):
        before=self.read()
        self.lab.send('shutdown -h now')
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            # Reading the ring pauses the guest. Leave enough uninterrupted
            # execution for rc shutdown hooks and their guest-clock deadlines.
            time.sleep(10)
            after=self.read()
            (self.lab.directory/'shutdown-dmesg.txt').write_text(after)
            if after!=before and 'unmounting done' in after[-2048:] and 'halting...' in after[-256:]:
                self.lab.logged_in=False
                self.lab.clean_shutdown=True
                return after
        raise RuntimeError('Graphical halt did not record clean unmount and halt')
