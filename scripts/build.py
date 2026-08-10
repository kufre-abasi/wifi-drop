#!/usr/bin/env python3
"""Build a standalone WiFi Drop desktop application with PyInstaller."""

import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "assets" / "generated"


def make_icon():
    GENERATED.mkdir(parents=True, exist_ok=True)
    size = 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70, 70, 954, 954), radius=230, fill="#176b4a")
    draw.rounded_rectangle((205, 235, 819, 789), radius=118, fill="#fffdf8")
    draw.rounded_rectangle((281, 315, 743, 709), radius=72, fill="#dfeee5")
    draw.rounded_rectangle((462, 350, 562, 610), radius=50, fill="#176b4a")
    draw.polygon([(382, 500), (512, 370), (642, 500)], fill="#176b4a")
    draw.rounded_rectangle((382, 630, 642, 670), radius=20, fill="#176b4a")
    png = GENERATED / "wifi-drop.png"
    image.save(png)

    ico = GENERATED / "wifi-drop.ico"
    image.save(ico, sizes=[(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)])

    if platform.system() == "Darwin":
        iconset = GENERATED / "WiFi Drop.iconset"
        if iconset.exists():
            shutil.rmtree(iconset)
        iconset.mkdir()
        for points in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = points * scale
                target = iconset / f"icon_{points}x{points}{'@2x' if scale == 2 else ''}.png"
                image.resize((pixels, pixels), Image.Resampling.LANCZOS).save(target)
        icns = GENERATED / "WiFi Drop.icns"
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True)
        return icns
    return ico if platform.system() == "Windows" else png


def main():
    icon = make_icon()
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "WiFi Drop",
        "--icon",
        str(icon),
        str(ROOT / "desktop_app.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    if platform.system() == "Darwin":
        app = ROOT / "dist" / "WiFi Drop.app"
        plist_path = app / "Contents" / "Info.plist"
        with plist_path.open("rb") as source:
            info = plistlib.load(source)
        info["CFBundleIdentifier"] = "com.kromate.wifi-drop"
        info["NSHighResolutionCapable"] = True
        info["NSRequiresAquaSystemAppearance"] = True
        with plist_path.open("wb") as target:
            plistlib.dump(info, target, sort_keys=True)
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)


if __name__ == "__main__":
    main()
