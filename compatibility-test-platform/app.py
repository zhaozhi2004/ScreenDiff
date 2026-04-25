import os
import uuid
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from config import Config, DEFAULT_RESOLUTIONS, DEFAULT_BROWSERS, BROWSERS_DIR
from models.database import db, Project, TestConfig, TestRun
from services.playwright_runner import PlaywrightRunner
from services.diff_engine import DiffEngine
from services.report_generator import ReportGenerator

app = Flask(__name__)

# 鈹€鈹€ Jinja2 鍏ㄥ眬杩囨护鍣?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
@app.template_filter('screenshot_rel')
def screenshot_rel(path):
    """灏嗗畬鏁存埅鍥捐矾寰勮浆涓?/screenshots/ 寮€澶寸殑 URL 璺緞"""
    if not path:
        return ''
    import re
    m = re.search(r'screenshots[\\/]', path)
    if m:
        return path[m.end():].replace('\\', '/')
    return path

@app.template_filter('diff_rel')
def diff_rel(path):
    """灏嗗畬鏁村樊寮傚浘璺緞杞负 /diffs/ 寮€澶寸殑 URL 璺緞"""
    if not path:
        return ''
    import re
    m = re.search(r'diffs[\\/]', path)
    if m:
        return path[m.end():].replace('\\', '/')
    return path


app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 鈹€鈹€ 璁剧疆 Playwright 娴忚鍣ㄨ矾寰勶紙渚挎惡妯″紡锛夆攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = Config.PLAYWRIGHT_BROWSERS_PATH

db.init_app(app)

# 鍏ㄥ眬瀹炰緥
runner = PlaywrightRunner(app.config['SCREENSHOT_ROOT'], app.config['PLAYWRIGHT_TIMEOUT'])
diff_engine = DiffEngine(app.config['DIFF_ROOT'])
report_gen = ReportGenerator()

# 鍏ㄥ眬浠诲姟鐘舵€?
task_progress = {}


def ensure_dirs():
    for d in [app.config['SCREENSHOT_ROOT'], app.config['BASELINE_ROOT'], app.config['DIFF_ROOT']]:
        Path(d).mkdir(parents=True, exist_ok=True)


def run_test_async(project_id, task_id):
    """异步执行测试任务，通过 socketio 推送进度"""
    with app.app_context():
        project = Project.query.get(project_id)
        if not project:
            return

        configs = TestConfig.query.filter_by(project_id=project_id, is_active=True).all()
        if not configs:
            task_progress[task_id]['status'] = 'failed'
            task_progress[task_id]['error'] = 'No active configs'
            socketio.emit('test_progress', task_progress[task_id], namespace='/test')
            return

        task_progress[task_id]['total'] = len(configs)
        task_progress[task_id]['status'] = 'running'

        results = []

        for idx, cfg in enumerate(configs):
            res = runner.capture(
                url=project.url,
                width=cfg.width,
                height=cfg.height,
                browser=cfg.browser,
                device_scale=cfg.device_scale,
                task_id=task_id
            )

            test_run = TestRun(
                project_id=project_id,
                config_id=cfg.id,
                screenshot_path=res.get('screenshot_path', ''),
                status='completed' if res['success'] else 'failed',
                error_message=res.get('error', '')
            )
            db.session.add(test_run)
            db.session.commit()

            # 濡傛灉鏈夊熀绾垮垯瀵规瘮
            if res['success'] and cfg.browser:
                baseline_dir = Path(app.config['BASELINE_ROOT']) / str(project_id)
                baseline_path = baseline_dir / cfg.resolution / f"{cfg.browser}.png"
                screenshot_path = res['screenshot_path']

                if baseline_path.exists():
                    diff_result = diff_engine.compare(
                        str(baseline_path),
                        screenshot_path,
                        task_id=f"{task_id}_{cfg.resolution}_{cfg.browser}"
                    )
                    test_run.diff_score = diff_result['score']
                    test_run.diff_path = diff_result.get('diff_path', '')
                    test_run.baseline_path = str(baseline_path)
                    db.session.commit()

            results.append({
                'config_id': cfg.id,
                'success': res['success'],
                'resolution': cfg.resolution,
                'browser': cfg.browser
            })

            task_progress[task_id]['completed'] = idx + 1
            task_progress[task_id]['current'] = f"{cfg.resolution} / {cfg.browser.upper()}"
            socketio.emit('test_progress', task_progress[task_id], namespace='/test')

        task_progress[task_id]['status'] = 'completed'
        socketio.emit('test_complete', {'task_id': task_id, 'results': results}, namespace='/test')


