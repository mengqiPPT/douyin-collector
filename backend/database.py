"""数据库模型与初始化"""
import sqlite3
import json
import os
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据库路径：Vercel 环境使用 /tmp，本地使用 data/ 目录
_db_env_path = os.environ.get("DOUYIN_DB_PATH", "")
if _db_env_path:
    DB_PATH = _db_env_path
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "videos.db")


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    # 视频主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            video_url TEXT,
            title TEXT,
            author TEXT,
            author_avatar TEXT DEFAULT '',
            description TEXT,
            tags TEXT,
            cover_url TEXT,
            category TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            like_count INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            share_count INTEGER DEFAULT 0,
            duration INTEGER DEFAULT 0,
            analyze_status TEXT DEFAULT 'pending',
            ai_summary TEXT DEFAULT '',
            ai_keypoints TEXT DEFAULT '',
            ai_tags TEXT DEFAULT '',
            transcribe_text TEXT DEFAULT '',
            analyzed_at TEXT DEFAULT ''
        )
    """)

    # 兼容已有数据库：如果表已存在但缺少新列，自动添加
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(videos)").fetchall()}
    new_cols = {
        "author_avatar": "TEXT DEFAULT ''",
        "like_count": "INTEGER DEFAULT 0",
        "comment_count": "INTEGER DEFAULT 0",
        "share_count": "INTEGER DEFAULT 0",
        "duration": "INTEGER DEFAULT 0",
        "analyze_status": "TEXT DEFAULT 'pending'",
        "ai_summary": "TEXT DEFAULT ''",
        "ai_keypoints": "TEXT DEFAULT ''",
        "ai_tags": "TEXT DEFAULT ''",
        "transcribe_text": "TEXT DEFAULT ''",
        "analyzed_at": "TEXT DEFAULT ''",
    }
    for col, col_def in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE videos ADD COLUMN {col} {col_def}")

    # FTS5 虚拟表，用于全文搜索
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts
        USING fts5(
            title, description, tags, author,
            content='videos',
            content_rowid='id'
        )
    """)

    # 插入触发器：同步数据到 FTS 表
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_ai AFTER INSERT ON videos BEGIN
            INSERT INTO videos_fts(rowid, title, description, tags, author)
            VALUES (new.id, new.title, new.description, new.tags, new.author);
        END
    """)

    # 删除触发器
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_ad AFTER DELETE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, title, description, tags, author)
            VALUES ('delete', old.id, old.title, old.description, old.tags, old.author);
        END
    """)

    # 更新触发器
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS videos_au AFTER UPDATE ON videos BEGIN
            INSERT INTO videos_fts(videos_fts, rowid, title, description, tags, author)
            VALUES ('delete', old.id, old.title, old.description, old.tags, old.author);
            INSERT INTO videos_fts(rowid, title, description, tags, author)
            VALUES (new.id, new.title, new.description, new.tags, new.author);
        END
    """)

    conn.commit()
    conn.close()


DEMO_VIDEOS = [
    {
        "url": "https://v.douyin.com/i2k3jZgF",
        "video_url": "",
        "title": "AI 绘画入门教程：Stable Diffusion 零基础教学",
        "author": "AI创作营",
        "author_avatar": "",
        "description": "Stable Diffusion 零基础教学，从安装到出图全流程讲解，包含提示词编写技巧、ControlNet 使用方法、LoRA 模型训练入门。",
        "tags": ["AI", "绘画", "教程"],
        "cover_url": "",
        "category": "科技",
        "like_count": 18400,
        "comment_count": 2200,
        "share_count": 9900,
        "duration": 180,
        "analyze_status": "done",
        "ai_summary": "本视频系统介绍了 Stable Diffusion AI 绘画工具的完整使用流程，涵盖环境搭建、模型选择、提示词编写、ControlNet 控制及 LoRA 训练等核心技能。",
        "ai_keypoints": ["Stable Diffusion 环境配置与模型下载", "提示词(Prompt)编写技巧与负面提示词", "ControlNet 精准控制构图与姿态", "LoRA 模型训练入门方法", "ComfyUI 工作流基础介绍"],
        "ai_tags": ["AI绘画", "StableDiffusion", "教程"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgG",
        "video_url": "",
        "title": "Python 自动化办公：用脚本处理 Excel 报表",
        "author": "编程达人",
        "author_avatar": "",
        "description": "手把手教你用 Python 的 openpyxl 和 pandas 库自动化处理 Excel 报表，包含数据读取、批量格式化、图表生成、邮件自动发送等实战技巧。",
        "tags": ["Python", "Excel", "办公自动化"],
        "cover_url": "",
        "category": "编程",
        "like_count": 12000,
        "comment_count": 720,
        "share_count": 2100,
        "duration": 240,
        "analyze_status": "done",
        "ai_summary": "本视频演示了如何用 Python 自动化处理 Excel 报表，从数据读取、批量格式化到图表生成和邮件自动发送，帮助办公人员大幅提升工作效率。",
        "ai_keypoints": ["openpyxl 库读取和写入 Excel 文件", "pandas 数据清洗与格式化技巧", "批量生成数据图表和可视化", "SMTP 邮件自动发送报表", "实际办公场景案例演示"],
        "ai_tags": ["Python", "办公自动化", "Excel"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgH",
        "video_url": "",
        "title": "深度工作法：如何在高干扰环境中保持专注",
        "author": "效率研究所",
        "author_avatar": "",
        "description": "深度工作法核心原理解析，番茄工作法进阶版，数字工具断舍离，专注力训练技巧，适合知识工作者和学生群体的效率提升指南。",
        "tags": ["效率", "专注", "学习方法"],
        "cover_url": "",
        "category": "教育",
        "like_count": 19200,
        "comment_count": 5500,
        "share_count": 3000,
        "duration": 300,
        "analyze_status": "done",
        "ai_summary": "本视频解析了深度工作法的核心原理，提供了番茄工作法进阶版、数字工具断舍离策略和专注力训练技巧，帮助用户在干扰环境中提升工作效率。",
        "ai_keypoints": ["深度工作法核心原理：注意力残余效应", "番茄工作法进阶版：动态调整专注时长", "数字工具断舍离：减少干扰源", "注意力训练：冥想与正念技巧", "环境设计：打造深度工作空间"],
        "ai_tags": ["效率", "学习方法", "专注力"],
    },
]


def seed_demo_data():
    """插入预置演示数据（仅当数据库为空时）

    适用于 Vercel Serverless 环境，实例回收后自动重建演示数据，
    确保在线 Demo 始终有内容展示。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 检查是否已有数据
    count = cursor.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    if count > 0:
        conn.close()
        return

    logger.info("数据库为空，插入预置演示数据...")
    created_at = datetime.now().isoformat(sep=" ", timespec="seconds")

    for demo in DEMO_VIDEOS:
        analyzed_at = created_at if demo.get("analyze_status") == "done" else ""
        tags_json = json.dumps(demo.get("tags", []), ensure_ascii=False)
        keypoints_json = json.dumps(demo.get("ai_keypoints", []), ensure_ascii=False)
        ai_tags_json = json.dumps(demo.get("ai_tags", []), ensure_ascii=False)

        cursor.execute(
            """INSERT INTO videos (
                url, video_url, title, author, author_avatar, description, tags,
                cover_url, category, created_at, like_count, comment_count, share_count, duration,
                analyze_status, ai_summary, ai_keypoints, ai_tags, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                demo["url"], demo["video_url"], demo["title"], demo["author"],
                demo["author_avatar"], demo["description"], tags_json,
                demo["cover_url"], demo["category"], created_at,
                demo["like_count"], demo["comment_count"], demo["share_count"], demo["duration"],
                demo["analyze_status"], demo["ai_summary"], keypoints_json, ai_tags_json, analyzed_at
            ),
        )

    conn.commit()
    conn.close()
    logger.info(f"已插入 {len(DEMO_VIDEOS)} 条预置演示数据")


def insert_video(url, video_url, title, author, description, tags, cover_url, category="",
                  author_avatar="", like_count=0, comment_count=0, share_count=0, duration=0):
    """插入一条视频记录"""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    tags_json = json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else tags
    cursor.execute(
        """INSERT INTO videos (url, video_url, title, author, author_avatar, description, tags,
           cover_url, category, created_at, like_count, comment_count, share_count, duration)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (url, video_url, title, author, author_avatar, description, tags_json,
         cover_url, category, created_at, like_count, comment_count, share_count, duration),
    )
    vid = cursor.lastrowid
    conn.commit()
    conn.close()
    return vid


