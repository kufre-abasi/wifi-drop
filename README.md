# WiFi Drop

Share large files across the room. WiFi Drop transfers files directly between a laptop and phones on the same Wi-Fi—no cloud upload, account, or phone app.

## What it does

- Receives videos and other files from a phone through a mobile-friendly webpage.
- Streams in 8 MB chunks with automatic retries for unstable Wi-Fi.
- Saves into `Desktop/WiFi Drop` by default.
- Lets the laptop user choose and remember another destination folder.
- Shares selected laptop files back to connected phones, with resumable downloads.
- Protects each session with a random six-digit private link.
- Handles files up to 25 GB without loading them into memory.
- Adds suffixes instead of overwriting files with the same name.

## Use the desktop app

1. Download the build for your operating system from the repository's Actions artifacts or Releases.
2. Open **WiFi Drop** on the laptop.
3. Keep the app open and connect the phone to the same Wi-Fi.
4. Scan the QR code or copy the private phone link.
5. Choose files on the phone and wait for **Saved**.

On macOS, an unsigned community build may require **Control-click → Open** the first time. A signed/notarized release can remove that warning.

## Run from source

Python 3.9 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python desktop_app.py
```

The basic terminal receiver has no third-party runtime dependency:

```bash
python3 wifi_drop.py
```

## Build the desktop application

```bash
python -m pip install -r requirements.txt pyinstaller
python scripts/build.py
```

The packaged application appears in `dist/`. GitHub Actions builds macOS, Windows, and Linux artifacts automatically.

## Security and privacy

WiFi Drop serves a private HTTP address on the local network. Files are never sent to a WiFi Drop cloud service. Use a trusted home or office Wi-Fi rather than a public or guest network. Anyone who knows the full private link while the app is running can access the transfer page and files deliberately shared from the laptop.

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

[MIT](LICENSE)
