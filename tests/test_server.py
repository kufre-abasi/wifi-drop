import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from wifi_drop import Handler, RESERVED_PATHS, UPLOADS, WiFiDropServer


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        UPLOADS.clear()
        RESERVED_PATHS.clear()
        self.server = WiFiDropServer(("127.0.0.1", 0), Handler)
        self.server.pin = "123456"
        self.server.output_dir = self.folder
        self.server.verbose = False
        self.server.received_files = []
        self.server.received_files_lock = threading.Lock()
        self.server.shared_files = {}
        self.server.shared_files_lock = threading.Lock()
        self.server.devices = {}
        self.server.devices_lock = threading.Lock()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        result = response.status, dict(response.getheaders()), payload
        connection.close()
        return result

    def json_request(self, method, path, payload):
        body = json.dumps(payload).encode()
        status, headers, response = self.request(method, path, body, {"Content-Type": "application/json", "Content-Length": str(len(body))})
        return status, headers, json.loads(response)

    def test_chunked_upload_preserves_bytes(self):
        source = (b"large-video-block" * 700000)[:10_000_000]
        status, _, started = self.json_request("POST", "/api/start?pin=123456", {"name": "video.mp4", "size": len(source)})
        self.assertEqual(status, 201)
        upload_id = started["id"]
        offset = 0
        for chunk in (source[:4_000_000], source[4_000_000:8_000_000], source[8_000_000:]):
            status, _, response = self.request(
                "PUT",
                f"/api/chunk?pin=123456&id={upload_id}&offset={offset}",
                chunk,
                {"Content-Length": str(len(chunk)), "Content-Type": "application/octet-stream"},
            )
            self.assertEqual(status, 200, response)
            offset += len(chunk)
        status, _, finished = self.json_request("POST", f"/api/finish?pin=123456&id={upload_id}", {})
        self.assertEqual(status, 201)
        saved = self.folder / finished["name"]
        self.assertEqual(hashlib.sha256(saved.read_bytes()).digest(), hashlib.sha256(source).digest())

    def test_private_apis_require_pin(self):
        status, _, _ = self.request("GET", "/api/files")
        self.assertEqual(status, 404)
        status, _, _ = self.request("POST", "/api/start", b"{}", {"Content-Length": "2"})
        self.assertEqual(status, 403)

    def test_explicitly_shared_file_supports_ranges(self):
        shared = self.folder / "shared.mov"
        shared.write_bytes(b"0123456789")
        self.server.shared_files["file-id"] = {"path": shared, "target": None}
        status, headers, payload = self.request("GET", "/download?pin=123456&id=file-id", headers={"Range": "bytes=3-6"})
        self.assertEqual(status, 206)
        self.assertEqual(headers["Content-Range"], "bytes 3-6/10")
        self.assertEqual(payload, b"3456")

    def test_registered_devices_only_receive_their_targeted_files(self):
        status, _, registered = self.json_request(
            "POST",
            "/api/device/register?pin=123456",
            {"id": "phone-a", "name": "Anthony's phone"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(registered["name"], "Anthony's phone")
        first = self.folder / "for-a.mp4"
        second = self.folder / "for-b.mp4"
        first.write_bytes(b"a")
        second.write_bytes(b"b")
        self.server.shared_files["first"] = {"path": first, "target": "phone-a"}
        self.server.shared_files["second"] = {"path": second, "target": "phone-b"}

        status, _, payload = self.request("GET", "/api/shared?pin=123456&device=phone-a")
        self.assertEqual(status, 200)
        files = json.loads(payload)["files"]
        self.assertEqual([item["name"] for item in files], ["for-a.mp4"])

        status, _, _ = self.request("GET", "/download?pin=123456&id=first&device=phone-b")
        self.assertEqual(status, 404)
        status, _, payload = self.request("GET", "/download?pin=123456&id=first&device=phone-a")
        self.assertEqual(status, 200)
        self.assertEqual(payload, b"a")


if __name__ == "__main__":
    unittest.main()
