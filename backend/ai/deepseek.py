"""DeepSeek Provider

DeepSeek API (https://platform.deepseek.com)
模型: deepseek-chat (≈GPT-4 水平，中文极强，价格极低)
"""
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

DEEPSEEK_BASE = "https://api.deepseek.com"


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek LLM Provider — 纯文本分析"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model

    @property
    def name(self) -> str:
        return f"DeepSeek/{self.model}"

    async def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """发送 Chat Completion 请求"""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": 1000,
                },
            )
            if resp.status_code != 200:
                logger.error(f"DeepSeek API error: {resp.status_code} {resp.text[:200]}")
                raise RuntimeError(f"DeepSeek API 调用失败: HTTP {resp.status_code}")

            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _parse_json(self, text: str, default=None) -> dict:
        """从 LLM 返回文本中提取 JSON"""
        if default is None:
            default = {}
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 提取 JSON 块
        import re
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        # 提取数组
        m = re.search(r'\[[\s\S]*\]', text)
        if m:
            try:
                arr = json.loads(m.group(0))
                if isinstance(default, list):
                    return arr
                return {"items": arr}
            except json.JSONDecodeError:
                pass
        logger.warning(f"无法解析 LLM 返回的 JSON: {text[:100]}")
        return default

    async def analyze_video_content(
        self,
        title: str = "",
        author: str = "",
        description: str = "",
        tags: list[str] = None,
        transcript: str = "",
        frame_descriptions: list[str] = None,
    ) -> AnalysisResult:
        tags = tags or []
        frames_str = "\n".join(f"- {f}" for f in (frame_descriptions or [])) if frame_descriptions else "无"

        user_prompt = ANALYZE_VIDEO_USER.format(
            title=title or "无",
            author=author or "未知",
            description=description or "无",
            tags_str=", ".join(tags) if tags else "无",
            transcript=transcript or "无",
            frames_str=frames_str,
        )

        try:
            text = await self._chat(ANALYZE_VIDEO_SYSTEM, user_prompt)
            data = self._parse_json(text, {
                "summary": text[:200],
                "keypoints": [],
                "tags": [],
                "category": "",
                "audience": "",
                "difficulty": "",
                "quality_score": 0,
            })
        except Exception as e:
            logger.error(f"DeepSeek analyze 失败: {e}")
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
            text = await self._chat(
                GENERATE_TAGS_SYSTEM,
                GENERATE_TAGS_USER.format(
                    content=content[:500],
                    existing=", ".join(existing_tags) if existing_tags else "无",
                ),
                temperature=0.2,
            )
            result = self._parse_json(text, [])
            if isinstance(result, dict):
                return result.get("items", result.get("tags", []))
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"DeepSeek generate_tags 失败: {e}")
            return existing_tags

    async def suggest_category(self, content: str, tags: list[str]) -> str:
        try:
            text = await self._chat(
                SUGGEST_CATEGORY_SYSTEM,
                SUGGEST_CATEGORY_USER.format(
                    content=content[:500],
                    tags=", ".join(tags) if tags else "无",
                ),
                temperature=0.1,
            )
            return text.strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"DeepSeek suggest_category 失败: {e}")
            return ""

    async def expand_search_query(self, query: str) -> list[str]:
        try:
            text = await self._chat(
                EXPAND_SEARCH_SYSTEM,
                EXPAND_SEARCH_USER.format(query=query),
                temperature=0.2,
            )
            result = self._parse_json(text, [])
            if isinstance(result, dict):
                return result.get("items", result.get("queries", [query]))
            return result if isinstance(result, list) else [query]
        except Exception as e:
            logger.error(f"DeepSeek expand_search 失败: {e}")
            return [query]