# 鈹€鈹€鈹€ 璺敱 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

@app.route('/')
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('index.html', projects=projects,
                           default_resolutions=DEFAULT_RESOLUTIONS,
                           default_browsers=DEFAULT_BROWSERS)


@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    configs = TestConfig.query.filter_by(project_id=project_id).all()
    runs = TestRun.query.filter_by(project_id=project_id).order_by(
        TestRun.created_at.desc()
    ).limit(50).all()
    return render_template('run_test.html', project=project, configs=configs, runs=runs)


@app.route('/compare/<int:project_id>')
def compare(project_id):
    project = Project.query.get_or_404(project_id)
    runs = TestRun.query.filter_by(project_id=project_id, status='completed').order_by(
        TestRun.created_at.desc()
    ).limit(100).all()
    return render_template('compare.html', project=project, runs=runs)


@app.route('/debug')
def debug_page():
    return render_template('debug.html')


@app.route('/report/<int:project_id>')
def report(project_id):
    project = Project.query.get_or_404(project_id)
    runs = TestRun.query.filter_by(project_id=project_id, status='completed').order_by(
        TestRun.created_at.desc()
    ).all()
    return render_template('report.html', project=project, runs=runs)


# 鈹€鈹€鈹€ API 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

@app.route('/api/projects', methods=['GET'])
def api_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'url': p.url,
        'description': p.description,
        'created_at': p.created_at.isoformat(),
        'config_count': p.configs.count(),
        'run_count': p.test_runs.count()
    } for p in projects])


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    data = request.get_json()
    name = data.get('name', '').strip()
    url = data.get('url', '').strip()
    description = data.get('description', '')

    if not name or not url:
        return jsonify({'error': 'name and url required'}), 400

    project = Project(name=name, url=url, description=description)
    db.session.add(project)
    db.session.commit()
    return jsonify({'id': project.id, 'name': project.name}), 201


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/projects/<int:project_id>/configs', methods=['GET'])
def api_get_configs(project_id):
    configs = TestConfig.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': c.id, 'resolution': c.resolution,
        'width': c.width, 'height': c.height,
        'device_scale': c.device_scale,
        'browser': c.browser, 'is_active': c.is_active
    } for c in configs])


@app.route('/api/projects/<int:project_id>/configs', methods=['POST'])
def api_add_config(project_id):
    data = request.get_json()
    project = Project.query.get_or_404(project_id)

    width = data.get('width')
    height = data.get('height')
    browser = data.get('browser', 'chromium')
    device_scale = data.get('device_scale', 1)

    if not width or not height:
        return jsonify({'error': 'width and height required'}), 400

    resolution = f"{width}x{height}"

    cfg = TestConfig(
        project_id=project_id,
        resolution=resolution,
        width=int(width),
        height=int(height),
        browser=browser,
        device_scale=int(device_scale),
        is_active=True
    )
    db.session.add(cfg)
    db.session.commit()
    return jsonify({'id': cfg.id, 'resolution': cfg.resolution, 'browser': cfg.browser})


@app.route('/api/projects/<int:project_id>/configs/<int:config_id>', methods=['DELETE'])
def api_delete_config(project_id, config_id):
    cfg = TestConfig.query.get_or_404(config_id)
    db.session.delete(cfg)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/api/projects/<int:project_id>/run', methods=['POST'])
def api_run_test(project_id):
    project = Project.query.get_or_404(project_id)
    task_id = uuid.uuid4().hex[:12]

    task_progress[task_id] = {
        'task_id': task_id,
        'project_id': project_id,
        'status': 'pending',
        'total': 0,
        'completed': 0,
        'current': '',
        'error': ''
    }

    thread = threading.Thread(target=run_test_async, args=(project_id, task_id))
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id, 'status': 'started'})


def _to_url_path(path, folder):
    """Convert absolute Windows path to URL-relative path."""
    if not path:
        return ''
    import re
    m = re.search(rf'{folder}[\\/]', path)
    if m:
        return path[m.end():].replace('\\', '/')
    return path.replace('\\', '/')

