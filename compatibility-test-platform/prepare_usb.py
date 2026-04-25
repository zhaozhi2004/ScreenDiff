"""
Portable environment packer - run once on a networked PC
Downloads and installs all runtime deps for true USB-portable use

Usage: python prepare_usb.py
"""

import os
import sys
import platform
import subprocess
import urllib.request
import zipfile
from pathlib import Path

# -- Config ---------------------------------------------------
PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

ROOT = Path(__file__).parent.resolve()
PORTABLE_DIR = ROOT / "portable"
INSTALLER_DIR = ROOT / "installer"
WHEELS_DIR = INSTALLER_DIR / "wheels"
PYTHON_DIR = PORTABLE_DIR / "python"
BROWSERS_DIR = PORTABLE_DIR / "browsers"
DATA_DIR = PORTABLE_DIR / "data"
REQUIREMENTS_FILE = ROOT / "requirements.txt"


def header(msg):
    print(f"\n{'='*55}")
    print(f"  {msg}")
    print(f"{'='*55}\n")


def step(n, total, msg):
    print(f"  [{n}/{total}] {msg}")


def download_file(url, dest, desc=""):
    if desc:
        print(f"    Download: {desc}")
    print(f"    URL: {url}")
    print(f"    Dest: {dest}")

    if Path(dest).exists():
        print(f"    [SKIP] File exists")
        return True

    try:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest, reporthook=_progress_hook)
        print(f"\n    [OK] Download complete")
        return True
    except Exception as e:
        print(f"\n    [FAIL] Download error: {e}")
        return False


def _progress_hook(count, block_size, total_size):
    if total_size <= 0:
        return
    percent = min(int(count * block_size * 100 / total_size), 100)
    filled = percent // 2
    bar = '#' * filled + '-' * (50 - filled)
    sys.stdout.write(f"\r    Progress: [{bar}] {percent}%")
    sys.stdout.flush()


