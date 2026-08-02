"""抖音视频收藏夹 - 后端主应用

FastAPI 应用，提供以下 API：
  POST   /api/videos          收藏视频（粘贴抖音分享链接）
  GET    /api/videos          视频列表（分页 + 全文搜索 + 分类过滤）
  GET    /api/videos/{id}     视频详情
  DELETE /api/videos/{id}     删除视频
  GET    /api/categories      分类列表
  PATCH  /api/videos/{id}     更新视频分类
  GET    /api/proxy-image     封面图代理（解决跨域问题）
"""
import json
import logging
import os
import sys

# -------------------------------------------------------------------
# 日志配置
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

# 确保能 import 同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import httpx

from database import (
    init_db, insert_video, get_video, list_videos, delete_video,
    list_categories, update_category, update_analyze_status, update_analyze_result,
    find_video_by_url,
)
from parser import parse_douyin_url, extract_url, is_valid_douyin_url
from category import auto_category
from analyzer import check_ffmpeg, analyze_video as run_ai_analysis
from ai import AIProviderHub

# -------------------------------------------------------------------
# 配置：AI API 密钥
# 优先级：环境变量 > 此处硬编码
# -------------------------------------------------------------------
AI_CONFIG = {
    "baidu_speech": {
        "app_id": os.environ.get("BAIDU_APP_ID", ""),
        "api_key": os.environ.get("BAIDU_API_KEY", ""),
        "secret_key": os.environ.get("BAIDU_SECRET_KEY", ""),
    },
    "qianfan": {
        "api_key": os.environ.get("QIANFAN_AK", ""),
        "secret_key": os.environ.get("QIANFAN_SK", ""),
    },
    "deepseek": {
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
    },
    "qwen": {
        "api_key": os.environ.get("QWEN_API_KEY", ""),
    },
}

# 初始化 AI Provider Hub
_ai_hub = AIProviderHub(
    deepseek_api_key=AI_CONFIG["deepseek"]["api_key"],
    qwen_api_key=AI_CONFIG["qwen"]["api_key"],
)

# -------------------------------------------------------------------
# 初始化
# -------------------------------------------------------------------
app = FastAPI(title="抖音视频收藏夹", version="1.0.0", description="抖音视频收藏与管理 API")

# CORS - 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
init_db()

# 前端静态文件目录（构建后的 Vue 应用）
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
_static_files_available = os.path.isdir(FRONTEND_DIST)


