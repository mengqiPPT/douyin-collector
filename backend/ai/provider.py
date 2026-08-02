"""AI Provider 工厂 — 统一管理和调度多个 AI Provider

策略：
- DeepSeek (deepseek-chat): 主力文本分析模型（中文最强、极便宜）
- Qwen (qwen-plus): 备选文本分析
- Qwen-VL (qwen-vl-plus): 多模态画面理解
- Qwen-Audio (qwen-audio-turbo): 音频理解

调用优先级：
  文本分析：DeepSeek → 失败回退 Qwen → 失败回退本地规则
  多模态：  Qwen-VL / Qwen-Audio（仅 Qwen 支持）
  搜索扩展：DeepSeek → 失败回退 Qwen
"""
import logging
from .deepseek import DeepSeekProvider
from .qwen import QwenTextProvider, QwenMultimodalAnalyzer

logger = logging.getLogger(__name__)


class AIProviderHub:
    """AI Provider 调度中心"""

    def __init__(self,
                 deepseek_api_key: str = "",
                 qwen_api_key: str = ""):
        self.deepseek = DeepSeekProvider(deepseek_api_key) if deepseek_api_key else None
        self.qwen_text = QwenTextProvider(qwen_api_key) if qwen_api_key else None
        self.qwen_multimodal = QwenMultimodalAnalyzer(qwen_api_key) if qwen_api_key else None

    @property
    def has_any_provider(self) -> bool:
        return self.deepseek is not None or self.qwen_text is not None

    @property
    def has_multimodal(self) -> bool:
        return self.qwen_multimodal is not None

    @property
    def active_providers(self) -> list[str]:
        names = []
        if self.deepseek:
            names.append(self.deepseek.name)
        if self.qwen_text:
            names.append(self.qwen_text.name)
        return names

    async def analyze_video_content(
        self, title="", author="", description="", tags=None,
        transcript="", frame_descriptions=None,
    ):
        """AI 分析视频内容（优先 DeepSeek，回退 Qwen）"""
        from .base import AnalysisResult

        providers = [p for p in [self.deepseek, self.qwen_text] if p]
        for provider in providers:
            try:
                result = await provider.analyze_video_content(
                    title=title, author=author, description=description,
                    tags=tags, transcript=transcript,
                    frame_descriptions=frame_descriptions,
                )
                if result.summary or result.tags:
                    logger.info(f"AI 分析成功: {provider.name}")
                    return result, provider.name
            except Exception as e:
                logger.warning(f"{provider.name} 分析失败: {e}")

        return AnalysisResult(), "none"

    async def generate_tags(self, content: str, existing_tags: list[str]) -> list[str]:
        """AI 生成标签"""
        for provider in [self.deepseek, self.qwen_text]:
            if not provider:
                continue
            try:
                tags = await provider.generate_tags(content, existing_tags)
                if tags:
                    return tags
            except:
                pass
        return existing_tags

    async def suggest_category(self, content: str, tags: list[str]) -> str:
        """AI 建议分类"""
        for provider in [self.deepseek, self.qwen_text]:
            if not provider:
                continue
            try:
                cat = await provider.suggest_category(content, tags)
                if cat:
                    return cat
            except:
                pass
        return ""

    async def expand_search_query(self, query: str) -> list[str]:
        """搜索查询扩展"""
        for provider in [self.deepseek, self.qwen_text]:
            if not provider:
                continue
            try:
                expanded = await provider.expand_search_query(query)
                if expanded and expanded != [query]:
                    return expanded
            except:
                pass
        return [query]

    async def describe_video_cover(self, cover_url: str) -> str:
        """用 Qwen-VL 描述视频封面"""
        if not self.qwen_multimodal:
            return ""
        try:
            descs = await self.qwen_multimodal.describe_video_frames(cover_url=cover_url)
            return descs[0] if descs else ""
        except Exception as e:
            logger.warning(f"封面分析失败: {e}")
            return ""

    async def understand_audio(self, audio_path: str) -> str:
        """用 Qwen-Audio 理解音频内容"""
        if not self.qwen_multimodal:
            return ""
        try:
            return await self.qwen_multimodal.transcribe_audio(audio_path)
        except Exception as e:
            logger.warning(f"音频分析失败: {e}")
            return ""
