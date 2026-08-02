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


# 预置演示数据（Vercel 冷启动时自动恢复）
# 包含 11 条用户真实收藏的视频数据（含封面图、AI 分析结果）
DEMO_VIDEOS = [
    {
        "url": "https://v.douyin.com/owuA_MZHJOE/",
        "video_url": "",
        "title": "【抖音独家精选】《被裁掉的女孩》综艺番外～下饭篇！ 没什么正事儿，就是给大家乐一下！",
        "author": "菲菲",
        "author_avatar": "https://p3.douyinpic.com/aweme/100x100/aweme-avatar/tos-cn-avt-0015_30f448e76898ba31bfd37ae19a548dad.jpeg",
        "description": "没什么正事儿，就是给大家乐一下！综艺番外下饭篇",
        "tags": ["抖音精选app", "创作阶梯计划", "抖音AI创作大赛", "开放赛道", "小云雀创作者计划"],
        "cover_url": "",
        "category": "娱乐综艺（综艺搞笑）",
        "like_count": 174032,
        "comment_count": 3268,
        "share_count": 36315,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "一段《被裁掉的女孩》综艺的番外篇，主打轻松娱乐，旨在为观众提供下饭时的欢乐内容。视频以宣传海报为主要画面，展示了多位角色的出场，营造了轻松热闹的氛围。整体内容以搞笑、日常互动为主，没有深度主题。",
        "ai_keypoints": ["《被裁掉的女孩》综艺番外篇，定位为轻松下饭内容", "多位角色轮番登场，氛围热闹轻松", "内容偏搞笑和日常互动，无深度主题", "带有抖音平台推广标签如AI创作大赛等"],
        "ai_tags": ["综艺番外", "下饭视频", "轻松娱乐", "抖音精选", "搞笑日常"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgJ/",
        "video_url": "",
        "title": "#保姆心声陆家保命指南 #保姆心声陆家保命指南后续",
        "author": "陆家",
        "author_avatar": "",
        "description": "保姆心声陆家保命指南系列短片",
        "tags": ["保姆心声", "陆家保命指南"],
        "cover_url": "",
        "category": "其他",
        "like_count": 32110,
        "comment_count": 247,
        "share_count": 129,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "保姆心声陆家保命指南系列短片，内容围绕家庭生活场景中的趣味互动展开，属于生活类短剧内容。",
        "ai_keypoints": ["保姆陆家的日常生活趣味短片", "家庭场景下的幽默互动", "系列化内容，有后续集数"],
        "ai_tags": ["保姆心声", "陆家保命指南", "生活短剧"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgK/",
        "video_url": "",
        "title": "【抖音精选独家】《零号档案》File Zero【6】 对面不相见，用心同用兵 得势侵吞远，乘危",
        "author": "抖音精选",
        "author_avatar": "",
        "description": "零号档案 File Zero 第六集，AI 生成的悬疑推理短剧，围绕案件展开层层递进的对决与博弈。",
        "tags": ["抖音精选app", "创作阶梯计划", "抖音AI创作大赛", "开放赛道"],
        "cover_url": "",
        "category": "AI内容创作",
        "like_count": 1015055,
        "comment_count": 13421,
        "share_count": 187283,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "《零号档案》是一部AI生成的悬疑推理短剧。本集围绕案件展开，各方势力在复杂局势中博弈对决，剧情层层递进。作品展现了AI在叙事类内容创作中的潜力，视觉效果和氛围营造颇具水准。",
        "ai_keypoints": ["AI生成的悬疑推理短剧《零号档案》第六集", "围绕案件展开的势力博弈与智斗", "AIGC技术赋能高质量叙事创作", "适合悬疑推理和短剧爱好者"],
        "ai_tags": ["AIGC", "AI短剧", "AI动漫", "国漫", "零号档案", "悬疑"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgL/",
        "video_url": "",
        "title": "梦境予你圆满 现实予他成全 #抖音ai创作大赛 #开放赛道 #拾光故事",
        "author": "拾光故事",
        "author_avatar": "",
        "description": "抖音AI创作大赛参赛作品，AI生成的原创动漫剧情片。梦境与现实对照，讲述一个关于成全与放手的感人故事。",
        "tags": ["抖音ai创作大赛", "开放赛道", "拾光故事"],
        "cover_url": "",
        "category": "AI内容创作",
        "like_count": 463240,
        "comment_count": 7542,
        "share_count": 165818,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "一部AI生成的原创动漫剧情片，参加抖音AI创作大赛。视频通过梦境与现实的对照，讲述了一个关于成全与放手的故事。画面富有诗意和情感张力，展现了AI动漫创作在情感表达上的可能性。",
        "ai_keypoints": ["AI生成的原创动漫剧情片", "梦境与现实对照的叙事结构", "传达关于成全与放手的情感主题", "抖音AI创作大赛参赛作品", "画面富有诗意与情感表达力"],
        "ai_tags": ["AIGC", "AI动画", "原创动漫", "梦境", "成全", "情感"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgM/",
        "video_url": "",
        "title": "【我凭发疯出道1-5合集】一口气创飞所有人 #AIGC #AI动漫 #AI动画 #国漫",
        "author": "我凭发疯出道",
        "author_avatar": "",
        "description": "AI 生成的动漫短剧合集，1-5集一口气看完。主角通过发疯式行为在职场逆袭的搞笑故事。",
        "tags": ["AIGC", "AI动漫", "AI动画", "国漫"],
        "cover_url": "",
        "category": "AI内容创作",
        "like_count": 244577,
        "comment_count": 2136,
        "share_count": 63204,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "一部AI生成的动漫短剧合集《我凭发疯出道》1-5集，讲述主角通过发疯式行为在职场逆袭的搞笑故事。作品呈现了AI在动漫创作领域的应用潜力，画面风格独特，剧情紧凑偏轻松搞笑路线。",
        "ai_keypoints": ["AI生成的国漫短剧，5集合一完整故事线", "主角通过出格行为对抗职场不公，爽文式逆袭", "AIGC技术赋能动漫创作，画面质量可圈可点", "搞笑+逆袭双线并行，适合喜欢爽漫的观众"],
        "ai_tags": ["AIGC", "AI动漫", "AI动画", "国漫", "逆袭", "搞笑短剧"],
    },
    {
        "url": "https://v.douyin.com/i2k3jZgN/",
        "video_url": "",
        "title": "【归墟】第一集 这是一个由失踪案开始的逃亡、废土与新物种时代的原创长篇故事 从第一只巨",
        "author": "归墟",
        "author_avatar": "",
        "description": "AI 生成的原创科幻短剧《归墟》第一集。从失踪案引入，展开一个末日废土世界，巨型生物出现后城市失控。",
        "tags": ["AI短剧", "归墟", "科幻"],
        "cover_url": "",
        "category": "AI内容创作",
        "like_count": 51808,
        "comment_count": 960,
        "share_count": 28677,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "这是一部AI生成的原创科幻短剧《归墟》的第一集。故事从一宗失踪案引入，展开了一个末日废土世界。巨型生物出现后城市迅速失控，幸存者为求生而踏上未知旅途。作品展现了AIGC在科幻题材创作上的想象力。",
        "ai_keypoints": ["AI生成的原创科幻短剧《归墟》第一集", "从失踪案引入末日废土世界观", "巨型生物失控带来生存危机", "原创长篇故事，世界观宏大"],
        "ai_tags": ["AI短剧", "AIGC", "科幻", "末日废土", "原创动画", "归墟"],
    },
    # === 以下为 2026-08-03 新补充的视频（含真实封面） ===
    {
        "url": "https://v.douyin.com/0OdYLSuEaA4/",
        "video_url": "",
        "title": "假面之下，英雄新生。 #英雄主义 #蜘蛛侠4 #蜘蛛侠崭新之日",
        "author": "高冷男神刘德柱",
        "author_avatar": "",
        "description": "假面之下，英雄新生。蜘蛛侠主题的AI生成英雄主义短片。",
        "tags": ["英雄主义", "蜘蛛侠4", "蜘蛛侠崭新之日", "漫威"],
        "cover_url": "https://p26-sign.douyinpic.com/tos-cn-i-0813c000-ce/oUawVAgnaPRlGMkSAAA9iIBIAABiBfXACAkPIE~tplv-dy-360p.jpeg",
        "category": "AI内容创作",
        "like_count": 35805,
        "comment_count": 1160,
        "share_count": 5072,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "以蜘蛛侠为核心的AI生成英雄主义短片，聚焦于假面之下的英雄新生主题，围绕蜘蛛侠4的崭新之日展开叙事。内容融合漫威超级英雄元素与情感表达，展现了AIGC在英雄题材创作中的应用。",
        "ai_keypoints": ["AI生成的蜘蛛侠主题英雄主义短片", "假面之下英雄新生的叙事主题", "融合漫威元素与情感化表达", "AIGC技术在英雄题材内容创作中的应用"],
        "ai_tags": ["蜘蛛侠", "英雄主义", "AIGC", "漫威", "超级英雄", "AI内容创作"],
    },
    {
        "url": "https://v.douyin.com/EuYo3S4dAKs/",
        "video_url": "",
        "title": "#ai从业者 #Workbuddy #OPC #ai风口怎么抓 #ai从业者",
        "author": "合一说AI效能",
        "author_avatar": "",
        "description": "AI从业者创业与职业发展探讨，围绕如何抓住AI风口、Workbuddy和OPC等协作工具展开。",
        "tags": ["ai从业者", "Workbuddy", "OPC", "ai风口怎么抓"],
        "cover_url": "https://p3-sign.douyinpic.com/tos-cn-i-0813c001/oQex5WVACAIIA7AfHIG50pQpcIA6t72elGA0D~tplv-dy-360p.jpeg",
        "category": "AI工具应用",
        "like_count": 9630,
        "comment_count": 2638,
        "share_count": 2585,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "聚焦AI从业者创业与职业发展的现实问题，围绕如何抓住当前AI风口、AI创业路径、协作工具（Workbuddy、OPC）应用展开。面向AI开发者或从业者，强调实操经验和行业趋势判断。",
        "ai_keypoints": ["AI从业者的创业机会与职业路径分析", "Workbuddy和OPC等AI协作工具的实践应用", "当前AI风口趋势与从业者应对策略", "面向AI开发者和行业从业者的经验分享"],
        "ai_tags": ["AI创业", "AI风口", "AI从业者", "Workbuddy", "OPC", "职业发展", "AIGC"],
    },
    {
        "url": "https://v.douyin.com/basDnfn_r6o/",
        "video_url": "",
        "title": "前辈们，是你们回来看我们了吗#八一建军节 #江 #延长 #爱国教育 #革命历史",
        "author": "大娱乐家",
        "author_avatar": "",
        "description": "八一建军节感动短片，结合江边场景，表达对革命前辈的缅怀与崇敬。",
        "tags": ["八一建军节", "江", "延长", "爱国教育", "革命历史"],
        "cover_url": "https://p9-sign.douyinpic.com/tos-cn-i-dy/eae4d3694a554cd3a28ed8fbdabf38f8~tplv-dy-360p.jpeg",
        "category": "通识/科普",
        "like_count": 178910,
        "comment_count": 1935,
        "share_count": 26835,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "八一建军节主题的感动短片，结合江边场景与历史影像，表达对革命前辈的缅怀与崇敬。通过富有感染力的视觉语言和深情朗诵，唤起对革命历史的记忆与敬意，营造庄重而温暖的氛围。",
        "ai_keypoints": ["八一建军节主题感动短片", "对革命前辈的缅怀与崇敬表达", "结合江边场景与历史影像的视觉叙事", "激发爱国情感与历史记忆"],
        "ai_tags": ["八一建军节", "致敬", "爱国教育", "革命历史", "感动短片", "红色文化"],
    },
    {
        "url": "https://v.douyin.com/s2qCXmZPkcg/",
        "video_url": "",
        "title": "秒秒guo的vibe coding的音乐播放器产品 #vibecoding #coding",
        "author": "AI乐未来",
        "author_avatar": "",
        "description": "展示用vibe coding方式构建音乐播放器产品，强调在轻松氛围中进行代码开发。",
        "tags": ["vibecoding", "coding"],
        "cover_url": "https://p11-sign.douyinpic.com/tos-cn-p-0015/ogAmAAPqDERBR9MIiFvfBFGbFDydPxE59GU~tplv-dy-360p.jpeg",
        "category": "AI工具应用",
        "like_count": 30,
        "comment_count": 3,
        "share_count": 6,
        "duration": 0,
        "analyze_status": "done",
        "ai_summary": "展示了一个由创作者'秒秒guo'打造的音乐播放器产品，聚焦于vibe coding（氛围编程）概念，强调在轻松、创意式的氛围中进行代码开发。产品展示融合了AI编程工具（如Claude）的实践应用，旨在降低编程门槛。",
        "ai_keypoints": ["vibe coding氛围编程概念的实际应用演示", "AI辅助音乐播放器产品开发流程", "Claude等AI工具在编程中的实践", "面向零基础开发者的编程体验"],
        "ai_tags": ["vibe coding", "AI编程工具", "音乐播放器", "Claude", "创作者工具", "AI开发应用"],
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
