"""Read the same wrapped NetBSD message ring with the stock and Xiri kernel ABIs."""

from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab.kernel_log import KernelLog


class KernelLogTests(unittest.TestCase):
    def test_pointer_width_and_wrapped_contents(self):
        # A 32-bit guest signs KSEG pointers into the monitor's address space.
        # The 64-bit guest stores an XKPHYS pointer, read via its KSEG0 alias after halt.
        for width, pointer in [(4, 0x88002000), (8, 0x9800000008002000)]:
            with self.subTest(width=width):
                symbol = 0xFFFFFFFF88001000
                buffer = 0xFFFFFFFF88002000
                memory = {symbol: pointer}
                data = b'orldhello w'
                for index, value in enumerate((0x63061, 4, 0, len(data))):
                    memory[buffer + index * width] = value
                for offset in range(0, len(data), width):
                    chunk = data[offset : offset + width].ljust(width, b'\0')
                    memory[buffer + 4 * width + offset] = int.from_bytes(chunk, 'big')
                commands = []

                def monitor(command):
                    commands.append(command)
                    if command in ('stop', 'start'):
                        return ''
                    op, addr, count, unit = command.split()
                    self.assertEqual((op, unit), ('mem', 'w' if width == 4 else 'd'))
                    addresses = (int(addr, 16) + width * i for i in range(int(count)))
                    return ''.join(f'0x{a:x}: 0x{memory[a]:x}\n' for a in addresses)

                lab = SimpleNamespace(monitor_command=monitor)
                guest_symbol = symbol & ((1 << (width * 8)) - 1)
                self.assertEqual(KernelLog(lab, guest_symbol, width).read(), 'hello world')
                self.assertEqual((commands[0], commands[-1]), ('stop', 'start'))
