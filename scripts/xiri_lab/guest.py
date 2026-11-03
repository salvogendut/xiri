"""Paced guest commands, evidence transfer and framebuffer captures."""
import gzip
import re
import time
import uuid


class Guest:
    def __init__(self, lab, *, pace_seconds=.02):
        self.lab = lab
        if lab.args.mode == 'ordinary':
            # X/serial interrupt latency can drop even a single quote at 5 ms.
            # Leave 20 ms between bytes, including multi-line shell arguments.
            def paced_send(text, newline=True):
                data = (text + ('\r' if newline else '')).encode('ascii')
                for byte in data:
                    lab.serial.sendall(bytes([byte]))
                    time.sleep(pace_seconds)
            lab.send = paced_send

    def command(self, command, timeout=120):
        before = len(self.lab.serial_text())
        code = self.lab.command(command, timeout)
        output = self.lab.serial_text()[before:]
        if code:
            raise RuntimeError(f'guest command failed ({code}): {command}\n{output[-2000:]}')
        return output

    def read(self, command, timeout=240):
        """Read command output as bytes; use command() to enforce its exit code.

        Pipeline exit semantics match the existing diagnostic readers, including
        grep/ps queries where an empty result is expected and checked by callers.
        """
        token = uuid.uuid4().hex
        begin, end = 'BEGIN_'+token, 'END_'+token
        output = self.command(
            "printf '\\n"+begin+"\\n'; { "+command+
            "; } 2>transfer.err | gzip -c | od -An -v -tx1; printf '"+end+"\\n'", timeout)
        match = re.search(r'^'+begin+r'\n([0-9a-f \n]+)^'+end+r'$', output, re.M)
        if not match:
            raise RuntimeError('missing or malformed guest transfer frame')
        try:
            return gzip.decompress(bytes.fromhex(match[1]))
        except (ValueError, OSError, EOFError) as error:
            raise RuntimeError('corrupt guest transfer payload') from error

    def read_text(self, command, timeout=240):
        return self.read(command, timeout).decode(errors='backslashreplace')

    def monitor(self, command):
        output = self.lab.monitor_command(command)
        with (self.lab.directory/'monitor.log').open('a') as stream:
            stream.write(command+'\n'+output+'\n')
        if any(word in output.lower() for word in ('error:', 'unknown command', 'timed out')):
            raise RuntimeError(f'monitor command failed: {command}: {output}')
        return output

    def capture(self, path):
        self.monitor('disp compositor gl')
        self.monitor('disp compositor sw')
        self.monitor('screen wait 500 10000')
        self.monitor('screen shot '+str(path))
        if path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise RuntimeError('framebuffer capture is not a PNG: '+str(path))

    def wait_for(self, condition, timeout=180):
        self.command('(tries=0; until '+condition+'; do tries=$((tries+1)); '
                     'test "$tries" -lt '+str(max(1, timeout//2))+
                     ' || exit 1; sleep 2; done)', timeout+20)
