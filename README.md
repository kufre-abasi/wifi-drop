# WiFi Drop

Transfer large files directly between a laptop and phones on the same Wi-Fi. There is no cloud upload, account, or phone app to install.

## Highlights

- Send videos, photos, documents, and other files in either direction.
- Stream files in 8 MB chunks with automatic retries on unstable Wi-Fi.
- Handle files up to 25 GB without loading the whole file into memory.
- Save received files to `Desktop/WiFi Drop` or a folder you choose.
- Discover browsers that have opened the private link and send to one selected device.
- Resume laptop-to-phone downloads and avoid overwriting duplicate filenames.
- Protect every session with a new random six-digit PIN.
- Use a native desktop control panel powered by WKWebView on macOS.

## Install on macOS

The downloadable desktop app does not require Python.

1. Open the [latest release](https://github.com/kromate/wifi-drop/releases/latest).
2. Download `WiFi-Drop-macOS-Apple-Silicon.zip`.
3. Open the ZIP and drag **WiFi Drop.app** into **Applications**.
4. Control-click **WiFi Drop** and choose **Open** the first time.
5. Allow incoming network connections if macOS asks.

The current prebuilt app supports Apple Silicon Macs. Intel Mac, Windows, and Linux users can run from source below; automated builds for all three operating systems are also available in the repository's **Actions** tab.

> The community macOS build is ad-hoc signed but not Apple-notarized, so macOS may show a first-launch security warning. If **Open** is unavailable, go to **System Settings → Privacy & Security** and choose **Open Anyway** after attempting to launch it once.

## Transfer files

### Phone to laptop

1. Connect the laptop and phone to the same Wi-Fi.
2. Open **WiFi Drop** on the laptop.
3. Scan the QR code with the phone, or copy and open the private link.
4. Choose files on the phone and keep the page open until every file says **Saved**.
5. Find the received files in `Desktop/WiFi Drop`, or in the folder selected in the desktop app.

### Laptop to phone

1. Open the QR code or private link on the phone.
2. Wait for the phone to appear under **Nearby devices** on the laptop.
3. Select that device and click **Choose files**.
4. Download the shared files from the phone page.

Only devices that open the private link appear in the app. Web browsers and operating systems do not safely expose a list of every client connected to the Wi-Fi.

## Run from source

You need [Python 3.9 or newer](https://www.python.org/downloads/).

### macOS and Linux

```bash
git clone https://github.com/kromate/wifi-drop.git
cd wifi-drop
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python desktop_app.py
```

On Linux, pywebview may require distribution-specific Qt system packages. See the [pywebview installation guide](https://pywebview.idepy.com/en/guide/installation).

### Windows PowerShell

```powershell
git clone https://github.com/kromate/wifi-drop.git
cd wifi-drop
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python desktop_app.py
```

### Terminal-only receiver

The basic receiver uses only the Python standard library and does not need the desktop UI dependencies:

```bash
python3 wifi_drop.py
```

It prints the private phone link in the terminal. Press `Ctrl+C` to stop it.

## Build a standalone application

Build on the operating system you want to support—PyInstaller does not cross-compile applications for other platforms.

```bash
python -m pip install -r requirements.txt pyinstaller
python scripts/build.py
```

The packaged application is written to `dist/`. Pushes and version tags also run the macOS, Windows, and Linux builds in GitHub Actions.

## Troubleshooting

- **The phone cannot open the link:** Confirm both devices are on the same non-guest Wi-Fi, keep WiFi Drop open, and allow incoming connections through the laptop firewall.
- **The phone is not listed:** Open or refresh the private WiFi Drop link on that phone.
- **A transfer was interrupted:** Keep both screens awake and choose the file again. Uploads retry automatically, while downloads support resuming.
- **The link changed:** A new private PIN is generated whenever the app restarts. Scan the current QR code again.
- **Port 8765 is busy:** Quit another running WiFi Drop instance, then reopen the app.

## Security and privacy

WiFi Drop serves an unencrypted private HTTP address on the local network. Files are never uploaded to a WiFi Drop cloud service. Use it only on a trusted home or office Wi-Fi—never expose port `8765` through port forwarding or a public IP address.

Anyone who knows the complete private link while the app is running can open the transfer page. Only files explicitly selected in the desktop app are offered for download.

See [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## Development

Run the automated tests with:

```bash
python -m unittest discover -s tests -v
```

Contributions and bug reports are welcome. Please include the operating system, Python version, and steps to reproduce when reporting a problem.

## License

[MIT](LICENSE)