def get_video(vid):
    """查询单条视频"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM videos WHERE id = ?", (vid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_video_by_url(url):
    """按 URL 查找视频，用于重复检测"""
    if not url:
        return None
    conn = get_connection()
    # 同时匹配原始链接和重定向后的链接
    row = conn.execute(
        "SELECT * FROM videos WHERE url = ? OR url LIKE ?",
        (url, f"%{url.split('/video/')[-1] if '/video/' in url else url}%")
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _sanitize_fts5_query(keyword):
    """对 FTS5 搜索关键词进行安全处理

    FTS5 语法中特殊字符包括：-  " ( ) : / backslash ^ $ ~ * < > 等
    不处理会导致查询异常（SQL语法错误）而非注入攻击
    策略：将整个短语用双引号包裹，实现字面匹配
    """
    if not keyword:
        return keyword
    # 去除可能破坏 FTS5 查询的特殊字符
    # 保留中文、字母、数字和常用标点
    safe = re.sub(r'["*\-()~^:<>=/\\]', ' ', keyword)
    safe = re.sub(r'\s+', ' ', safe).strip()
    if not safe:
        return safe
    # 按空格分词，每个词用双引号包裹避免 FTS5 语法解析
    terms = safe.split()
    if len(terms) == 1:
        return f'"{terms[0]}"'
    # 多词搜索：每个词都独立引号包裹
    return ' '.join(f'"{t}"' for t in terms)


def list_videos(page=1, size=20, keyword=None, category=None):
    """分页查询视频列表，支持关键词全文搜索和分类过滤"""
    # 对 FTS5 搜索关键词做安全处理
    fts_keyword = _sanitize_fts5_query(keyword) if keyword else None
    conn = get_connection()
    offset = (page - 1) * size

    if keyword:
        # 先用 FTS5 全文搜索 title/description/tags/author
        # 再用 LIKE 补充搜索 AI 分析字段（ai_summary, ai_keypoints, ai_tags）
        # 用 UNION 合并两路结果去重
        like_kw = f"%{keyword}%"

        if fts_keyword:
            # FTS5 安全关键词可用，正常走 MATCH + LIKE 双路搜索
            sql = """
                SELECT * FROM (
                    SELECT v.* FROM videos v
                    JOIN videos_fts f ON v.id = f.rowid
                    WHERE videos_fts MATCH ?
                    UNION
                    SELECT * FROM videos
                    WHERE ai_summary LIKE ? OR ai_keypoints LIKE ? OR ai_tags LIKE ?
                )
            """
            params = [fts_keyword, like_kw, like_kw, like_kw]
        else:
            # 关键词全是特殊字符，仅用 LIKE 搜索
            sql = """
                SELECT * FROM videos
                WHERE title LIKE ? OR description LIKE ? OR tags LIKE ? OR author LIKE ?
                   OR ai_summary LIKE ? OR ai_keypoints LIKE ? OR ai_tags LIKE ?
            """
            params = [like_kw, like_kw, like_kw, like_kw, like_kw, like_kw, like_kw]

        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([size, offset])
    else:
        sql = "SELECT * FROM videos"
        params = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([size, offset])

    rows = conn.execute(sql, params).fetchall()

    count_sql = "SELECT COUNT(*) as total FROM videos"
    count_params = []
    if keyword:
        like_kw = f"%{keyword}%"
        if fts_keyword:
            count_sql = """
                SELECT COUNT(*) as total FROM (
                    SELECT v.id FROM videos v
                    JOIN videos_fts f ON v.id = f.rowid
                    WHERE videos_fts MATCH ?
                    UNION
                    SELECT id FROM videos
                    WHERE ai_summary LIKE ? OR ai_keypoints LIKE ? OR ai_tags LIKE ?
                )
            """
            count_params = [fts_keyword, like_kw, like_kw, like_kw]
            if category:
                count_sql = """
                    SELECT COUNT(*) as total FROM (
                        SELECT v.id, v.category FROM videos v
                        JOIN videos_fts f ON v.id = f.rowid
                        WHERE videos_fts MATCH ?
                        UNION
                        SELECT id, category FROM videos
                        WHERE ai_summary LIKE ? OR ai_keypoints LIKE ? OR ai_tags LIKE ?
                    ) WHERE category = ?
                """
                count_params = [fts_keyword, like_kw, like_kw, like_kw, category]
        else:
            count_sql = """
                SELECT COUNT(*) as total FROM videos
                WHERE title LIKE ? OR description LIKE ? OR tags LIKE ? OR author LIKE ?
                   OR ai_summary LIKE ? OR ai_keypoints LIKE ? OR ai_tags LIKE ?
            """
            count_params = [like_kw, like_kw, like_kw, like_kw, like_kw, like_kw, like_kw]
            if category:
                count_sql += " AND category = ?"
                count_params.append(category)
    elif category:
        count_sql += " WHERE category = ?"
        count_params = [category]

    total = conn.execute(count_sql, count_params).fetchone()["total"]
    conn.close()
    return [dict(r) for r in rows], total


def delete_video(vid):
    """删除视频记录"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM videos WHERE id = ?", (vid,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def list_categories():
    """获取所有分类及每个分类的视频数量"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT category, COUNT(*) as count FROM videos
           WHERE category != '' GROUP BY category ORDER BY count DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_category(vid, category):
    """更新视频分类"""
    conn = get_connection()
    conn.execute("UPDATE videos SET category = ? WHERE id = ?", (category, vid))
    conn.commit()
    conn.close()


def update_analyze_status(vid, status):
    """更新分析状态: pending / analyzing / done / failed"""
    conn = get_connection()
    conn.execute("UPDATE videos SET analyze_status = ? WHERE id = ?", (status, vid))
    conn.commit()
    conn.close()


def update_analyze_result(vid, summary, keypoints, ai_tags, transcribe_text=""):
    """保存 AI 分析结果"""
    conn = get_connection()
    analyzed_at = datetime.now().isoformat(sep=" ", timespec="seconds")
    # 将 list 序列化为 JSON 字符串，避免 SQLite 不支持 list 类型
    keypoints_json = json.dumps(keypoints, ensure_ascii=False) if isinstance(keypoints, list) else (keypoints or "")
    ai_tags_json = json.dumps(ai_tags, ensure_ascii=False) if isinstance(ai_tags, list) else (ai_tags or "")
    conn.execute(
        """UPDATE videos SET
           analyze_status = 'done',
           ai_summary = ?,
           ai_keypoints = ?,
           ai_tags = ?,
           transcribe_text = ?,
           analyzed_at = ?
           WHERE id = ?""",
        (summary, keypoints_json, ai_tags_json, transcribe_text, analyzed_at, vid),
    )
    conn.commit()
    conn.close()
