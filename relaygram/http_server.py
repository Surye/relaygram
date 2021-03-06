import http.server
from threading import Thread
import os.path
import mimetypes

class HTTPHandler:
    def __init__(self, config):
        self.config = config

        handler = HTTPHandler.make_http_handler(self.config['media_dir'])
        self.httpd = http.server.HTTPServer(('', self.config['media']['port']), handler)

        self.thread = Thread(target=self.main_loop)

    def run(self):
        self.thread.start()
        return self

    def main_loop(self):
        self.httpd.serve_forever()

    @staticmethod
    def make_http_handler(root_path):
        class RelayGramHTTPHandler(http.server.BaseHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super(RelayGramHTTPHandler, self).__init__(*args, **kwargs)

            def do_GET(self):
                file_path = os.path.abspath(root_path + self.path)

                if os.path.commonprefix([root_path, file_path]) != os.path.abspath(root_path):  # Detect path traversal attempt
                    self.send_error(501, "Nice try")
                else:
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        self.send_error(404, 'File Not Found')
                    else:
                        mimetype = mimetypes.guess_type(file_path)

                        self.send_response(200)
                        if mimetype[0]:
                            self.send_header('Content-Type', mimetype[0])
                        self.send_header('Content-Length', os.path.getsize(file_path))
                        self.end_headers()
                        self.wfile.write(open(file_path, mode='rb').read())

        return RelayGramHTTPHandler