@app.route('/api/test-runs/<int:run_id>', methods=['GET'])
def api_get_run(run_id):
    run = TestRun.query.get_or_404(run_id)
    return jsonify({
        'id': run.id,
        'project_id': run.project_id,
        'resolution': run.get_resolution(),
        'browser': run.get_browser(),
        'screenshot_path': _to_url_path(run.screenshot_path, 'screenshots'),
        'baseline_path': _to_url_path(run.baseline_path, 'baselines'),
        'diff_path': _to_url_path(run.diff_path, 'diffs'),
        'diff_score': run.diff_score,
        'status': run.status,
        'error_message': run.error_message,
        'created_at': run.created_at.isoformat() if run.created_at else None
    })


@app.route('/api/test-runs/<int:run_id>/baseline', methods=['POST'])
def api_set_baseline(run_id):
    run = TestRun.query.get_or_404(run_id)
    if not run.screenshot_path or not Path(run.screenshot_path).exists():
        return jsonify({'error': 'No screenshot available'}), 400

    cfg = run.config
    baseline_dir = Path(app.config['BASELINE_ROOT']) / str(run.project_id) / cfg.resolution
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = baseline_dir / f"{cfg.browser}.png"

    import shutil
    shutil.copy2(run.screenshot_path, baseline_path)

    run.baseline_path = str(baseline_path)
    db.session.commit()
    return jsonify({'baseline_path': str(baseline_path)})


@app.route('/api/compare', methods=['GET'])
def api_compare():
    """瀵规瘮涓や釜 TestRun"""
    run_a_id = request.args.get('run_a', type=int)
    run_b_id = request.args.get('run_b', type=int)
    if not run_a_id or not run_b_id:
        return jsonify({'error': 'run_a and run_b required'}), 400

    run_a = TestRun.query.get_or_404(run_a_id)
    run_b = TestRun.query.get_or_404(run_b_id)

    if not run_a.screenshot_path or not run_b.screenshot_path:
        return jsonify({'error': 'Missing screenshots'}), 400

    result = diff_engine.compare(run_a.screenshot_path, run_b.screenshot_path,
                                  task_id=f"cmp_{run_a_id}_{run_b_id}")

    return jsonify({
        'score': result['score'],
        'diff_path': _to_url_path(result['diff_path'], 'diffs'),
        'diff_pixels': result['diff_pixels'],
        'total_pixels': result['total_pixels']
    })


@app.route('/api/report/<int:project_id>', methods=['GET'])
def api_get_report(project_id):
    project = Project.query.get_or_404(project_id)
    runs = TestRun.query.filter_by(project_id=project_id, status='completed').order_by(
        TestRun.created_at.desc()
    ).all()

    data = [{
        'resolution': r.get_resolution(),
        'browser': r.get_browser(),
        'diff_score': r.diff_score,
        'screenshot_path': r.screenshot_path,
        'baseline_path': r.baseline_path,
        'diff_path': r.diff_path,
        'status': r.status,
        'created_at': r.created_at.isoformat() if r.created_at else None
    } for r in runs]

    format = request.args.get('format', 'html')
    if format == 'pdf':
        path = report_gen.generate_pdf(project.name, data)
        return send_from_directory(Path(path).parent, Path(path).name,
                                   as_attachment=True, download_name=Path(path).name)
    else:
        path = report_gen.generate_html_report(project.name, data, project_url=project.url)
        return send_from_directory(Path(path).parent, Path(path).name,
                                   as_attachment=True, download_name=Path(path).name)


# 鈹€鈹€鈹€ 鎴浘鏂囦欢鏈嶅姟 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(app.config['SCREENSHOT_ROOT'], filename)


@app.route('/baselines/<path:filename>')
def serve_baseline(filename):
    return send_from_directory(app.config['BASELINE_ROOT'], filename)


@app.route('/diffs/<path:filename>')
def serve_diff(filename):
    return send_from_directory(app.config['DIFF_ROOT'], filename)


# 鈹€鈹€鈹€ SocketIO 浜嬩欢 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

@socketio.on('connect', namespace='/test')
def test_connect():
    emit('connected', {'msg': 'connected'})


# 鈹€鈹€鈹€ 鍒濆鍖?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

if __name__ == '__main__':
    ensure_dirs()
    with app.app_context():
        db.create_all()
    print("\n  [OK] Compatibility Test Platform started")
    print(f"  [URL] http://localhost:5000")
    print(f"  [END] Press Ctrl+C to stop\n")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
