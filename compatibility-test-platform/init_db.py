#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ScreenDiff 数据库初始化脚本
运行此脚本创建数据库和示例数据
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.database import Project, TestConfig, TestRun


def init_db():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("✅ 数据库表已创建")
        
        # 检查是否已有数据
        if Project.query.count() == 0:
            # 创建示例项目
            sample_project = Project(
                name="示例项目",
                url="https://www.example.com",
                description="这是一个示例项目，用于演示 ScreenDiff 的功能"
            )
            db.session.add(sample_project)
            db.session.commit()
            print("✅ 示例项目已创建")
        else:
            print("ℹ️  数据库已有数据，跳过示例创建")


def reset_db():
    """重置数据库（删除并重建）"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ 数据库已重置")


if __name__ == "__main__":
    print("=" * 50)
    print("ScreenDiff 数据库初始化")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        confirm = input("⚠️  确定要重置数据库吗？所有数据将被删除！(y/N): ")
        if confirm.lower() == 'y':
            reset_db()
    else:
        init_db()
    
    print("\n完成！运行 'python app.py' 启动服务")
