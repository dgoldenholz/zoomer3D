"""Preview the static site with byte-range support for MP4 seeking."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import re


class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        range_value = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not range_value or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_value)
        if not match or not any(match.groups()):
            return super().send_head()
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        file = path.open("rb")
        file.seek(start)
        self.remaining = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(self.remaining))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(path.stat().st_mtime))
        self.end_headers()
        return file

    def copyfile(self, source, output):
        if self.remaining is None:
            return super().copyfile(source, output)
        remaining = self.remaining
        while remaining:
            block = source.read(min(64 * 1024, remaining))
            if not block:
                break
            output.write(block)
            remaining -= len(block)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8794)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "docs")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_dir():
        parser.error(f"Directory does not exist: {directory}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(RangeHandler, directory=str(directory)))
    print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
