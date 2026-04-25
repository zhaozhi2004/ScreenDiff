import os
import cv2
import numpy as np
from pathlib import Path


class DiffEngine:
    """图像差异对比引擎"""

    def __init__(self, diff_root: str = 'diffs', threshold: int = 30):
        """
        diff_root: 差异图存储目录
        threshold: 像素差异阈值（0-255），超过视为不同
        """
        self.diff_root = Path(diff_root)
        self.diff_root.mkdir(parents=True, exist_ok=True)
        self.threshold = threshold

    def _read_image(self, path: str):
        """
        读取图片，支持中文路径
        cv2.imread 不支持中文路径，需要用 np.fromfile + cv2.imdecode
        """
        try:
            img_array = np.fromfile(path, dtype=np.uint8)
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def compare(self, img_a_path: str, img_b_path: str, task_id: str = None) -> dict:
        """
        对比两张图片，返回差异度信息和差异图路径
        Returns: {
            'score': float,          # 0.0 ~ 1.0，差异比例
            'diff_path': str,         # 差异图路径（含高亮）
            'total_pixels': int,
            'diff_pixels': int,
        }
        """
        if task_id is None:
            import uuid
            task_id = uuid.uuid4().hex[:8]

        diff_path = str(self.diff_root / f"{task_id}_diff.png")

        img_a = self._read_image(img_a_path)
        img_b = self._read_image(img_b_path)

        if img_a is None or img_b is None:
            return {
                'score': -1,
                'diff_path': '',
                'total_pixels': 0,
                'diff_pixels': 0,
                'error': 'Failed to load images'
            }

        # 尺寸对齐：把 B resize 到 A 的大小
        if img_a.shape != img_b.shape:
            img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))

        # 转灰度做差异计算
        gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

        # 像素级差异
        diff = cv2.absdiff(gray_a, gray_b)
        diff_mask = diff > self.threshold
        diff_pixels = int(np.sum(diff_mask))
        total_pixels = diff.size
        score = diff_pixels / total_pixels

        # 半透明叠加，差异区域标记为红色
        overlay = img_a.copy()
        overlay[diff_mask] = [0, 0, 255]  # BGR: Red
        diff_visual = cv2.addWeighted(img_a, 0.5, overlay, 0.5, 0)

        # 使用 imencode + tofile 保存，支持中文路径
        ext = Path(diff_path).suffix
        cv2.imencode(ext, diff_visual)[1].tofile(diff_path)

        return {
            'score': round(score, 4),
            'diff_path': diff_path,
            'total_pixels': total_pixels,
            'diff_pixels': diff_pixels,
            'error': ''
        }

    def compare_batch(self, screenshot_dir: str, baseline_dir: str,
                      task_id: str = None) -> list:
        """
        批量对比两个目录下的同名截图
        目录结构: {dir}/{width}x{height}/{browser}.png
        Returns: list of compare results
        """
        results = []
        screenshot_dir = Path(screenshot_dir)
        baseline_dir = Path(baseline_dir)

        if task_id is None:
            import uuid
            task_id = uuid.uuid4().hex[:8]

        for res_dir in screenshot_dir.iterdir():
            if not res_dir.is_dir():
                continue
            for img_file in res_dir.glob('*.png'):
                rel_res = res_dir.name
                rel_file = img_file.name
                baseline_path = baseline_dir / rel_res / rel_file

                if not baseline_path.exists():
                    continue

                comp_result = self.compare(
                    str(baseline_path),
                    str(img_file),
                    task_id=f"{task_id}_{rel_res}_{img_file.stem}"
                )
                comp_result['resolution'] = rel_res
                comp_result['browser'] = img_file.stem
                results.append(comp_result)

        return results
