"""抖音视频链接解析器

从抖音分享链接中提取视频元数据：
- 视频标题、作者、描述、话题标签、封面图URL、视频地址

解析策略（按优先级依次尝试）：
1. 页面内嵌 JSON 数据（aweme_detail / item_list）
2. RENDER_DATA / _ROUTER_DATA 内嵌 JSON（React SSR 数据）
3. SEO meta 标签回退
4. 页面文本回退
"""
import re
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# 移动端 UA - 抖音对移动端会返回含元数据的 HTML
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.0 Mobile/15E148 Safari/604.1"
)

# PC 端 UA - 备选方案
PC_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 抖音短链正则（含下划线和连字符，如 owuA_MZHJOE）
SHORT_URL_PATTERN = re.compile(r"https?://v\.douyin\.com/[A-Za-z0-9_-]+/?")
# 抖音长链正则
LONG_URL_PATTERN = re.compile(r"https?://www\.douyin\.com/video/(\d+)")
# iesdouyin 分享页
IES_PATTERN = re.compile(r"https?://www\.iesdouyin\.com/share/video/(\d+)")


def extract_url(text):
    """从用户输入的分享文本中提取抖音URL"""
    if not text:
        return None
    for pattern in [SHORT_URL_PATTERN, LONG_URL_PATTERN, IES_PATTERN]:
        m = pattern.search(text)
        if m:
            return m.group(0)
    return None


def is_valid_douyin_url(url):
    """校验是否为合法的抖音链接"""
    if not url:
        return False
    return any(p.search(url) for p in [SHORT_URL_PATTERN, LONG_URL_PATTERN, IES_PATTERN])


async def resolve_video_id(url):
    """从抖音链接中解析出 video_id

    - 短链：跟随重定向，从最终 URL 提取
    - 长链/iesdouyin：直接从 URL 中提取
    """
    # 长链直接提取
    m = LONG_URL_PATTERN.search(url)
    if m:
        return m.group(1)

    # iesdouyin 直接提取
    m = IES_PATTERN.search(url)
    if m:
        return m.group(1)

    # 短链需要重定向
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(url, headers={"User-Agent": MOBILE_UA})
        final_url = str(resp.url)
        m = re.search(r"/video/(\d+)", final_url)
        if m:
            return m.group(1)
        # 从 URL 参数中查找
        m = re.search(r"video_id=(\d+)", final_url)
        if m:
            return m.group(1)
    return None


async def _fetch_page(video_id, ua=MOBILE_UA):
    """获取视频页面 HTML"""
    url = f"https://www.iesdouyin.com/share/video/{video_id}/"
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        resp = await client.get(url, headers={"User-Agent": ua})
        if resp.status_code != 200:
            raise RuntimeError(f"页面请求失败: HTTP {resp.status_code}")
        return resp.text.replace("\\u002F", "/")


def _extract_embedded_json(html, video_id):
    """策略 1：从页面内嵌 JSON 数据中提取

    抖音移动端页面中的 _ROUTER_DATA 或 window._SSR_HYDRATED_DATA
    包含了完整的视频信息。
    """
    # 尝试匹配多种内嵌 JSON 模式
    patterns = [
        # 最常见的模式：完整的 item 对象
        r'"item_list"\s*:\s*\[\s*\{.*?"aweme_id"\s*:\s*"' + re.escape(video_id) + r'".*?\}\]',
        # _ROUTER_DATA 模式
        r'<script[^>]*id="RENDER_DATA"[^>]*>(.*?)</script>',
        # __NEXT_DATA__ 模式
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    ]

    for pattern in patterns:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                text = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
                # RENDER_DATA 可能被 URL 编码
                from urllib.parse import unquote
                text = unquote(text)
                data = json.loads(text)
                return _extract_from_json_obj(data, video_id)
            except (json.JSONDecodeError, KeyError):
                continue

    # 直接搜索 desc/nickname 字段（原有逻辑作为回退）
    return None


