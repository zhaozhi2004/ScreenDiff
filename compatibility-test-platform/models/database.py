from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    configs = db.relationship('TestConfig', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_runs = db.relationship('TestRun', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def config_count(self):
        return self.configs.count()

    @property
    def run_count(self):
        return self.test_runs.count()


class TestConfig(db.Model):
    __tablename__ = 'test_configs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    resolution = db.Column(db.String(20), nullable=False)  # e.g. "1920x1080"
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    device_scale = db.Column(db.Integer, default=1)
    browser = db.Column(db.String(20), nullable=False)  # chromium/firefox/webkit
    is_active = db.Column(db.Boolean, default=True)

    test_runs = db.relationship('TestRun', backref='config', lazy='dynamic')


class TestRun(db.Model):
    __tablename__ = 'test_runs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    config_id = db.Column(db.Integer, db.ForeignKey('test_configs.id'), nullable=True)
    screenshot_path = db.Column(db.Text, default='')
    baseline_path = db.Column(db.Text, default='')
    diff_path = db.Column(db.Text, default='')
    diff_score = db.Column(db.Float, default=0.0)  # 0.0 ~ 1.0
    status = db.Column(db.String(20), default='pending')  # pending/running/completed/failed
    error_message = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_resolution(self):
        if self.config:
            return self.config.resolution
        return 'unknown'

    def get_browser(self):
        if self.config:
            return self.config.browser
        return 'unknown'
