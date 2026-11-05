"""Collect large diagnostic archives through the lab's loopback NAT gateway."""
import hashlib
import socket
import threading
import time
import uuid
from pathlib import Path


def archive(guest, command, destination, timeout=180):
    """Run an archive producer and verify its guest SHA256 after TCP upload.

    This requires the existing 192.168.231.0/24 diagnostic NAT configuration.
    The listener is local, bounded and serves no host files. Publish the local
    artifact only after EOF, the guest command and the digest all agree.
    """
    destination = Path(destination)
    temporary = destination.with_name(destination.name + '.partial')
    remote = '/tmp/xiri-transfer-' + uuid.uuid4().hex
    stopped = threading.Event()
    errors = []
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        server.settimeout(.5)
        deadline = time.monotonic() + timeout

        def receive():
            try:
                while not stopped.is_set():
                    if time.monotonic() >= deadline:
                        raise TimeoutError('archive connection deadline')
                    try:
                        conn, _ = server.accept()
                        break
                    except socket.timeout:
                        continue
                else:
                    return
                with conn, temporary.open('wb') as output:
                    conn.settimeout(.5)
                    while not stopped.is_set():
                        if time.monotonic() >= deadline:
                            raise TimeoutError('archive receive deadline')
                        try:
                            chunk = conn.recv(65536)
                        except socket.timeout:
                            continue
                        if not chunk:
                            return
                        output.write(chunk)
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=receive, daemon=True)
        thread.start()
        try:
            guest.command('(' + command + ') >' + remote +
                          ' && sha256 -q ' + remote + ' >' + remote + '.sha256'
                          ' && nc -N -w 60 192.168.231.1 ' +
                          str(server.getsockname()[1]) + ' <' + remote, timeout)
            thread.join(max(0, deadline - time.monotonic()))
            if thread.is_alive():
                raise TimeoutError('archive receiver did not finish')
            if errors:
                raise errors[0]
            with temporary.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            expected = guest.read_text('cat ' + remote + '.sha256', 30).strip()
            if digest != expected:
                raise ValueError('guest archive SHA256 mismatch')
            temporary.replace(destination)
            guest.command('rm -f ' + remote + ' ' + remote + '.sha256', 30)
            return digest
        finally:
            stopped.set()
            thread.join(2)