def _extract_from_json_obj(data, video_id):
    """从解析好的 JSON 对象中提取视频信息（含作者头像、互动数据）"""
    result = {
        "title": "",
        "author": "",
        "author_avatar": "",
        "description": "",
        "tags": [],
        "cover_url": "",
        "video_url": "",
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "duration": 0,
    }

    # 尝试从不同路径获取 item 数据
    item = None
    # 路径 1: app.pageData.itemList[0]
    if "app" in data and "pageData" in data.get("app", {}):
        items = data["app"]["pageData"].get("itemList", [])
        if items:
            item = items[0]
    # 路径 2: item_list 直接在顶层
    if not item and "item_list" in data:
        items = data["item_list"]
        if isinstance(items, list) and items:
            item = items[0]
        elif isinstance(items, dict):
            item = items.get(video_id) or list(items.values())[0] if items else None
    # 路径 3: 顶层直接是 item
    if not item and "aweme_id" in data:
        item = data

    if not item:
        return None

    # --- 基础元数据 ---
    result["description"] = item.get("desc", "")
    result["title"] = result["description"]

    # --- 作者信息 ---
    author_info = item.get("author", {})
    result["author"] = author_info.get("nickname", "")

    # 作者头像（多种可能的字段名）
    avatar = author_info.get("avatar_thumb", {}) or author_info.get("avatar_medium", {}) or author_info.get("avatar_larger", {})
    if not avatar:
        avatar = author_info.get("avatar_168x168", {}) or author_info.get("avatar_300x300", {})
    avatar_urls = avatar.get("url_list", []) if isinstance(avatar, dict) else []
    if not avatar_urls:
        # 直接是字符串 URL
        for key in ("avatar_thumb", "avatar_medium", "avatar_larger", "avatar_168x168", "avatar_300x300"):
            val = author_info.get(key, "")
            if isinstance(val, str) and val.startswith("http"):
                avatar_urls = [val]
                break
    result["author_avatar"] = avatar_urls[0] if avatar_urls else ""

    # --- 标签 ---
    text_extra = item.get("text_extra", [])
    if text_extra:
        result["tags"] = list(dict.fromkeys(
            t.get("hashtag_name", "") for t in text_extra if t.get("hashtag_name")
        ))

    # --- 封面图 ---
    cover = item.get("video", {}).get("cover", {})
    cover_urls = cover.get("url_list", [])
    if cover_urls:
        result["cover_url"] = cover_urls[0]

    # --- 视频地址 ---
    video_info = item.get("video", {})
    play_addr = video_info.get("play_addr", {})
    play_urls = play_addr.get("url_list", [])
    if play_urls:
        result["video_url"] = play_urls[0]

    # --- 时长（毫秒 → 秒） ---
    duration_ms = video_info.get("duration", 0)
    if isinstance(duration_ms, (int, float)):
        result["duration"] = duration_ms // 1000

    # --- 互动数据 ---
    stats = item.get("statistics", {})
    result["like_count"] = stats.get("digg_count", 0) or stats.get("like_count", 0) or 0
    result["comment_count"] = stats.get("comment_count", 0) or 0
    result["share_count"] = stats.get("share_count", 0) or 0

    return result


