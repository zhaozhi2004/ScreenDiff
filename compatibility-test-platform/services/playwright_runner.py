import os
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright


class PlaywrightRunner:
    """多分辨率 Playwright 截图执行器"""

    BROWSER_MAP = {
        'chromium': 'chromium',
        'firefox': 'firefox',
        'webkit': 'webkit',
    }

    def __init__(self, screenshot_root: str, timeout_ms: int = 30000):
        self.screenshot_root = Path(screenshot_root)
        self.timeout_ms = timeout_ms

    def capture(self, url: str, width: int, height: int, browser: str = 'chromium',
                device_scale: int = 1, task_id: str = None) -> dict:
        """
        在指定分辨率下截图
        Returns: {
            'success': bool,
            'screenshot_path': str,
            'error': str
        }
        """
        if task_id is None:
            task_id = uuid.uuid4().hex[:8]

        run_dir = self.screenshot_root / task_id / f"{width}x{height}"
        run_dir.mkdir(parents=True, exist_ok=True)
        output_path = run_dir / f"{browser}.png"

        browser_type = self.BROWSER_MAP.get(browser, 'chromium')

        try:
            with sync_playwright() as p:
                browser_instance = getattr(p, browser_type).launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )

                context = browser_instance.new_context(
                    viewport={'width': width, 'height': height},
                    device_scale_factor=device_scale,
                    user_agent=None,
                )
                page = context.new_page()
                page.goto(url, timeout=self.timeout_ms, wait_until='networkidle')

                page.screenshot(
                    path=str(output_path),
                    full_page=False,
                    timeout=self.timeout_ms
                )

                context.close()
                browser_instance.close()

            return {
                'success': True,
                'screenshot_path': str(output_path),
                'error': ''
            }

        except Exception as e:
            return {
                'success': False,
                'screenshot_path': '',
                'error': str(e)
            }

    def run_test_suite(self, url: str, configs: list, task_id: str = None,
                       progress_callback=None) -> list:
        """
        按配置列表批量截图
        configs: [{resolution, width, height, device_scale, browser}]
        progress_callback: callable(current, total)
        Returns: list of result dicts
        """
        if task_id is None:
            task_id = uuid.uuid4().hex[:8]

        total = len(configs)
        results = []

        with sync_playwright() as p:
            for idx, cfg in enumerate(configs):
                width = cfg.get('width')
                height = cfg.get('height')
                browser = cfg.get('browser', 'chromium')
                device_scale = cfg.get('device_scale', 1)

                run_dir = self.screenshot_root / task_id / f"{width}x{height}"
                run_dir.mkdir(parents=True, exist_ok=True)
                output_path = run_dir / f"{browser}.png"

                result = {
                    'config': cfg,
                    'screenshot_path': '',
                    'success': False,
                    'error': ''
                }

                try:
                    browser_type = self.BROWSER_MAP.get(browser, 'chromium')
                    browser_instance = getattr(p, browser_type).launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )
                    context = browser_instance.new_context(
                        viewport={'width': width, 'height': height},
                        device_scale_factor=device_scale,
                    )
                    page = context.new_page()
                    page.goto(url, timeout=self.timeout_ms, wait_until='networkidle')
                    page.screenshot(path=str(output_path), full_page=False)
                    context.close()
                    browser_instance.close()

                    result['success'] = True
                    result['screenshot_path'] = str(output_path)

                except Exception as e:
                    result['error'] = str(e)

                results.append(result)

                if progress_callback:
                    progress_callback(idx + 1, total)

        return results