# -------------------------------------------------------------------
# 全局异常处理
# -------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """统一 HTTP 异常响应格式"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} | {request.method} {request.url.path}")
    return Response(
        content=json.dumps({"detail": exc.detail}),
        status_code=exc.status_code,
        media_type="application/json",
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """全局未捕获异常处理"""
    logger.exception(f"未处理的异常: {request.method} {request.url.path} | {type(exc).__name__}: {exc}")
    return Response(
        content=json.dumps({"detail": "服务器内部错误，请查看日志"}),
        status_code=500,
        media_type="application/json",
    )


# -------------------------------------------------------------------
# 请求/响应模型
# -------------------------------------------------------------------
class CollectRequest(BaseModel):
    share_text: str


class CategoryUpdateRequest(BaseModel):
    category: str


# -------------------------------------------------------------------
# API 路由
# -------------------------------------------------------------------
@app.get("/api")
def api_root():
    """API 信息"""
    return {"name": "抖音视频收藏夹 API", "version": "1.0.0", "docs": "/docs"}


@app.post("/api/videos")
async def collect_video(req: CollectRequest, background_tasks: BackgroundTasks):
    """收藏视频：接收抖音分享文本，解析并保存（保存后自动触发 AI 分析）"""
    share_text = req.share_text.strip()
    if not share_text:
        raise HTTPException(status_code=400, detail="分享文本不能为空")

    # 提取 URL
    url = extract_url(share_text)
    if not url:
        raise HTTPException(status_code=400, detail="未在文本中找到有效的抖音链接")

    # 检查是否已收藏
    existing = find_video_by_url(url)
    if existing:
        logger.info(f"重复收藏请求: {url}")
        return {
            "message": "该视频已在收藏列表中",
            "video": _serialize_video(existing),
            "is_existing": True,
        }

    # 解析
    try:
        info = await parse_douyin_url(share_text)
    except httpx.TimeoutException:
        logger.warning(f"解析超时: {url}")
        raise HTTPException(status_code=504, detail="解析超时，请稍后重试")
    except Exception as e:
        logger.error(f"解析失败: {url} | {type(e).__name__}: {e}")
        raise HTTPException(status_code=502, detail=f"解析失败: {str(e)}")

    if not info:
        logger.warning(f"无法解析: {url}")
        raise HTTPException(status_code=422, detail="无法从该链接解析视频信息，可能页面不可公开访问")

    # 使用解析后返回的真实 URL 再次检查（处理短链重定向后的长链）
    resolved_url = info.get("source_url") or url
    if resolved_url != url:
        existing = find_video_by_url(resolved_url)
        if existing:
            logger.info(f"重复收藏请求(重定向后): {resolved_url}")
            return {
                "message": "该视频已在收藏列表中",
                "video": _serialize_video(existing),
                "is_existing": True,
            }

    # 自动分类
    cat = auto_category(info.get("tags", []), info.get("description", ""), info.get("title", ""))

    # 存入数据库
    try:
        vid = insert_video(
            url=url,
            video_url=info.get("video_url", ""),
            title=info.get("title", ""),
            author=info.get("author", ""),
            author_avatar=info.get("author_avatar", ""),
            description=info.get("description", ""),
            tags=info.get("tags", []),
            cover_url=info.get("cover_url", ""),
            category=cat,
            like_count=info.get("like_count", 0),
            comment_count=info.get("comment_count", 0),
            share_count=info.get("share_count", 0),
            duration=info.get("duration", 0),
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            logger.info(f"数据库唯一约束触发: {url}")
            raise HTTPException(status_code=409, detail="该视频已收藏过")
        logger.error(f"保存失败: {url} | {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    logger.info(f"收藏成功: id={vid} title={info.get('title', '')[:30]}")

    # 自动触发 AI 分析（后台异步执行）
    auto_analyze = False
    if check_ffmpeg():
        auto_analyze = True
        update_analyze_status(vid, "analyzing")
        tags_for_analysis = info.get("tags", [])
        background_tasks.add_task(
            _run_analysis_background,
            vid=vid,
            video_url=info.get("video_url", ""),
            title=info.get("title", ""),
            author=info.get("author", ""),
            description=info.get("description", ""),
            tags=tags_for_analysis,
            config=AI_CONFIG,
        )
        logger.info(f"自动分析已投递: id={vid}")

    video = get_video(vid)
    return {
        "message": "收藏成功" + ("，已自动开始 AI 分析" if auto_analyze else ""),
        "video": _serialize_video(video),
        "auto_analyze": auto_analyze,
    }


@app.get("/api/videos")
async def get_videos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类过滤"),
):
    """获取视频列表，支持分页、全文搜索、分类过滤"""
    keyword = q.strip() if q else None

    # AI 搜索查询扩展：将用户搜索词扩展为多个相关词
    search_terms = [keyword] if keyword else []
    if keyword and _ai_hub.has_any_provider and len(keyword) >= 2:
        try:
            expanded = await _ai_hub.expand_search_query(keyword)
            search_terms = list(dict.fromkeys([keyword] + expanded))[:3]  # 最多3个去重
            logger.info(f"搜索扩展: '{keyword}' → {search_terms}")
        except Exception:
            pass

    # 用扩展后的关键词搜索（取第一个作为 FTS5 关键词）
    search_kw = search_terms[0] if search_terms else None
    videos, total = list_videos(page=page, size=size, keyword=search_kw, category=category)
    return {
        "videos": [_serialize_video(v) for v in videos],
        "total": total,
        "page": page,
        "size": size,
    }


@app.get("/api/videos/{vid}")
def get_video_detail(vid: int):
    """获取视频详情"""
    video = get_video(vid)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return _serialize_video(video)


@app.delete("/api/videos/{vid}")
def remove_video(vid: int):
    """删除视频"""
    deleted = delete_video(vid)
    if not deleted:
        raise HTTPException(status_code=404, detail="视频不存在")
    return {"message": "删除成功"}


@app.get("/api/categories")
def get_categories():
    """获取所有分类及数量"""
    return list_categories()


@app.patch("/api/videos/{vid}")
def update_video_category(vid: int, req: CategoryUpdateRequest):
    """更新视频分类"""
    video = get_video(vid)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    update_category(vid, req.category.strip())
    return {"message": "更新成功", "video": _serialize_video(get_video(vid))}


@app.get("/api/videos/{vid}/analyze")
def get_analyze_status(vid: int):
    """获取视频分析状态和结果"""
    video = get_video(vid)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return _serialize_video(video)


@app.post("/api/videos/{vid}/analyze")
async def analyze_video(vid: int, background_tasks: BackgroundTasks):
    """触发 AI 分析（后台异步执行，立即返回）

    分析流程：
    1. 校验视频存在且不在分析中
    2. 设置状态为 analyzing，立即返回
    3. 后台执行：下载视频 → 提取音频 → 语音转写 → LLM 摘要
    4. 完成后自动更新数据库中的分析结果
    5. 前端通过 GET /api/videos/{id}/analyze 轮询状态
    """
    video = get_video(vid)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    if video.get("analyze_status") == "analyzing":
        raise HTTPException(status_code=409, detail="正在分析中，请稍候")

    # 检查环境：FFmpeg 是可选依赖（音频提取增强分析，但不是必须）
    ffmpeg_ok = check_ffmpeg()
    if not ffmpeg_ok:
        logger.warning("FFmpeg 未安装，视频分析将仅基于元数据生成（不提取音频）")
        # 不抛出错误，继续执行，只是 video_url 会设为空，analyzer 会跳过音频流程

    # 提取必要数据（避免在后台任务中访问已关闭的数据库连接）
    video_url = video.get("video_url", "")
    video_title = video.get("title", "")
    video_author = video.get("author", "")
    video_description = video.get("description", "")
    tags = video.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []

    # 设置分析中状态
    update_analyze_status(vid, "analyzing")

    # 投递后台任务
    background_tasks.add_task(
        _run_analysis_background,
        vid=vid,
        video_url=video_url,
        title=video_title,
        author=video_author,
        description=video_description,
        tags=tags,
        config=AI_CONFIG,
    )

    logger.info(f"分析任务已投递: id={vid} title={video_title[:30]}")
    return {
        "message": "分析任务已启动",
        "status": "analyzing",
        "video": _serialize_video(get_video(vid)),
    }


async def _run_analysis_background(vid, video_url, title, author, description, tags, config):
    """后台执行 AI 分析任务

    分析流程：
    1. 本地引擎：下载视频 → 提取音频 → 语音转文字（原有流程）
    2. Qwen VL：分析视频封面图（多模态）
    3. LLM：调用 AI Hub 做深度内容分析
    4. LLM：生成精准标签和分类建议
    """
    try:
        logger.info(f"后台分析开始: id={vid}")

        # --- 阶段 1: 本地引擎处理（视频下载/音频提取/转写）---
        transcript = ""
        frame_descriptions = []
        try:
            local_result = await run_ai_analysis(
                video_url=video_url, title=title, author=author,
                description=description, tags=tags, config=config,
            )
            transcript = local_result.get("transcribe_text", "")
        except Exception as e:
            logger.warning(f"本地引擎分析失败（将跳过语音转写）: {e}")

        # --- 阶段 2: Qwen VL 多模态分析封面图 ---
        if _ai_hub.has_multimodal and video_url:
            # 用封面图 URL 做画面理解（douyin 封面图通常就是视频关键帧）
            video = get_video(vid)
            cover_url = video.get("cover_url", "") if video else ""
            if cover_url:
                try:
                    frame_desc = await _ai_hub.describe_video_cover(cover_url)
                    if frame_desc:
                        frame_descriptions.append(frame_desc)
                        logger.info(f"Qwen-VL 封面分析完成: id={vid}")
                except Exception as e:
                    logger.warning(f"Qwen-VL 分析失败: {e}")

        # --- 阶段 3: LLM 深度内容分析 ---
        ai_summary = ""
        ai_tags = []
        ai_keypoints = []
        better_cat = ""
        provider_used = "none"

        if _ai_hub.has_any_provider:
            try:
                analysis_result, provider_used = await _ai_hub.analyze_video_content(
                    title=title, author=author, description=description,
                    tags=tags, transcript=transcript,
                    frame_descriptions=frame_descriptions,
                )
                ai_summary = analysis_result.summary
                ai_keypoints = analysis_result.keypoints
                ai_tags = analysis_result.tags
                logger.info(f"LLM 分析完成: id={vid} provider={provider_used}")
            except Exception as e:
                logger.error(f"LLM 分析失败，回退到本地引擎: {e}")

        # --- 阶段 4: 如果 LLM 没有结果，回退到本地规则引擎 ---
        if not ai_summary:
            try:
                local_fallback = await run_ai_analysis(
                    video_url="", title=title, author=author,
                    description=description, tags=tags, config={"qianfan": {}},
                )
                ai_summary = local_fallback.get("summary", "")
                ai_keypoints = local_fallback.get("keypoints", [])
                ai_tags = local_fallback.get("tags", [])
                logger.info(f"回退到本地规则引擎: id={vid}")
            except Exception:
                pass

        # --- 阶段 5: AI 建议分类 ---
        if _ai_hub.has_any_provider and ai_summary:
            try:
                better_cat = await _ai_hub.suggest_category(
                    content=f"{title} {description} {ai_summary}",
                    tags=ai_tags,
                )
            except Exception:
                pass

        # --- 保存结果 ---
        update_analyze_result(
            vid,
            summary=ai_summary,
            keypoints=ai_keypoints,
            ai_tags=ai_tags,
            transcribe_text=transcript,
        )

        # 重新分类
        if better_cat:
            update_category(vid, better_cat)
            logger.info(f"AI 重新分类: id={vid} → {better_cat}")
        else:
            # 回退到本地分类
            try:
                from analyzer import suggest_category_from_analysis
                local_cat = suggest_category_from_analysis(ai_summary, ai_tags, ai_keypoints)
                if local_cat:
                    update_category(vid, local_cat)
                    logger.info(f"本地重新分类: id={vid} → {local_cat}")
            except Exception:
                pass

        logger.info(f"后台分析完成: id={vid} provider={provider_used}")

    except Exception as e:
        logger.exception(f"后台分析失败: id={vid}")
        update_analyze_status(vid, "failed")


@app.get("/api/env-check")
def env_check():
    """检查 AI 分析所需的环境依赖

    返回各组件可用性及当前分析模式：
    - full：百度语音 + 千帆 LLM（完整 AI 分析）
    - basic_plus：Whisper 本地转写 + 本地规则摘要
    - basic：仅元数据 + 本地规则摘要（无语音转写）
    """
    baidu_cfg = AI_CONFIG.get("baidu_speech", {})
    qianfan_cfg = AI_CONFIG.get("qianfan", {})

    ffmpeg_ok = check_ffmpeg()
    baidu_ok = bool(baidu_cfg.get("app_id") and baidu_cfg.get("api_key") and baidu_cfg.get("secret_key"))
    qianfan_ok = bool(qianfan_cfg.get("api_key") and qianfan_cfg.get("secret_key"))

    # 检查 Whisper 是否可导入
    whisper_ok = False
    try:
        import whisper  # noqa: F401
        whisper_ok = True
    except ImportError:
        pass

    # 判定分析模式
    if baidu_ok and qianfan_ok:
        mode = "full"
    elif whisper_ok or baidu_ok:
        mode = "basic_plus"
    else:
        mode = "basic"

    return {
        "ffmpeg": ffmpeg_ok,
        "baidu_speech": baidu_ok,
        "whisper": whisper_ok,
        "qianfan": qianfan_ok,
        "mode": mode,
        "mode_label": {
            "full": "完整模式（AI 语音识别 + LLM 摘要）",
            "basic_plus": "基础+模式（本地语音识别 + 规则摘要）",
            "basic": "基础模式（仅元数据 + 规则摘要）",
        }.get(mode, "未知"),
        "can_analyze": True,
        # AI Provider 状态
        "ai_providers": _ai_hub.active_providers,
        "ai_multimodal": _ai_hub.has_multimodal,
    }


@app.get("/api/proxy-image")
async def proxy_image(url: str = Query(..., description="图片URL")):
    """图片代理：解决抖音封面图跨域无法加载的问题"""
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="无效的图片URL")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.douyin.com/",
            })
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="图片获取失败")
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="图片获取超时")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"图片代理失败: {str(e)}")