def _extract_from_simple_parsing(html, video_id):
    """策略 2：用简单正则从内嵌 JSON 片段提取（原有逻辑优化版）

    当完整 JSON 解析失败时，直接搜索关键字段。
    使用更健壮的正则，支持多种格式变体。
    """
    result = {
        "title": "",
        "author": "",
        "author_avatar": "",
        "description": "",
        "tags": [],
        "cover_url": "",
        "video_url": "",
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "duration": 0,
    }

    # --- 提取描述 (desc) ---
    m = re.search(r'"aweme_id"\s*:\s*"' + re.escape(video_id) + r'"[^}]*?"desc"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if not m:
        m = re.search(r'"desc"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if m:
        desc = m.group(1).replace('\\"', '"').replace("\\n", "\n")
        result["description"] = desc
        result["title"] = desc

    # --- 提取作者 (nickname) ---
    m = re.search(r'"author"\s*:\s*\{[^}]*?"nickname"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if not m:
        m = re.search(r'"nickname"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if m:
        result["author"] = m.group(1).replace('\\"', '"')

    # --- 提取标签 (hashtag_name) ---
    tags = re.findall(r'"hashtag_name"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if tags:
        result["tags"] = list(dict.fromkeys(tags))

    # --- 提取封面图 (cover.url_list) ---
    cover_match = re.search(
        r'"cover"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"',
        html,
    )
    if cover_match:
        result["cover_url"] = cover_match.group(1)

    # --- 提取视频地址 (play_addr.url_list) ---
    play_match = re.search(
        r'"play_addr"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"',
        html,
    )
    if play_match:
        result["video_url"] = play_match.group(1)

    # --- 提取作者头像 ---
    avatar_match = re.search(r'"avatar_thumb"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"', html)
    if not avatar_match:
        avatar_match = re.search(r'"avatar_medium"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"', html)
    if not avatar_match:
        avatar_match = re.search(r'"avatar_168x168"\s*:\s*\{[^}]*?"url_list"\s*:\s*\["([^"]+)"', html)
    if avatar_match:
        result["author_avatar"] = avatar_match.group(1)

    # --- 提取互动数据 ---
    # 使用更精确的正则，确保匹配正确的字段位置
    for name, key in [("digg_count", "like_count"), ("comment_count", "comment_count"), ("share_count", "share_count")]:
        # 优先在 statistics 区块内匹配
        m = re.search(rf'"statistics"\s*:\s*\{{[^}}]*?"{name}"\s*:\s*(\d+)', html)
        if m:
            result[key] = int(m.group(1))
        else:
            # 回退：全局匹配，但要求字段名前有引号
            m = re.search(rf'"{name}"\s*:\s*(\d+)', html)
            if m:
                result[key] = int(m.group(1))

    # --- 提取时长 ---
    m = re.search(r'"duration"\s*:\s*(\d+)', html)
    if m:
        result["duration"] = int(m.group(1)) // 1000

    return result


def _extract_from_seo(html, video_id):
    """策略 3：从 SEO meta 标签中提取

    即使页面是 JS 渲染的，通常也会有 meta 标签用于 SEO。
    """
    result = {
        "title": f"抖音视频_{video_id}",
        "author": "",
        "author_avatar": "",
        "description": "",
        "tags": [],
        "cover_url": "",
        "video_url": "",
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
        "duration": 0,
    }

    # meta title
    m = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', html)
    if not m:
        m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        result["title"] = m.group(1).strip()

    # meta description
    m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
    if not m:
        m = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"', html)
    if m:
        meta_desc = m.group(1)
        if " - " in meta_desc:
            result["description"] = meta_desc.split(" - ")[0]
        else:
            result["description"] = meta_desc

    # meta image (og:image)
    m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
    if m:
        result["cover_url"] = m.group(1)

    # meta author/title 中提取作者
    m = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]+)"', html)
    if m:
        result["author"] = m.group(1)

    # 从 og:title 中提取作者（格式: "xxx 的作品"）
    og_title = result["title"]
    author_match = re.search(r'【(.+?)】|"(.+?)"的作品|@(\S+)', og_title)
    if author_match:
        author = author_match.group(1) or author_match.group(2) or author_match.group(3)
        if author:
            result["author"] = author

    return result


async def fetch_video_data(video_id):
    """通过 iesdouyin.com 获取视频页面并提取元数据

    使用三层策略依次尝试：
    1. 完整 JSON 解析（最可靠）
    2. 正则片段提取（中等可靠）
    3. SEO meta 标签（最不可靠但总比没有好）
    """
    html = ""

    # 获取页面
    try:
        html = await _fetch_page(video_id)
    except Exception as e:
        logger.warning(f"获取页面失败: {e}, 尝试 PC UA")
        try:
            html = await _fetch_page(video_id, ua=PC_UA)
        except Exception as e2:
            logger.error(f"PC UA 也失败: {e2}")
            raise RuntimeError(f"无法获取视频页面 (video_id={video_id})")

    if not html or len(html) < 500:
        raise RuntimeError(f"页面内容为空或过短 (video_id={video_id})")

    # 策略 1: 完整 JSON 解析
    result = _extract_embedded_json(html, video_id)
    if result and result.get("description"):
        logger.info(f"策略1(JSON解析)成功: video_id={video_id}")
        return result

    # 策略 2: 正则片段提取
    result = _extract_from_simple_parsing(html, video_id)
    if result and result.get("description"):
        logger.info(f"策略2(正则提取)成功: video_id={video_id}")
        result["title"] = _normalize_title(result.get("title", ""), result.get("description", ""))
        return result

    # 策略 3: SEO meta 标签
    result = _extract_from_seo(html, video_id)
    logger.info(f"策略3(SEO提取): video_id={video_id}, has_desc={bool(result.get('description'))}")
    result["title"] = _normalize_title(result.get("title", ""), result.get("description", ""))
    return result


def _normalize_title(title, description):
    """标题规范化：截断过长标题，取描述前 50 字"""
    if not title or title.startswith("抖音视频_"):
        if description:
            return description[:50]
    if len(title) > 80:
        return title[:80]
    return title


async def parse_douyin_url(share_text):
    """完整解析流程：从分享文本中提取 URL -> 解析视频元数据

    Args:
        share_text: 用户粘贴的分享文本（可能包含URL和描述文字）

    Returns:
        dict with keys: title, author, description, tags, cover_url, video_url, source_url
        or None if parsing fails
    """
    url = extract_url(share_text)
    if not url:
        logger.warning("未能从分享文本中提取 URL")
        return None

    # 解析 video_id
    video_id = await resolve_video_id(url)
    if not video_id:
        logger.warning(f"无法解析 video_id: {url}")
        return None

    # 获取视频元数据
    try:
        info = await fetch_video_data(video_id)
        if info:
            info["source_url"] = url
            return info
    except Exception as e:
        logger.error(f"视频数据抓取失败: video_id={video_id} | {e}")

    return None
