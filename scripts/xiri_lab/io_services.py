"""Loopback HTTP and TCP endpoints for the NetBSD guest I/O checks."""
import functools
import http.server
import socketserver
import threading


class Services:
    def __init__(self, directory):
        self.directory = directory
        self.http_log = (directory / 'http.log').open('a', buffering=1)
        self.upload_done = threading.Event()
        self.upload_error = None
        owner = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *args):
                owner.http_log.write(fmt % args + '\n')

        class Upload(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    self.request.settimeout(30)
                    with (directory / 'tcp-upload.bin').open('wb') as stream:
                        while chunk := self.request.recv(65536):
                            stream.write(chunk)
                    self.request.sendall(b'XIRI_UPLOAD_RECEIVED\n')
                except OSError as error:
                    owner.upload_error = str(error)
                finally:
                    owner.upload_done.set()

        handler = functools.partial(Handler, directory=directory / 'share')
        self.http = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.upload = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Upload)
        self.upload.daemon_threads = True
        self.threads = []
        for server in [self.http, self.upload]:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        for server in [self.http, self.upload]:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=5)
        self.http_log.close()
