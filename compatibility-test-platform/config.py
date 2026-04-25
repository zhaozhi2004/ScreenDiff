import os
import sys
from pathlib import Path

# ── 项目根目录（兼容便携模式）──────────────────────
# 便携模式下 Python 嵌入包的 sys.executable 在 portable/python/ 下
# 需要定位到项目根目录
def _find_root():
    """从当前文件向上查找包含 app.py 的目录"""
    p = Path(__file__).resolve().parent
    # 如果当前目录就有 app.py，直接返回
    if (p / 'app.py').exists():
        return p
    # 否则返回当前文件所在目录
    return p

BASE_DIR = _find_root()

# ── 便携目录 ──────────────────────────────────────
PORTABLE_DIR = BASE_DIR / 'portable'
DATA_DIR = PORTABLE_DIR / 'data'
BROWSERS_DIR = PORTABLE_DIR / 'browsers'
SCREENSHOT_DIR = BASE_DIR / 'screenshots'
BASELINE_DIR = BASE_DIR / 'baselines'
DIFF_DIR = BASE_DIR / 'diffs'

# 确保目录存在
for d in [DATA_DIR, BROWSERS_DIR, SCREENSHOT_DIR, BASELINE_DIR, DIFF_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'compat-test-platform-dev-key')

    # ── SQLite（文件数据库，零依赖）────────────────
    DB_PATH = DATA_DIR / 'compatibility_test.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── 文件路径 ──────────────────────────────────
    SCREENSHOT_ROOT = str(SCREENSHOT_DIR)
    BASELINE_ROOT = str(BASELINE_DIR)
    DIFF_ROOT = str(DIFF_DIR)

    # ── Playwright ────────────────────────────────
    PLAYWRIGHT_TIMEOUT = 30000  # ms
    PLAYWRIGHT_BROWSERS_PATH = str(BROWSERS_DIR)

    # ── 测试限制 ──────────────────────────────────
    TEST_GLOBAL_TIMEOUT = 300
    MAX_CONCURRENT_TASKS = 3


# ── 预设分辨率 ────────────────────────────────────
DEFAULT_RESOLUTIONS = [
    {'name': '1920×1080 (Desktop)', 'width': 1920, 'height': 1080, 'device_scale': 1},
    {'name': '1366×768 (Laptop)', 'width': 1366, 'height': 768, 'device_scale': 1},
    {'name': '1536×864 (Laptop)', 'width': 1536, 'height': 864, 'device_scale': 1},
    {'name': '390×844 (iPhone 14)', 'width': 390, 'height': 844, 'device_scale': 3},
    {'name': '375×667 (iPhone SE)', 'width': 375, 'height': 667, 'device_scale': 2},
    {'name': '430×932 (iPhone 14 Pro Max)', 'width': 430, 'height': 932, 'device_scale': 3},
    {'name': '360×800 (Android)', 'width': 360, 'height': 800, 'device_scale': 2},
    {'name': '414×896 (iPhone XR)', 'width': 414, 'height': 896, 'device_scale': 2},
    {'name': '2560×1440 (2K)', 'width': 2560, 'height': 1440, 'device_scale': 1},
    {'name': '1280×720 (HD)', 'width': 1280, 'height': 720, 'device_scale': 1},
]

DEFAULT_BROWSERS = ['chromium', 'firefox', 'webkit']
