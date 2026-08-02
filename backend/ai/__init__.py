"""AI 分析模块

提供统一的 AI Provider 接口和多模型调度。

架构：
  AIProviderHub (调度中心)
    ├── DeepSeekProvider   (主力文本分析)
    ├── QwenTextProvider   (备选文本分析)
    └── QwenMultimodalAnalyzer (多模态: VL + Audio)

使用示例:
    hub = AIProviderHub(
        deepseek_api_key="sk-xxx",
        qwen_api_key="sk-xxx",
    )
    result, provider = await hub.analyze_video_content(
        title="...", description="...", tags=[...]
    )
"""
from .provider import AIProviderHub
from .base import AnalysisResult
from .deepseek import DeepSeekProvider
from .qwen import QwenTextProvider, QwenMultimodalAnalyzer
