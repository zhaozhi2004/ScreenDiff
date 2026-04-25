# ScreenDiff

**跨浏览器视觉回归测试**


## 功能特性

- **多浏览器支持**：Chromium、Firefox、WebKit 三大内核
- **多分辨率测试**：支持自定义视口尺寸（1920x1080、1366x768、1536x864 等）
- **智能差异检测**：基于像素的图像对比，自动计算差异率和差异像素数
- **可视化对比**：并排展示基线截图、当前截图和差异高亮图
- **基线管理**：支持设置任意截图为基线，方便版本对比
- **报告导出**：一键生成 HTML 测试报告，包含完整对比数据

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | Flask 2.x |
| 截图引擎 | Playwright |
| 图像处理 | OpenCV + NumPy |
| 数据库 | SQLite (SQLAlchemy ORM) |
| 前端 | Jinja2 + 原生 JavaScript |
| 样式 | 自定义 CSS (深色主题) |

---

## 快速开始

### 环境要求

- Python 3.8+
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆项目
cd C:\Users\你的用户名\Desktop
git clone https://github.com/your-repo/screendiff.git
cd screendiff

# 2. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
playwright install

# 5. 初始化数据库
python init_db.py

# 6. 启动服务
python app.py
```

### 访问界面

打开浏览器访问：http://localhost:5000

---

## 使用方法

### 1. 创建测试项目

在首页点击「新建项目」，填写：
- 项目名称（如：百度首页）
- 测试 URL（如：https://www.baidu.com）
- 分辨率列表（如：1920x1080, 1366x768）
- 浏览器选择（可多选）

### 2. 运行测试

点击项目卡片上的「运行测试」，系统将：
1. 使用 Playwright 打开指定 URL
2. 在选定分辨率下截图
3. 自动保存到 `screenshots/` 目录

### 3. 对比分析

进入「视觉对比」页面：
1. 选择「基线版本」（作为参照的截图）
2. 选择「对比版本」（需要对比的新截图）
3. 点击「开始对比」

系统将显示：
- 基线截图
- 当前截图
- 差异高亮图（红色标记差异区域）
- 视觉差异率百分比
- 差异像素统计

### 4. 设置基线

在测试记录列表中，点击「设为基线」可将任意截图标记为标准参照。

### 5. 导出报告

点击「生成报告」，导出包含所有测试数据的 HTML 报告。

---

## 项目结构

```
screendiff/
├── app.py                 # Flask 主应用
├── config.py              # 配置文件
├── init_db.py             # 数据库初始化脚本
├── requirements.txt       # Python 依赖
│
├── models/
│   └── database.py        # 数据模型定义
│
├── services/
│   ├── playwright_runner.py  # Playwright 截图服务
│   ├── diff_engine.py        # 图像差异对比引擎
│   └── report_generator.py  # 报告生成服务
│
├── templates/
│   ├── base.html         # 基础模板
│   ├── index.html        # 首页
│   ├── compare.html      # 对比页面
│   └── report.html       # 报告页面
│
├── static/
│   └── style.css         # 样式文件
│
├── screenshots/          # 截图存储目录
├── diffs/                # 差异图存储目录
└── reports/              # 报告存储目录
```

---

## API 接口

### 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 获取所有项目 |
| POST | `/api/projects` | 创建新项目 |
| DELETE | `/api/projects/<id>` | 删除项目 |

### 测试运行

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/<id>/run` | 启动测试 |
| GET | `/api/test-runs/<id>` | 获取测试详情 |
| POST | `/api/test-runs/<id>/baseline` | 设置为基线 |

### 对比分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/compare?run_a=<id>&run_b=<id>` | 对比两个截图 |
| GET | `/api/report/<project_id>` | 获取报告数据 |

---

## 注意事项

### 中文路径问题

本项目使用 OpenCV 进行图像处理，但 OpenCV 的 `cv2.imread()` 不支持中文路径。项目已通过以下方案解决：

```python
# 读取图片（支持中文路径）
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

# 保存图片（支持中文路径）
_, buffer = cv2.imencode('.png', img)
buffer.tofile(path)
```

**建议**：如非必要，尽量将项目放置在纯英文路径下，可避免潜在的编码问题。

### Playwright 浏览器

首次运行需下载浏览器内核（约 300MB）：

```bash
playwright install
```

如遇网络问题，可设置国内镜像：

```bash
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install
```

---

## 常见问题

**Q: 截图显示为空白？**

A: 检查目标页面是否加载完成，可调整 `wait_for_load_state` 参数。

**Q: 差异图显示为全黑？**

A: 确认截图路径不含中文字符，或使用已修复的 NumPy 方案读取。

**Q: 运行测试无反应？**

A: 检查 Playwright 浏览器是否正确安装，运行 `playwright install` 重新安装。

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

## 许可证

MIT License

---
2026-张雅博
