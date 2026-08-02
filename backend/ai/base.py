"""AI Provider 抽象基类

所有 LLM Provider 必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """统一的分析结果结构"""
    summary: str = ""                    # 内容摘要
    keypoints: list = field(default_factory=list)   # 核心要点
    tags: list = field(default_factory=list)        # AI 标签
    category: str = ""                   # 建议分类
    audience: str = ""                   # 目标受众
    difficulty: str = ""                 # 难度: 入门/进阶/高级
    quality_score: int = 0              # 内容质量评分 0-100


class BaseAIProvider(ABC):
    """LLM Provider 抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        ...

    @abstractmethod
    async def analyze_video_content(
        self,
        title: str,
        author: str,
        description: str,
        tags: list[str],
        transcript: str = "",
        frame_descriptions: list[str] = None,
    ) -> AnalysisResult:
        """分析视频内容，生成结构化分析结果

        Args:
            title: 视频标题
            author: 作者名
            description: 视频描述
            tags: 原始标签列表
            transcript: 语音转写文本
            frame_descriptions: 视频帧描述列表（多模态）

        Returns:
            AnalysisResult: 结构化的分析结果
        """
        ...

    @abstractmethod
    async def generate_tags(self, content: str, existing_tags: list[str]) -> list[str]:
        """根据内容生成更精准的标签

        Args:
            content: 内容文本（标题+描述+摘要）
            existing_tags: 现有标签

        Returns:
            新标签列表
        """
        ...

    @abstractmethod
    async def suggest_category(self, content: str, tags: list[str]) -> str:
        """根据内容建议分类

        Args:
            content: 内容文本
            tags: 标签列表

        Returns:
            建议的分类名称
        """
        ...

    @abstractmethod
    async def expand_search_query(self, query: str) -> list[str]:
        """搜索查询扩展

        将用户搜索词扩展为多个同义/相关查询词，
        提升 FTS5 搜索的召回率。

        Args:
            query: 用户输入的搜索词

        Returns:
            扩展后的查询词列表
        """
        ...