# -------------------------------------------------------------------
# 辅助函数
# -------------------------------------------------------------------
def _serialize_video(v):
    """将数据库行序列化为前端可用的 dict，解析 tags/ai_tags JSON"""
    if not v:
        return None
    d = dict(v)
    if isinstance(d.get("tags"), str):
        try:
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = []
    if not isinstance(d.get("tags"), list):
        d["tags"] = []
    # 解析 ai_keypoints (JSON 字符串 -> list)
    if isinstance(d.get("ai_keypoints"), str) and d.get("ai_keypoints"):
        try:
            d["ai_keypoints"] = json.loads(d["ai_keypoints"])
        except Exception:
            d["ai_keypoints"] = []
    elif not d.get("ai_keypoints"):
        d["ai_keypoints"] = []
    # 解析 ai_tags (JSON 字符串 -> list)
    if isinstance(d.get("ai_tags"), str) and d.get("ai_tags"):
        try:
            d["ai_tags"] = json.loads(d["ai_tags"])
        except Exception:
            d["ai_tags"] = []
    elif not d.get("ai_tags"):
        d["ai_tags"] = []
    return d


# -------------------------------------------------------------------
# 前端 SPA fallback（部署模式：FastAPI 同时服务前端 + API）
# 必须在所有 API 路由定义之后注册，否则会拦截 API 请求
# -------------------------------------------------------------------
if _static_files_available:
    import mimetypes
    from starlette.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    # 挂载静态资源（JS/CSS/图片等）
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback: 非 /api 的 GET 请求返回 index.html
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """所有非 API 路径返回前端 index.html（Vue Router 处理）"""
        # 跳过 API 路径和静态资源
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            raise HTTPException(status_code=404)
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        return {"message": "前端文件未构建，请运行 npm run build 后重启"}


# -------------------------------------------------------------------
# 入口
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