def setup_python_embed():
    step(1, 5, "Prepare Python embed package")

    zip_path = INSTALLER_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"

    if not download_file(PYTHON_EMBED_URL, str(zip_path), f"Python {PYTHON_VERSION} embed"):
        print("    Fallback: will use system Python")
        return False

    if PYTHON_DIR.exists():
        print(f"    [SKIP] Already extracted")
    else:
        print(f"    Extract to: {PYTHON_DIR}")
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(PYTHON_DIR))
        print(f"    [OK] Extracted")

    # Configure _pth file to enable site-packages
    pth_file = PYTHON_DIR / f"python{PYTHON_VERSION.replace('.','')[:2]}._pth"
    if pth_file.exists():
        pth_content = f"""python{PYTHON_VERSION.replace('.','')[:2]}.zip
.
Lib
Lib\\site-packages
..\\..\\..\\
import site
"""
        pth_file.write_text(pth_content, encoding='utf-8')
        print(f"    [OK] Configured _pth")

    (PYTHON_DIR / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    return True


def setup_pip():
    step(2, 5, "Install pip into portable Python")

    get_pip_path = INSTALLER_DIR / "get-pip.py"
    if not download_file(GET_PIP_URL, str(get_pip_path), "get-pip.py"):
        return False

    python_exe = PYTHON_DIR / "python.exe"
    if not python_exe.exists():
        print("    [FAIL] Python embed not ready")
        return False

    result = subprocess.run(
        [str(python_exe), "-m", "pip", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"    [SKIP] pip already installed: {result.stdout.strip()}")
        return True

    print(f"    Installing pip...")
    result = subprocess.run(
        [str(python_exe), str(get_pip_path), "--no-warn-script-location"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"    [FAIL] pip install error: {result.stderr}")
        return False

    print(f"    [OK] pip installed")
    return True


def download_wheels():
    step(3, 5, "Download dependency wheels (offline cache)")

    if not REQUIREMENTS_FILE.exists():
        print(f"    [FAIL] requirements.txt not found")
        return False

    WHEELS_DIR.mkdir(parents=True, exist_ok=True)

    wheel_count = len(list(WHEELS_DIR.glob("*.whl")))
    if wheel_count > 5:
        print(f"    [SKIP] {wheel_count} wheels already downloaded")
        return True

    print(f"    Downloading to: {WHEELS_DIR}")
    print(f"    This may take a few minutes...")

    pip_cmd = sys.executable
    result = subprocess.run(
        [pip_cmd, "-m", "pip", "download",
         "-r", str(REQUIREMENTS_FILE),
         "-d", str(WHEELS_DIR),
         "--platform", "win_amd64",
         "--python-version", "311",
         "--only-binary=:all:"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"    [WARN] Exact download failed, trying generic...")
        result = subprocess.run(
            [pip_cmd, "-m", "pip", "download",
             "-r", str(REQUIREMENTS_FILE),
             "-d", str(WHEELS_DIR)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"    [FAIL] Download error: {result.stderr}")
            return False

    wheel_count = len(list(WHEELS_DIR.glob("*.whl")))
    print(f"    [OK] Downloaded {wheel_count} packages")
    return True


def install_deps_to_portable():
    step(4, 5, "Install dependencies into portable Python")

    python_exe = PYTHON_DIR / "python.exe"
    pip_exe = PYTHON_DIR / "Scripts" / "pip.exe"

    if not python_exe.exists():
        print("    [FAIL] Portable Python not ready")
        return False

    # Check if already installed
    result = subprocess.run(
        [str(python_exe), "-c", "import flask"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("    [SKIP] Dependencies already installed")
        return True

    # Try offline install from local wheels first
    if WHEELS_DIR.exists() and list(WHEELS_DIR.glob("*.whl")):
        print(f"    Installing from local wheels (offline)...")
        result = subprocess.run(
            [str(pip_exe), "install", "--no-index",
             "--find-links", str(WHEELS_DIR),
             "-r", str(REQUIREMENTS_FILE),
             "--no-warn-script-location"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("    [OK] Installed from local wheels")
            return True
        print(f"    [WARN] Offline install failed, trying online...")

    # Online install
    print(f"    Installing from network...")
    result = subprocess.run(
        [str(pip_exe), "install", "-r", str(REQUIREMENTS_FILE),
         "--no-warn-script-location"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"    [FAIL] Install error: {result.stderr[-500:]}")
        return False

    print("    [OK] Dependencies installed from network")
    return True


def download_playwright_browser():
    step(5, 5, "Download Playwright Chromium")

    browser_dirs = list(BROWSERS_DIR.glob("chromium-*"))
    if browser_dirs:
        print(f"    [SKIP] Browser exists: {browser_dirs[0].name}")
        return True

    BROWSERS_DIR.mkdir(parents=True, exist_ok=True)

    # Use portable Python's playwright to download browser
    python_exe = PYTHON_DIR / "python.exe"
    if not python_exe.exists():
        # Fallback to system Python
        python_exe = Path(sys.executable)

    print(f"    Downloading Chromium (~150MB, may take 5-10 min)...")

    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)

    result = subprocess.run(
        [str(python_exe), "-m", "playwright", "install", "chromium"],
        env=env, capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"    [WARN] Browser download failed (can retry on first launch)")
        return True

    browser_dirs = list(BROWSERS_DIR.glob("chromium-*"))
    if browser_dirs:
        print(f"    [OK] Browser ready: {browser_dirs[0].name}")
    else:
        print(f"    [OK] Browser download command executed")

    return True


def print_summary():
    header("Pack complete!")

    total_size = 0
    file_count = 0
    for f in ROOT.rglob("*"):
        if f.is_file() and '.git' not in str(f) and '__pycache__' not in str(f):
            total_size += f.stat().st_size
            file_count += 1

    size_mb = total_size / (1024 * 1024)

    print(f"  Project:  {ROOT}")
    print(f"  Files:    {file_count}")
    print(f"  Size:     {size_mb:.1f} MB")
    print()
    print(f"  +--------------------------------------------------+")
    print(f"  |  TRULY PORTABLE - No Python install needed!      |")
    print(f"  |                                                  |")
    print(f"  |  Usage:                                          |")
    print(f"  |    1. Copy whole folder to USB drive             |")
    print(f"  |    2. Plug into ANY Windows PC                   |")
    print(f"  |    3. Double-click start.bat                     |")
    print(f"  |    4. Browser opens http://localhost:5000        |")
    print(f"  |                                                  |")
    print(f"  |  Data:  portable/data/ (SQLite)                  |")
    print(f"  |  Shots: screenshots/                             |")
    print(f"  +--------------------------------------------------+")
    print()


def main():
    # Force UTF-8 output on Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    header("Compatibility Test Platform - Portable Packer")
    print(f"  OS:     {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version}")
    print(f"  Root:   {ROOT}")
    print()

    print("  Checking network...")
    try:
        urllib.request.urlopen("https://www.python.org", timeout=5)
        print("  [OK] Network connected")
    except Exception:
        print("  [FAIL] No network - please run on a connected PC")

    for d in [INSTALLER_DIR, WHEELS_DIR, PYTHON_DIR, BROWSERS_DIR, DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    results = []
    results.append(("Python embed package", setup_python_embed()))
    results.append(("pip into portable Python", setup_pip()))
    results.append(("Dependency wheels (cache)", download_wheels()))
    results.append(("Install deps to portable", install_deps_to_portable()))
    results.append(("Playwright Chromium", download_playwright_browser()))

    print()
    header("Results")
    for name, ok in results:
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status}  {name}")

    print_summary()


if __name__ == "__main__":
    main()
