"""通义千问 Provider

通义千问 API (https://dashscope.aliyun.com)
模型:
  - qwen-plus: 文本分析（性价比高）
  - qwen-vl-plus: 多模态（图片/视频帧理解）
  - qwen-audio: 音频理解（语音转文字+理解）

用途：
  - 视频帧分析：提取关键帧，用 Qwen-VL 描述画面内容
  - 语音转写+理解：Qwen-Audio 直接理解音频内容（不局限于转写文字）
  - 文本分析：作为 DeepSeek 的备选方案
"""
import os
import json
import logging
import httpx
from .base import BaseAIProvider, AnalysisResult
from .prompts import (
    ANALYZE_VIDEO_SYSTEM, ANALYZE_VIDEO_USER,
    GENERATE_TAGS_SYSTEM, GENERATE_TAGS_USER,
    SUGGEST_CATEGORY_SYSTEM, SUGGEST_CATEGORY_USER,
    EXPAND_SEARCH_SYSTEM, EXPAND_SEARCH_USER,
)

logger = logging.getLogger(__name__)

QWEN_BASE = "https://dashscope.aliyuncs.com/api/v1"


class QwenTextProvider(BaseAIProvider):
    """通义千问 文本分析 Provider — 作为 DeepSeek 备选"""

    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.api_key = api_key
        self.model = model

    @property
    def name(self) -> str:
        return f"Qwen/{self.model}"

    async def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """发送通义千问 Text Completion 请求"""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{QWEN_BASE}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": {
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ]
                    },
                    "parameters": {
                        "temperature": temperature,
                        "max_tokens": 1000,
                        "result_format": "message",
                    },
                },
            )
            if resp.status_code != 200:
                logger.error(f"Qwen API error: {resp.status_code} {resp.text[:200]}")
                raise RuntimeError(f"通义千问 API 调用失败: HTTP {resp.status_code}")

            data = resp.json()
            return data["output"]["choices"][0]["message"]["content"]

    def _parse_json(self, text: str, default=None):
        """从 LLM 返回文本中提取 JSON"""
        if default is None:
            default = {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        import re
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        m = re.search(r'\[[\s\S]*\]', text)
        if m:
            try:
                arr = json.loads(m.group(0))
                return arr if isinstance(default, list) else {"items": arr}
            except json.JSONDecodeError:
                pass
        return default

    async def analyze_video_content(
        self, title="", author="", description="", tags=None, transcript="", frame_descriptions=None,
    ) -> AnalysisResult:
        tags = tags or []
        frames_str = "\n".join(f"- {f}" for f in (frame_descriptions or [])) if frame_descriptions else "无"
        user_prompt = ANALYZE_VIDEO_USER.format(
            title=title or "无", author=author or "未知", description=description or "无",
            tags_str=", ".join(tags) if tags else "无",
            transcript=transcript or "无", frames_str=frames_str,
        )
        try:
            text = await self._chat(ANALYZE_VIDEO_SYSTEM, user_prompt)
            data = self._parse_json(text, {"summary": text[:200], "keypoints": [], "tags": [], "category": "", "audience": "", "difficulty": "", "quality_score": 0})
        except Exception as e:
            logger.error(f"Qwen analyze 失败: {e}")
            return AnalysisResult()
        return AnalysisResult(
            summary=data.get("summary", "")[:300],
            keypoints=data.get("keypoints", [])[:5],
            tags=data.get("tags", [])[:8],
            category=data.get("category", ""),
            audience=data.get("audience", ""),
            difficulty=data.get("difficulty", ""),
            quality_score=int(data.get("quality_score", 0)),
        )

    async def generate_tags(self, content: str, existing_tags: list[str]) -> list[str]:
        try:
            text = await self._chat(GENERATE_TAGS_SYSTEM, GENERATE_TAGS_USER.format(content=content[:500], existing=", ".join(existing_tags) if existing_tags else "无"), temperature=0.2)
            result = self._parse_json(text, [])
            if isinstance(result, dict):
                return result.get("items", result.get("tags", []))
            return result if isinstance(result, list) else []
        except:
            return existing_tags

    async def suggest_category(self, content: str, tags: list[str]) -> str:
        try:
            text = await self._chat(SUGGEST_CATEGORY_SYSTEM, SUGGEST_CATEGORY_USER.format(content=content[:500], tags=", ".join(tags) if tags else "无"), temperature=0.1)
            return text.strip().strip('"').strip("'")
        except:
            return ""

    async def expand_search_query(self, query: str) -> list[str]:
        try:
            text = await self._chat(EXPAND_SEARCH_SYSTEM, EXPAND_SEARCH_USER.format(query=query), temperature=0.2)
            result = self._parse_json(text, [])
            if isinstance(result, dict):
                return result.get("items", result.get("queries", [query]))
            return result if isinstance(result, list) else [query]
        except:
            return [query]


# -------------------------------------------------------------------
# 多模态能力（Qwen 特有）
# -------------------------------------------------------------------
class QwenMultimodalAnalyzer:
    """通义千问多模态分析器

    能力：
    1. 视频帧理解 (Qwen-VL): 提取关键帧，描述画面内容
    2. 音频理解 (Qwen-Audio): 直接理解音频内容，比传统 ASR 更智能
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def describe_image(self, image_url_or_base64: str) -> str:
        """用 Qwen-VL 描述图片内容

        Args:
            image_url_or_base64: 图片 URL 或 base64 编码的图片数据

        Returns:
            图片内容的文字描述
        """
        # 判断是 URL 还是 base64
        is_url = image_url_or_base64.startswith("http")

        content_parts = []
        if is_url:
            content_parts.append({"image": image_url_or_base64})
        else:
            content_parts.append({"image": f"data:image/jpeg;base64,{image_url_or_base64}"})
        content_parts.append({"text": "请详细描述这张图片的画面内容，包括：场景、人物、动作、文字信息、整体氛围。"})

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{QWEN_BASE}/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-vl-plus",
                    "input": {"messages": [{"role": "user", "content": content_parts}]},
                    "parameters": {"max_tokens": 300},
                },
            )
            if resp.status_code != 200:
                logger.error(f"Qwen-VL error: {resp.status_code} {resp.text[:200]}")
                return ""
            data = resp.json()
            return data["output"]["choices"][0]["message"]["content"]

    async def describe_video_frames(self, cover_url: str = "", frame_urls: list[str] = None) -> list[str]:
        """描述视频的多个画面

        Args:
            cover_url: 封面图 URL
            frame_urls: 其他关键帧 URL 列表

        Returns:
            画面描述列表
        """
        descriptions = []

        # 分析封面图
        if cover_url:
            try:
                desc = await self.describe_image(cover_url)
                if desc:
                    descriptions.append(f"[封面] {desc}")
            except Exception as e:
                logger.warning(f"封面图分析失败: {e}")

        # 分析其他关键帧
        for url in (frame_urls or []):
            try:
                desc = await self.describe_image(url)
                if desc:
                    descriptions.append(desc)
            except Exception as e:
                logger.warning(f"关键帧分析失败: {e}")

        return descriptions

    async def transcribe_audio(self, audio_url_or_path: str) -> str:
        """用 Qwen-Audio 理解音频内容

        比传统 ASR 更智能：不仅能转写文字，还能理解语境、情绪、音效等。

        Args:
            audio_url_or_path: 音频 URL 或本地文件路径

        Returns:
            音频内容的文字描述和转写
        """
        # Qwen-Audio 通过 DashScope 的 file upload API 处理
        # 对于本地文件，先上传获取 URL
        audio_url = audio_url_or_path
        if not audio_url.startswith("http"):
            # 本地文件 → base64 → data URI (Qwen-Audio 支持)
            import base64
            with open(audio_url_or_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            audio_url = f"data:audio/wav;base64,{audio_b64}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{QWEN_BASE}/services/aigc/multimodal-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-audio-turbo",
                    "input": {
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"audio": audio_url},
                                {"text": "请完整转写这段音频的内容，然后总结核心观点和关键信息。"},
                            ],
                        }]
                    },
                    "parameters": {"max_tokens": 2000},
                },
            )
            if resp.status_code != 200:
                logger.error(f"Qwen-Audio error: {resp.status_code} {resp.text[:200]}")
                return ""
            data = resp.json()
            return data["output"]["choices"][0]["message"]["content"]
