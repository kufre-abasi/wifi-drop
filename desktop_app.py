#!/usr/bin/env python3
"""WKWebView desktop control panel for WiFi Drop."""

import base64
import io
import json
import os
import platform
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import qrcode
import webview

from wifi_drop import Handler, UPLOADS, UPLOADS_LOCK, WiFiDropServer, local_ipv4_addresses


APP_NAME = "WiFi Drop"
DEFAULT_FOLDER = Path.home() / "Desktop" / APP_NAME


ADMIN_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WiFi Drop</title>
  <style>
    :root { color-scheme:light; --ink:#17211b; --muted:#68736c; --paper:#f5f1e8; --card:#fffdf8; --line:#d9d5ca; --green:#176b4a; --green-dark:#0d5137; --soft:#dfeee5; --white:#fff; --shadow:0 18px 55px rgba(38,49,41,.09); }
    * { box-sizing:border-box; }
    html { background:var(--paper); }
    body { margin:0; min-height:100vh; color:var(--ink); background:radial-gradient(circle at 5% -5%,#fff 0,transparent 32%),var(--paper); font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif; -webkit-font-smoothing:antialiased; }
    button { font:inherit; }
    .app { width:min(1120px,calc(100% - 48px)); margin:0 auto; padding:32px 0 38px; }
    header { display:flex; align-items:center; justify-content:space-between; gap:20px; }
    .brand { display:flex; align-items:center; gap:12px; font-size:20px; font-weight:800; letter-spacing:-.035em; }
    .logo { position:relative; display:grid; place-items:center; width:38px; height:38px; border-radius:12px; background:var(--green); color:white; font-size:23px; font-weight:800; box-shadow:0 7px 18px rgba(23,107,74,.22); }
    .ready { display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:99px; background:var(--soft); color:var(--green); font-size:12px; font-weight:750; }
    .dot { width:8px; height:8px; border-radius:50%; background:#28a870; box-shadow:0 0 0 4px rgba(40,168,112,.12); }
    .hero { display:flex; align-items:flex-end; justify-content:space-between; gap:30px; margin:36px 0 24px; }
    h1 { max-width:650px; margin:0; font-size:clamp(38px,5vw,60px); line-height:.96; letter-spacing:-.06em; }
    .hero p { max-width:310px; margin:0 0 4px; color:var(--muted); font-size:15px; line-height:1.5; }
    .grid { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(300px,.8fr); gap:18px; align-items:start; }
    .stack { display:grid; gap:18px; }
    .card { padding:22px; border:1px solid var(--line); border-radius:22px; background:var(--card); box-shadow:var(--shadow); }
    .eyebrow { margin:0 0 8px; color:var(--muted); font-size:11px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
    h2 { margin:0; font-size:19px; letter-spacing:-.03em; }
    .link-layout { display:grid; grid-template-columns:minmax(0,1fr) 142px; gap:22px; align-items:center; }
    .link-box { display:flex; align-items:center; gap:10px; min-height:48px; margin:17px 0 14px; padding:10px 12px 10px 15px; border:1px solid var(--line); border-radius:14px; background:#faf8f2; }
    .link-box code { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#344239; font:600 12px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace; }
    .qr { width:142px; height:142px; padding:8px; border:1px solid var(--line); border-radius:18px; background:white; }
    .actions { display:flex; flex-wrap:wrap; gap:9px; }
    .button { display:inline-flex; align-items:center; justify-content:center; min-height:40px; padding:0 15px; border:1px solid transparent; border-radius:11px; cursor:pointer; font-size:13px; font-weight:750; transition:transform .15s ease,background .15s ease,border-color .15s ease; }
    .button:hover { transform:translateY(-1px); }
    .button:active { transform:translateY(0); }
    .primary { background:var(--green); color:white; box-shadow:0 8px 18px rgba(23,107,74,.17); }
    .primary:hover { background:var(--green-dark); }
    .secondary { border-color:var(--line); background:white; color:var(--ink); }
    .secondary:hover { border-color:#b8c0ba; background:#faf9f5; }
    .button:disabled { cursor:not-allowed; opacity:.46; transform:none; box-shadow:none; }
    .folder { display:flex; align-items:center; justify-content:space-between; gap:18px; }
    .folder-path { max-width:100%; margin:7px 0 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); font-size:13px; }
    .folder-icon { flex:none; display:grid; place-items:center; width:44px; height:44px; border-radius:14px; background:#efe9d9; color:#8b6f2e; font-size:21px; }
    .devices { display:grid; gap:9px; margin-top:15px; }
    .device { width:100%; display:flex; align-items:center; gap:12px; padding:12px; text-align:left; border:1px solid var(--line); border-radius:14px; background:white; cursor:pointer; transition:.15s ease; }
    .device:hover { border-color:#aab8af; }
    .device.selected { border-color:var(--green); background:var(--soft); box-shadow:0 0 0 2px rgba(23,107,74,.1); }
    .device-icon { flex:none; display:grid; place-items:center; width:36px; height:36px; border-radius:11px; background:#eef1ec; color:var(--green); font-size:17px; }
    .device-copy { min-width:0; flex:1; }
    .device-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; font-weight:750; }
    .device-meta { margin-top:3px; color:var(--muted); font-size:11px; }
    .radio { width:16px; height:16px; border:2px solid #bec7c1; border-radius:50%; }
    .selected .radio { border:5px solid var(--green); background:white; }
    .empty { padding:18px 0 5px; color:var(--muted); font-size:13px; line-height:1.5; }
    .send { margin-top:15px; display:flex; align-items:center; justify-content:space-between; gap:12px; padding-top:15px; border-top:1px solid #ebe7de; }
    .send-copy { color:var(--muted); font-size:12px; line-height:1.4; }
    .activity { margin-top:14px; }
    .activity-row { display:flex; align-items:center; gap:11px; padding:11px 0; border-top:1px solid #ebe7de; }
    .activity-row:first-child { border-top:0; }
    .check { flex:none; display:grid; place-items:center; width:28px; height:28px; border-radius:9px; background:var(--soft); color:var(--green); font-size:13px; font-weight:900; }
    .activity-name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; font-weight:700; }
    .notice { display:none; margin:0 0 16px; padding:11px 14px; border-radius:12px; background:var(--soft); color:var(--green-dark); font-size:13px; font-weight:650; }
    .notice.show { display:block; }
    footer { display:flex; align-items:center; justify-content:space-between; gap:20px; margin-top:20px; color:var(--muted); font-size:11px; }
    .quiet { padding:0; border:0; background:transparent; color:var(--muted); cursor:pointer; font-size:11px; }
    .quiet:hover { color:var(--ink); }
    @media (max-width:850px) { .app{width:min(100% - 30px,680px)}.hero{display:block}.hero p{margin-top:14px}.grid{grid-template-columns:1fr}.link-layout{grid-template-columns:1fr}.qr{display:none} }
    @media (prefers-reduced-motion:reduce) { * { transition:none!important; } }
  </style>
</head>
<body>
  <main class="app">
    <header>
      <div class="brand"><span class="logo">↑</span><span>WiFi Drop</span></div>
      <div class="ready"><span class="dot"></span><span id="statusText">Starting…</span></div>
    </header>

    <section class="hero">
      <h1>Share files across the room.</h1>
      <p>No cloud, no account, no phone app. Devices only need to be on the same Wi-Fi.</p>
    </section>

    <div class="notice" id="notice" role="status"></div>

    <section class="grid">
      <div class="stack">
        <article class="card">
          <div class="link-layout">
            <div>
              <p class="eyebrow">Connect a phone</p>
              <h2>Scan or share this private link</h2>
              <div class="link-box"><code id="phoneLink">Preparing link…</code></div>
              <div class="actions">
                <button class="button primary" onclick="copyLink()">Copy link</button>
                <button class="button secondary" onclick="openPreview()">Open phone preview</button>
              </div>
            </div>
            <img class="qr" id="qr" alt="QR code for the phone link">
          </div>
        </article>

        <article class="card folder">
          <div style="min-width:0;flex:1">
            <p class="eyebrow">Save received files to</p>
            <h2>WiFi Drop folder</h2>
            <p class="folder-path" id="folderPath">Desktop/WiFi Drop</p>
            <div class="actions" style="margin-top:14px">
              <button class="button secondary" onclick="chooseFolder()">Choose folder</button>
              <button class="button secondary" onclick="openFolder()">Open folder</button>
            </div>
          </div>
          <span class="folder-icon">▰</span>
        </article>

        <article class="card">
          <p class="eyebrow">Recent activity</p>
          <h2 id="activityTitle">No transfers yet</h2>
          <div class="activity" id="activity"><div class="empty">Received files will appear here.</div></div>
        </article>
      </div>

      <aside class="stack">
        <article class="card">
          <p class="eyebrow">Nearby devices</p>
          <h2>Choose a recipient</h2>
          <div class="devices" id="devices"><div class="empty">Open the phone link to make a device appear here.</div></div>
          <div class="send">
            <span class="send-copy" id="sendCopy">Waiting for a device</span>
            <button class="button primary" id="sendButton" onclick="sendFiles()" disabled>Choose files</button>
          </div>
        </article>

        <article class="card">
          <p class="eyebrow">How it works</p>
          <div class="activity-row"><span class="check">1</span><div class="activity-name">Open the private link on a phone</div></div>
          <div class="activity-row"><span class="check">2</span><div class="activity-name">Select that phone under Nearby devices</div></div>
          <div class="activity-row"><span class="check">3</span><div class="activity-name">Send files directly over this Wi-Fi</div></div>
        </article>
      </aside>
    </section>

    <footer><span>Private local transfer · Keep WiFi Drop open while sending</span><button class="quiet" onclick="quitApp()">Quit WiFi Drop</button></footer>
  </main>

  <script>
    let appState = null;
    let selectedDevice = null;
    const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
    const notice = message => { const el=document.getElementById('notice'); el.textContent=message; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),2800); };

    async function refresh() {
      try {
        appState = await window.pywebview.api.status();
        document.getElementById('statusText').textContent = appState.active_uploads ? `Receiving ${appState.active_uploads}` : 'Ready';
        document.getElementById('phoneLink').textContent = appState.phone_url;
        document.getElementById('folderPath').textContent = appState.destination;
        document.getElementById('qr').src = appState.qr;
        renderDevices(appState.devices);
        renderActivity(appState.received, appState.active_uploads);
      } catch (_) {}
    }

    function renderDevices(devices) {
      const box = document.getElementById('devices');
      if (!devices.length) {
        selectedDevice = null;
        box.innerHTML = '<div class="empty">Open the phone link to make a device appear here.</div>';
      } else {
        if (!devices.some(d => d.id === selectedDevice)) selectedDevice = devices[0].id;
        box.innerHTML = devices.map(device => `<button class="device ${device.id===selectedDevice?'selected':''}" onclick="selectDevice('${esc(device.id)}')"><span class="device-icon">▯</span><span class="device-copy"><span class="device-name">${esc(device.name)}</span><span class="device-meta">Connected · ${esc(device.ip)}</span></span><span class="radio"></span></button>`).join('');
      }
      const chosen = devices.find(d => d.id === selectedDevice);
      document.getElementById('sendButton').disabled = !chosen;
      document.getElementById('sendCopy').textContent = chosen ? `Send privately to ${chosen.name}` : 'Waiting for a device';
    }

    function renderActivity(files, active) {
      document.getElementById('activityTitle').textContent = active ? `Receiving ${active} file${active===1?'':'s'}…` : files.length ? `${files.length} file${files.length===1?'':'s'} received this session` : 'No transfers yet';
      document.getElementById('activity').innerHTML = files.length ? files.map(file => `<div class="activity-row"><span class="check">✓</span><div class="activity-name">${esc(file.name)}</div></div>`).join('') : '<div class="empty">Received files will appear here.</div>';
    }

    function selectDevice(id) { selectedDevice=id; renderDevices(appState.devices); }
    async function copyLink() { try { await navigator.clipboard.writeText(appState.phone_url); } catch (_) { const t=document.createElement('textarea');t.value=appState.phone_url;document.body.appendChild(t);t.select();document.execCommand('copy');t.remove(); } notice('Private link copied'); }
    async function openPreview() { await window.pywebview.api.open_preview(); }
    async function chooseFolder() { const result=await window.pywebview.api.choose_folder(); if(result?.message) notice(result.message); await refresh(); }
    async function openFolder() { await window.pywebview.api.open_folder(); }
    async function sendFiles() { if(!selectedDevice)return; const result=await window.pywebview.api.choose_files(selectedDevice); if(result?.message) notice(result.message); await refresh(); }
    async function quitApp() { await window.pywebview.api.quit(); }
    window.addEventListener('pywebviewready', () => { refresh(); setInterval(refresh,2000); });
  </script>
</body>
</html>'''


def settings_path():
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "settings.json"


def load_destination():
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        value = str(data.get("destination", "")).strip()
        if value:
            return Path(value).expanduser()
    except (OSError, ValueError, TypeError):
        pass
    return DEFAULT_FOLDER


def save_destination(path):
    target = settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"destination": str(path)}, indent=2), encoding="utf-8")


def reveal_path(path):
    if platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif platform.system() == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def make_server(destination):
    server = None
    for port in range(8765, 8776):
        try:
            server = WiFiDropServer(("0.0.0.0", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError("No available local port between 8765 and 8775")
    server.pin = f"{secrets.randbelow(900000) + 100000}"
    server.output_dir = destination
    server.verbose = False
    server.received_files = []
    server.received_files_lock = threading.Lock()
    server.shared_files = {}
    server.shared_files_lock = threading.Lock()
    server.devices = {}
    server.devices_lock = threading.Lock()
    return server


class DesktopApi:
    def __init__(self, server, destination, phone_url):
        self.server = server
        self.destination = destination
        self.phone_url = phone_url
        self.window = None
        image = qrcode.make(phone_url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        self.qr = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")

    def status(self):
        with self.server.devices_lock:
            devices = [device.copy() for device in self.server.devices.values() if time.time() - device["last_seen"] < 20]
        devices.sort(key=lambda device: device["last_seen"], reverse=True)
        with self.server.received_files_lock:
            received = [{"name": path.name} for path in self.server.received_files[:8] if path.exists()]
        with UPLOADS_LOCK:
            active_uploads = len(UPLOADS)
        return {
            "phone_url": self.phone_url,
            "destination": str(self.destination),
            "qr": self.qr,
            "devices": devices,
            "received": received,
            "active_uploads": active_uploads,
        }

    def choose_folder(self):
        selected = self.window.create_file_dialog(webview.FileDialog.FOLDER, directory=str(self.destination))
        if not selected:
            return {"ok": False}
        destination = Path(selected[0]).resolve()
        try:
            destination.mkdir(parents=True, exist_ok=True)
            save_destination(destination)
        except OSError as error:
            return {"ok": False, "message": f"That folder cannot be used: {error}"}
        self.destination = destination
        self.server.output_dir = destination
        return {"ok": True, "message": "Save folder updated"}

    def open_folder(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        reveal_path(self.destination)
        return {"ok": True}

    def open_preview(self):
        webbrowser.open(self.phone_url)
        return {"ok": True}

    def choose_files(self, device_id):
        with self.server.devices_lock:
            device = self.server.devices.get(device_id)
            if not device or time.time() - device["last_seen"] >= 20:
                return {"ok": False, "message": "That device is no longer connected"}
            device_name = device["name"]
        selected = self.window.create_file_dialog(webview.FileDialog.OPEN, directory=str(Path.home()), allow_multiple=True)
        if not selected:
            return {"ok": False}
        added = 0
        with self.server.shared_files_lock:
            for value in selected:
                path = Path(value).resolve()
                duplicate = any(item["path"] == path and item.get("target") == device_id for item in self.server.shared_files.values())
                if path.is_file() and not duplicate:
                    self.server.shared_files[secrets.token_urlsafe(10)] = {"path": path, "target": device_id, "created": time.time()}
                    added += 1
        return {"ok": True, "message": f"{added} file{'s' if added != 1 else ''} ready for {device_name}"}

    def quit(self):
        if self.window:
            self.window.destroy()
        return {"ok": True}


def main():
    destination = load_destination().resolve()
    if "--self-test" in sys.argv:
        print(json.dumps({"app": APP_NAME, "default_destination": str(DEFAULT_FOLDER), "destination": str(destination), "ui": "WKWebView"}))
        return
    destination.mkdir(parents=True, exist_ok=True)
    server = make_server(destination)
    host = (local_ipv4_addresses() or ["127.0.0.1"])[0]
    phone_url = f"http://{host}:{server.server_port}/?pin={server.pin}"
    server_thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True)
    server_thread.start()
    api = DesktopApi(server, destination, phone_url)
    api.window = webview.create_window(
        APP_NAME,
        html=ADMIN_HTML,
        js_api=api,
        width=1080,
        height=790,
        min_size=(820, 640),
        resizable=True,
        background_color="#f5f1e8",
    )
    try:
        webview.start(gui="cocoa", debug=False, private_mode=False)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
