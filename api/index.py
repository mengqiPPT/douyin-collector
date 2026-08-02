"""Vercel Serverless 入口 — FastAPI 全栈应用

Vercel 通过此文件将 FastAPI 应用作为 Serverless Function 运行。
所有 /api/* 请求由 Vercel 路由到此函数处理。

数据库存储在 /tmp（Vercel 函数实例内），
同一个 warm 实例内的请求共享数据库。
"""
import sys
import os

# 确保能 import 后端模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# 数据库路径 → /tmp（Vercel 唯一可写持久目录）
os.environ["DOUYIN_DB_PATH"] = "/tmp/videos.db"

# 导入 FastAPI app（Vercel 会自动检测 ASGI app）
from main import app
