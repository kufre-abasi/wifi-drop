#!/usr/bin/env python3
"""WiFi Drop: receive large files from a phone over the local network."""

import argparse
import html
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_NAME = "WiFi Drop"
CHUNK_SIZE = 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024 * 1024
MAX_CHUNK_BYTES = 16 * 1024 * 1024
RESERVED_PATHS = set()
RESERVATION_LOCK = threading.Lock()
UPLOADS = {}
UPLOADS_LOCK = threading.Lock()


HTML_PAGE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#f5f1e8">
  <title>WiFi Drop</title>
  <style>
    :root { color-scheme: light; --ink:#17211b; --muted:#647069; --paper:#f5f1e8; --card:#fffdf8; --line:#d9d5ca; --green:#176b4a; --green2:#0d5137; --soft:#dfeee5; --red:#9e3434; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; background:radial-gradient(circle at 15% 0%,#fffdf6 0,transparent 38%),var(--paper); color:var(--ink); font-family:ui-rounded,"SF Pro Rounded","Avenir Next",system-ui,sans-serif; }
    .shell { width:min(100% - 28px,680px); margin:0 auto; padding:34px 0 calc(36px + env(safe-area-inset-bottom)); }
    header { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:26px; }
    .brand { font-weight:850; letter-spacing:-.04em; font-size:22px; }
    .status { display:flex; align-items:center; gap:7px; color:var(--green); font-size:13px; font-weight:750; }
    .dot { width:8px; height:8px; border-radius:50%; background:#26a66f; box-shadow:0 0 0 4px #d8eee3; }
    .hero { margin:16px 0 24px; }
    h1 { max-width:540px; margin:0 0 10px; font-size:clamp(34px,8vw,58px); line-height:.96; letter-spacing:-.055em; }
    .lede { max-width:520px; margin:0; color:var(--muted); font-size:16px; line-height:1.55; }
    .drop { position:relative; display:block; margin:28px 0 14px; padding:34px 22px; text-align:center; border:2px dashed #98aa9f; border-radius:24px; background:rgba(255,253,248,.74); cursor:pointer; transition:.18s ease; }
    .drop:hover,.drop.drag { border-color:var(--green); background:var(--soft); transform:translateY(-1px); }
    .drop input { position:absolute; inset:0; width:100%; height:100%; opacity:0; cursor:pointer; }
    .upload-mark { display:grid; place-items:center; width:52px; height:52px; margin:0 auto 14px; border-radius:17px; background:var(--green); color:white; font-size:28px; line-height:1; }
    .drop strong { display:block; margin-bottom:5px; font-size:18px; }
    .drop span { color:var(--muted); font-size:14px; }
    .note { margin:0 3px 24px; color:var(--muted); font-size:13px; text-align:center; }
    .panel { margin-top:18px; padding:20px; border:1px solid var(--line); border-radius:22px; background:var(--card); box-shadow:0 10px 35px rgba(43,52,46,.06); }
    .panel-head { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px; }
    h2 { margin:0; font-size:16px; letter-spacing:-.02em; }
    .count { color:var(--muted); font-size:12px; }
    .empty { padding:12px 0 3px; color:var(--muted); font-size:14px; }
    .item { padding:13px 0; border-top:1px solid #ebe7de; }
    .item:first-child { border-top:0; }
    .row { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; }
    .file-name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; font-weight:720; }
    .file-meta { flex:none; color:var(--muted); font-size:12px; }
    .bar { height:7px; margin-top:10px; overflow:hidden; border-radius:99px; background:#e7e4db; }
    .fill { width:0; height:100%; border-radius:inherit; background:linear-gradient(90deg,var(--green),#31a979); transition:width .15s linear; }
    .item.error .fill { background:var(--red); }
    .item.done .fill { background:#2d9a6c; }
    .item-status { margin-top:7px; color:var(--muted); font-size:12px; }
    .item.error .item-status { color:var(--red); }
    .received { display:flex; align-items:center; gap:11px; padding:11px 0; border-top:1px solid #ebe7de; }
    .received:first-child { border-top:0; }
    .check { flex:none; display:grid; place-items:center; width:28px; height:28px; border-radius:9px; background:var(--soft); color:var(--green); font-weight:900; }
    .received-text { min-width:0; flex:1; }
    .received-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; font-weight:700; }
    .received-meta { margin-top:2px; color:var(--muted); font-size:12px; }
    .download { color:inherit; text-decoration:none; border-radius:12px; }
    .download:hover { background:var(--soft); }
    .download .received-meta { display:block; }
    .privacy { display:flex; gap:10px; align-items:flex-start; margin:22px 4px 0; color:var(--muted); font-size:12px; line-height:1.45; }
    .shield { flex:none; color:var(--green); font-weight:900; }
    @media (max-width:480px) { .shell{padding-top:24px}.panel{padding:17px}.drop{padding:29px 16px} }
    @media (prefers-reduced-motion:reduce) { * { transition:none!important; } }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand">WiFi Drop</div>
      <div class="status"><span class="dot"></span> Laptop connected</div>
    </header>
    <section class="hero">
      <h1>Send it across the room.</h1>
      <p class="lede">Choose videos or other files from this phone. They travel directly to your laptop over this Wi-Fi.</p>
    </section>

    <label class="drop" id="dropZone">
      <input id="picker" type="file" multiple aria-label="Choose files to send">
      <span class="upload-mark" aria-hidden="true">↑</span>
      <strong>Choose files</strong>
      <span>Videos, photos, documents — large files are welcome</span>
    </label>
    <p class="note">Keep this page open until every file says “Saved”.</p>

    <section class="panel" id="queuePanel" hidden>
      <div class="panel-head"><h2>Sending</h2><span class="count" id="queueCount"></span></div>
      <div id="queue"></div>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>Received on laptop</h2><span class="count" id="receivedCount"></span></div>
      <div id="received"><div class="empty">No files received yet.</div></div>
    </section>

    <section class="panel" id="sharedPanel" hidden>
      <div class="panel-head"><h2>From the laptop</h2><span class="count" id="sharedCount"></span></div>
      <div id="shared"></div>
    </section>

    <div class="privacy"><span class="shield">◆</span><span>Private to this Wi-Fi session. Files go directly to the laptop and are not uploaded to a cloud service.</span></div>
  </main>
  <script>
    const PIN = __PIN__;
    const picker = document.getElementById('picker');
    const zone = document.getElementById('dropZone');
    const queue = document.getElementById('queue');
    const queuePanel = document.getElementById('queuePanel');
    let pending = [];
    let busy = false;
    let wakeLock = null;

    const formatBytes = n => {
      if (!Number.isFinite(n)) return '';
      const units = ['B','KB','MB','GB','TB']; let i=0;
      while (n >= 1024 && i < units.length-1) { n/=1024; i++; }
      return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
    };
    const escapeHTML = s => String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

    async function refreshReceived() {
      try {
        const res = await fetch(`/api/files?pin=${encodeURIComponent(PIN)}`, {cache:'no-store'});
        if (!res.ok) return;
        const data = await res.json();
        const box = document.getElementById('received');
        document.getElementById('receivedCount').textContent = data.files.length ? `${data.files.length} file${data.files.length===1?'':'s'}` : '';
        box.innerHTML = data.files.length ? data.files.map(f => `<div class="received"><span class="check">✓</span><div class="received-text"><div class="received-name">${escapeHTML(f.name)}</div><div class="received-meta">${formatBytes(f.size)} · ${escapeHTML(f.time)}</div></div></div>`).join('') : '<div class="empty">No files received yet.</div>';
      } catch (_) {}
    }

    async function refreshShared() {
      try {
        const res = await fetch(`/api/shared?pin=${encodeURIComponent(PIN)}`, {cache:'no-store'});
        if (!res.ok) return;
        const data = await res.json();
        const panel = document.getElementById('sharedPanel');
        const box = document.getElementById('shared');
        panel.hidden = data.files.length === 0;
        document.getElementById('sharedCount').textContent = `${data.files.length} file${data.files.length===1?'':'s'}`;
        box.innerHTML = data.files.map(f => `<a class="received download" href="/download?pin=${encodeURIComponent(PIN)}&id=${encodeURIComponent(f.id)}"><span class="check">↓</span><span class="received-text"><span class="received-name">${escapeHTML(f.name)}</span><span class="received-meta">${formatBytes(f.size)} · Tap to download</span></span></a>`).join('');
      } catch (_) {}
    }

    function addFiles(files) {
      for (const file of files) {
        const id = `f-${crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`;
        pending.push({file,id});
        queue.insertAdjacentHTML('beforeend', `<div class="item" id="${id}"><div class="row"><div class="file-name">${escapeHTML(file.name)}</div><div class="file-meta">${formatBytes(file.size)}</div></div><div class="bar"><div class="fill"></div></div><div class="item-status">Waiting…</div></div>`);
      }
      queuePanel.hidden = false;
      document.getElementById('queueCount').textContent = `${pending.length} queued`;
      runQueue();
    }

    async function holdAwake() {
      try { if ('wakeLock' in navigator && !wakeLock) wakeLock = await navigator.wakeLock.request('screen'); } catch (_) {}
    }
    async function releaseAwake() {
      try { if (wakeLock) await wakeLock.release(); } catch (_) {} wakeLock = null;
    }

    async function runQueue() {
      if (busy) return;
      busy = true;
      await holdAwake();
      while (pending.length) {
        const job = pending.shift();
        document.getElementById('queueCount').textContent = `${pending.length + 1} remaining`;
        await upload(job);
      }
      busy = false;
      document.getElementById('queueCount').textContent = 'Complete';
      await releaseAwake();
      picker.value = '';
    }

    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

    async function postJSON(path, body) {
      const joiner = path.includes('?') ? '&' : '?';
      const res = await fetch(`${path}${joiner}pin=${encodeURIComponent(PIN)}`, {
        method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body || {})
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
      return data;
    }

    function sendChunk({file, uploadId, offset, end, item, speedState}) {
      return new Promise((resolve, reject) => {
        const fill = item.querySelector('.fill');
        const status = item.querySelector('.item-status');
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', `/api/chunk?pin=${encodeURIComponent(PIN)}&id=${encodeURIComponent(uploadId)}&offset=${offset}`);
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        xhr.upload.onprogress = event => {
          if (!event.lengthComputable) return;
          const loaded = offset + event.loaded;
          const pct = Math.min(100, loaded / file.size * 100);
          const now = performance.now();
          if (now - speedState.time > 500) {
            const speed = (loaded - speedState.loaded) / ((now - speedState.time) / 1000);
            const eta = speed > 0 ? Math.ceil((file.size - loaded) / speed) : 0;
            status.textContent = `${Math.round(pct)}% · ${formatBytes(speed)}/s${eta ? ` · about ${eta}s left` : ''}`;
            speedState.time = now;
            speedState.loaded = loaded;
          }
          fill.style.width = `${pct}%`;
        };
        xhr.onload = () => {
          let data = {};
          try { data = JSON.parse(xhr.responseText || '{}'); } catch (_) {}
          if (xhr.status >= 200 && xhr.status < 300) resolve(data);
          else if (xhr.status === 409 && Number(data.received) >= end) resolve(data);
          else reject(new Error(data.error || `Chunk failed (${xhr.status})`));
        };
        xhr.onerror = () => reject(new Error('Connection interrupted'));
        xhr.onabort = () => reject(new Error('Transfer cancelled'));
        xhr.send(file.slice(offset, end));
      });
    }

    async function upload({file,id}) {
      const item = document.getElementById(id);
      const fill = item.querySelector('.fill');
      const status = item.querySelector('.item-status');
      const chunkSize = 8 * 1024 * 1024;
      const speedState = {time:performance.now(), loaded:0};
      let session = null;
      try {
        status.textContent = 'Preparing secure transfer…';
        session = await postJSON('/api/start', {name:file.name, size:file.size});
        let offset = Number(session.received || 0);
        while (offset < file.size) {
          const end = Math.min(offset + chunkSize, file.size);
          let sent = false;
          for (let attempt = 0; attempt < 5 && !sent; attempt++) {
            try {
              const result = await sendChunk({file, uploadId:session.id, offset, end, item, speedState});
              offset = Math.max(end, Number(result.received || 0));
              sent = true;
            } catch (error) {
              if (attempt === 4) throw error;
              status.textContent = `Wi-Fi paused — retrying this part (${attempt + 1}/4)…`;
              await pause(750 * Math.pow(2, attempt));
            }
          }
        }
        await postJSON(`/api/finish?id=${encodeURIComponent(session.id)}`, {});
        fill.style.width = '100%';
        item.classList.add('done');
        status.textContent = 'Saved on laptop';
        await refreshReceived();
      } catch (error) {
        if (session) postJSON(`/api/cancel?id=${encodeURIComponent(session.id)}`, {}).catch(() => {});
        item.classList.add('error');
        status.textContent = `${error.message || 'Transfer interrupted'}. Choose the file again to retry.`;
      }
    }

    picker.addEventListener('change', () => addFiles(picker.files));
    ['dragenter','dragover'].forEach(evt => zone.addEventListener(evt,e=>{e.preventDefault();zone.classList.add('drag')}));
    ['dragleave','drop'].forEach(evt => zone.addEventListener(evt,e=>{e.preventDefault();zone.classList.remove('drag')}));
    zone.addEventListener('drop', e => addFiles(e.dataTransfer.files));
    refreshReceived();
    refreshShared();
    setInterval(() => { refreshReceived(); refreshShared(); }, 5000);
  </script>
</body>
</html>'''


def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def safe_filename(raw_name):
    name = Path(raw_name.replace("\x00", "")).name.strip()
    name = re.sub(r"[\r\n/]", "_", name)
    return name[:240] or "unnamed-file"


def reserve_destination(folder, name):
    stem, suffix = os.path.splitext(name)
    with RESERVATION_LOCK:
        candidate = folder / name
        index = 2
        while candidate.exists() or candidate in RESERVED_PATHS:
            candidate = folder / f"{stem} ({index}){suffix}"
            index += 1
        RESERVED_PATHS.add(candidate)
        return candidate


def release_destination(path):
    with RESERVATION_LOCK:
        RESERVED_PATHS.discard(path)


def local_ipv4_addresses():
    found = []
    commands = [
        ["ipconfig", "getifaddr", "en0"],
        ["ipconfig", "getifaddr", "en1"],
        ["hostname", "-I"],
    ]
    for command in commands:
        try:
            output = subprocess.check_output(command, stderr=subprocess.DEVNULL, text=True, timeout=1)
        except Exception:
            continue
        for value in output.split():
            if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value) and not value.startswith("127.") and value not in found:
                found.append(value)
    if not found:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            value = sock.getsockname()[0]
            sock.close()
            if value and not value.startswith("127."):
                found.append(value)
        except OSError:
            pass
    return found


class WiFiDropServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "WiFiDrop/1.0"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            super().log_message(fmt, *args)

    def send_bytes(self, status, body=b"", content_type="text/plain; charset=utf-8", extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def request_pin(self, query):
        return query.get("pin", [""])[0] or self.headers.get("X-Upload-Pin", "")

    def authorized(self, query):
        return secrets.compare_digest(self.request_pin(query), self.server.pin)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/favicon.ico":
            self.send_bytes(204)
            return

        if parsed.path == "/" and not self.authorized(query):
            if self.client_address[0] in ("127.0.0.1", "::1"):
                self.send_bytes(302, extra_headers={"Location": f"/?pin={self.server.pin}"})
            else:
                message = b"WiFi Drop is locked. Open the full private link shown on the laptop."
                self.send_bytes(403, message)
            return

        if parsed.path == "/" and self.authorized(query):
            page = HTML_PAGE.replace("__PIN__", json.dumps(self.server.pin)).encode("utf-8")
            self.send_bytes(200, page, "text/html; charset=utf-8")
            return

        if parsed.path == "/api/files" and self.authorized(query):
            files = []
            with self.server.received_files_lock:
                received_paths = list(self.server.received_files)
            for path in received_paths:
                if not path.is_file():
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                files.append({
                    "name": path.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "time": time.strftime("%b %d, %I:%M %p", time.localtime(stat.st_mtime)).replace(" 0", " "),
                })
            files.sort(key=lambda item: item["modified"], reverse=True)
            self.send_bytes(200, json_bytes({"files": files[:30]}), "application/json; charset=utf-8")
            return

        if parsed.path == "/api/shared" and self.authorized(query):
            files = []
            with self.server.shared_files_lock:
                shared_items = list(self.server.shared_files.items())
            for file_id, path in shared_items:
                try:
                    stat = path.stat()
                except OSError:
                    continue
                files.append({"id": file_id, "name": path.name, "size": stat.st_size})
            self.send_bytes(200, json_bytes({"files": files}), "application/json; charset=utf-8")
            return

        if parsed.path == "/download" and self.authorized(query):
            file_id = query.get("id", [""])[0]
            with self.server.shared_files_lock:
                path = self.server.shared_files.get(file_id)
            if path is None or not path.is_file():
                self.send_bytes(404, b"Shared file not found")
                return
            try:
                size = path.stat().st_size
                start, end = 0, size - 1
                range_header = self.headers.get("Range", "")
                if range_header.startswith("bytes="):
                    start_text, _, end_text = range_header[6:].partition("-")
                    start = int(start_text) if start_text else 0
                    end = int(end_text) if end_text else size - 1
                    if start < 0 or end < start or start >= size:
                        self.send_bytes(416, extra_headers={"Content-Range": f"bytes */{size}"})
                        return
                    end = min(end, size - 1)
                length = max(0, end - start + 1)
                self.send_response(206 if range_header.startswith("bytes=") else 200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                if range_header.startswith("bytes="):
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                encoded_name = urllib.parse.quote(path.name)
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{encoded_name}")
                self.send_header("Cache-Control", "private, no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                with path.open("rb") as source:
                    source.seek(start)
                    remaining = length
                    while remaining:
                        chunk = source.read(min(CHUNK_SIZE, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except (OSError, ValueError):
                if not self.wfile.closed:
                    try:
                        self.send_bytes(500, b"Could not read shared file")
                    except (BrokenPipeError, ConnectionResetError):
                        pass
            return

        self.send_bytes(404, b"Not found")

    def read_json(self, maximum=65536):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request size")
        if content_length < 0 or content_length > maximum:
            raise ValueError("Invalid request size")
        try:
            return json.loads(self.rfile.read(content_length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Invalid JSON")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if not self.authorized(query):
            self.send_bytes(403, json_bytes({"error": "Invalid access code"}), "application/json")
            return

        if parsed.path == "/api/start":
            try:
                payload = self.read_json()
                size = int(payload.get("size", -1))
            except (ValueError, TypeError):
                self.send_bytes(400, json_bytes({"error": "Invalid file information"}), "application/json")
                return
            if size < 0 or size > MAX_UPLOAD_BYTES:
                self.send_bytes(413, json_bytes({"error": "File must be smaller than 25 GB"}), "application/json")
                return
            final_path = reserve_destination(self.server.output_dir, safe_filename(str(payload.get("name", ""))))
            temp_path = self.server.output_dir / f".wifi-drop-{uuid.uuid4().hex}.part"
            upload_id = secrets.token_urlsafe(18)
            try:
                temp_path.touch(exist_ok=False)
            except OSError:
                release_destination(final_path)
                self.send_bytes(500, json_bytes({"error": "Could not prepare the Desktop file"}), "application/json")
                return
            with UPLOADS_LOCK:
                UPLOADS[upload_id] = {
                    "temp": temp_path,
                    "final": final_path,
                    "size": size,
                    "received": 0,
                    "created": time.time(),
                }
            self.send_bytes(201, json_bytes({"id": upload_id, "name": final_path.name, "received": 0}), "application/json")
            return

        if parsed.path == "/api/finish":
            upload_id = query.get("id", [""])[0]
            with UPLOADS_LOCK:
                state = UPLOADS.get(upload_id)
                if state is None:
                    self.send_bytes(404, json_bytes({"error": "Upload session not found"}), "application/json")
                    return
                if state["received"] != state["size"]:
                    self.send_bytes(409, json_bytes({"error": "File is not complete", "received": state["received"]}), "application/json")
                    return
                try:
                    with state["temp"].open("rb") as uploaded:
                        os.fsync(uploaded.fileno())
                    os.replace(state["temp"], state["final"])
                except OSError:
                    self.send_bytes(500, json_bytes({"error": "Could not finish saving the file"}), "application/json")
                    return
                UPLOADS.pop(upload_id, None)
            release_destination(state["final"])
            with self.server.received_files_lock:
                self.server.received_files.insert(0, state["final"])
            self.send_bytes(201, json_bytes({"saved": True, "name": state["final"].name, "size": state["size"]}), "application/json")
            return

        if parsed.path == "/api/cancel":
            upload_id = query.get("id", [""])[0]
            with UPLOADS_LOCK:
                state = UPLOADS.pop(upload_id, None)
            if state is not None:
                try:
                    state["temp"].unlink(missing_ok=True)
                except OSError:
                    pass
                release_destination(state["final"])
            self.send_bytes(200, json_bytes({"cancelled": True}), "application/json")
            return

        self.send_bytes(404, b"Not found")

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path not in ("/upload", "/api/chunk"):
            self.send_bytes(404, b"Not found")
            return
        if not self.authorized(query):
            self.send_bytes(403, json_bytes({"error": "Invalid access code"}), "application/json")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            content_length = -1
        if content_length < 0:
            self.send_bytes(411, json_bytes({"error": "File size is required"}), "application/json")
            return
        if content_length > (MAX_CHUNK_BYTES if parsed.path == "/api/chunk" else MAX_UPLOAD_BYTES):
            self.send_bytes(413, json_bytes({"error": "File is larger than 25 GB"}), "application/json")
            return

        if parsed.path == "/api/chunk":
            upload_id = query.get("id", [""])[0]
            try:
                offset = int(query.get("offset", ["-1"])[0])
            except ValueError:
                offset = -1
            with UPLOADS_LOCK:
                state = UPLOADS.get(upload_id)
                if state is None:
                    self.send_bytes(404, json_bytes({"error": "Upload session not found"}), "application/json")
                    return
                if offset != state["received"]:
                    remaining = content_length
                    while remaining:
                        discarded = self.rfile.read(min(CHUNK_SIZE, remaining))
                        if not discarded:
                            break
                        remaining -= len(discarded)
                    self.send_bytes(409, json_bytes({"error": "Chunk offset changed", "received": state["received"]}), "application/json")
                    return
                if offset + content_length > state["size"]:
                    self.send_bytes(400, json_bytes({"error": "Chunk exceeds file size"}), "application/json")
                    return
                remaining = content_length
                try:
                    with state["temp"].open("r+b") as output:
                        output.seek(offset)
                        while remaining:
                            chunk = self.rfile.read(min(CHUNK_SIZE, remaining))
                            if not chunk:
                                raise ConnectionError("Chunk ended early")
                            output.write(chunk)
                            remaining -= len(chunk)
                        output.flush()
                    state["received"] = offset + content_length
                    received = state["received"]
                except (ConnectionError, OSError):
                    try:
                        with state["temp"].open("r+b") as output:
                            output.truncate(offset)
                    except OSError:
                        pass
                    try:
                        self.send_bytes(500, json_bytes({"error": "Chunk was interrupted", "received": offset}), "application/json")
                    except BrokenPipeError:
                        pass
                    return
            self.send_bytes(200, json_bytes({"received": received}), "application/json")
            return

        raw_name = query.get("name", [""])[0]
        final_path = reserve_destination(self.server.output_dir, safe_filename(raw_name))
        temp_path = self.server.output_dir / f".wifi-drop-{uuid.uuid4().hex}.part"
        remaining = content_length
        saved = False
        try:
            with temp_path.open("xb") as output:
                while remaining:
                    chunk = self.rfile.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        raise ConnectionError("Upload ended before the complete file arrived")
                    output.write(chunk)
                    remaining -= len(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_path, final_path)
            saved = True
            with self.server.received_files_lock:
                self.server.received_files.insert(0, final_path)
            self.send_bytes(201, json_bytes({"saved": True, "name": final_path.name, "size": content_length}), "application/json")
        except (BrokenPipeError, ConnectionError, OSError) as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            if not isinstance(exc, BrokenPipeError):
                try:
                    self.send_bytes(500, json_bytes({"error": "The transfer was interrupted"}), "application/json")
                except BrokenPipeError:
                    pass
        finally:
            release_destination(final_path)
            if not saved:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Receive files from a phone on the same Wi-Fi")
    parser.add_argument("--port", type=int, default=8765, help="Starting port (default: 8765)")
    parser.add_argument("--output", type=Path, default=Path.home() / "Desktop" / "WiFi Drop", help="Save folder (default: Desktop/WiFi Drop)")
    parser.add_argument("--pin", help="Reuse a specific private access code")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.pin and not re.fullmatch(r"\d{4,12}", args.pin):
        raise SystemExit("The access code must contain 4 to 12 digits.")
    pin = args.pin or f"{secrets.randbelow(900000) + 100000}"

    server = None
    for port in range(args.port, args.port + 11):
        try:
            server = WiFiDropServer(("0.0.0.0", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise SystemExit(f"Could not find an available port from {args.port} to {args.port + 10}.")

    server.pin = pin
    server.output_dir = output_dir
    server.verbose = args.verbose
    server.received_files = []
    server.received_files_lock = threading.Lock()
    server.shared_files = {}
    server.shared_files_lock = threading.Lock()
    addresses = local_ipv4_addresses()

    print("\n" + "=" * 62)
    print(f"  {APP_NAME} is ready")
    print("=" * 62)
    if addresses:
        print("\n  On your phone, open this private link:\n")
        print(f"  http://{addresses[0]}:{server.server_port}/?pin={pin}")
        if len(addresses) > 1:
            for address in addresses[1:]:
                print(f"  Alternative: http://{address}:{server.server_port}/?pin={pin}")
    else:
        print("\n  I could not detect the Wi-Fi address automatically.")
        print(f"  Open http://localhost:{server.server_port}/?pin={pin} on this laptop.")
    print(f"\n  Received files save to:\n  {output_dir}")
    print("\n  Keep this window open. Press Control-C when finished.\n")
    print("=" * 62 + "\n", flush=True)

    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nWiFi Drop stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
