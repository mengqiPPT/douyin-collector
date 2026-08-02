"""AI 视频内容分析模块

流程：视频下载 -> 音频提取(FFmpeg) -> 语音转文字 -> LLM 摘要生成

支持多种方案：
- 语音转文字：百度语音识别 API / 本地 Whisper 模型
- LLM 摘要：千帆大模型 / 本地规则生成
"""
import os
import sys
import json
import re
import asyncio
import tempfile
import subprocess
import shutil
from pathlib import Path

import httpx

def _discover_ffmpeg_paths():
    """动态发现所有可能的 FFmpeg 路径

    检测顺序：
    1. PATH 环境变量中的 ffmpeg（shutil.which）
    2. FFMPEG_PATH 环境变量
    3. 常见安装位置（Windows / macOS / Linux）
    4. Winget 安装路径（通配符查找）
    """
    candidates = []

    # 1. PATH 环境变量
    which_result = shutil.which("ffmpeg")
    if which_result:
        candidates.append(which_result)

    # 2. 环境变量
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        candidates.append(env_path)

    # 3. 常见安装位置
    if sys.platform == "win32":
        # Chocolatey / 手动安装
        candidates.extend([
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        ])
        # Winget 安装路径（Gyan.FFmpeg）
        winget_base = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            r"Microsoft\WinGet\Packages"
        )
        if os.path.isdir(winget_base):
            try:
                for d in os.listdir(winget_base):
                    if "Gyan.FFmpeg" in d:
                        ffmpeg_exe = os.path.join(winget_base, d, "ffmpeg.exe")
                        if os.path.isfile(ffmpeg_exe):
                            candidates.append(ffmpeg_exe)
                        else:
                            # 子目录查找：ffmpeg-x.x.x-full_build/bin/ffmpeg.exe
                            for root, dirs, _ in os.walk(os.path.join(winget_base, d)):
                                for dname in dirs:
                                    if "ffmpeg" in dname.lower() or "bin" == dname.lower():
                                        exe = os.path.join(root, dname, "ffmpeg.exe")
                                        if os.path.isfile(exe):
                                            candidates.append(exe)
            except Exception:
                pass
    elif sys.platform == "darwin":
        candidates.extend([
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ])
    else:
        candidates.extend([
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ])

    return candidates


# 启动时扫描一次，缓存结果
_FFMPEG_CANDIDATES = _discover_ffmpeg_paths()


def get_ffmpeg_path():
    """查找可用的 FFmpeg 路径"""
    for p in _FFMPEG_CANDIDATES:
        if p and os.path.isfile(p):
            return p
    return None


def check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    return get_ffmpeg_path() is not None


# -------------------------------------------------------------------
# 1. 视频下载
# -------------------------------------------------------------------
async def download_video(video_url, save_path, headers=None):
    """下载视频文件到本地"""
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://www.douyin.com/",
        }
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(video_url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"视频下载失败: HTTP {resp.status_code}")
        with open(save_path, "wb") as f:
            f.write(resp.content)
    return save_path


# -------------------------------------------------------------------
# 2. 音频提取
# -------------------------------------------------------------------
def extract_audio(video_path, audio_path):
    """使用 FFmpeg 从视频中提取音频

    提取为 wav 格式，16kHz，单声道，适合语音识别
    """
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("FFmpeg 未安装或未找到")

    cmd = [
        ffmpeg,
        "-i", video_path,
        "-vn",                    # 不要视频
        "-acodec", "pcm_s16le",   # PCM 16-bit
        "-ar", "16000",           # 16kHz 采样率
        "-ac", "1",               # 单声道
        "-y",                     # 覆盖输出
        audio_path,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr[-500:] if result.stderr else 'unknown error'}")
    if not os.path.isfile(audio_path) or os.path.getsize(audio_path) == 0:
        raise RuntimeError("音频提取失败: 输出文件为空")
    return audio_path


# -------------------------------------------------------------------
# 3. 语音转文字
# -------------------------------------------------------------------
def transcribe_audio_baidu(audio_path, app_id, api_key, secret_key):
    """使用百度语音识别 API 将音频转为文字"""
    from aip import AipSpeech

    client = AipSpeech(app_id, api_key, secret_key)

    # 百度语音识别单次最多约 60 秒，需要分段
    # 读取完整音频
    with open(audio_path, "rb") as f:
        all_data = f.read()

    # 每段最多 60 秒 = 60 * 16000 * 2 = 1,920,000 bytes
    chunk_size = 60 * 16000 * 2
    chunks = [all_data[i:i + chunk_size] for i in range(0, len(all_data), chunk_size)]

    all_text = []
    for i, chunk in enumerate(chunks):
        result = client.asr(chunk, "wav", 16000, {"dev_pid": 1537})
        if result.get("err_no", -1) != 0:
            raise RuntimeError(f"语音识别失败(第{i+1}段): {result.get('err_msg', 'unknown')}")
        result_list = result.get("result", [])
        texts = []
        for item in result_list:
            if isinstance(item, dict):
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        all_text.append(" ".join(texts))

    return " ".join(all_text)


def transcribe_audio_whisper(audio_path):
    """使用 OpenAI Whisper 本地模型进行语音识别（免费，无需 API 密钥）

    需要安装：pip install openai-whisper
    首次使用会自动下载模型
    """
    import whisper

    # 使用 small 模型，平衡速度和准确率
    model = whisper.load_model("small")
    result = model.transcribe(audio_path, language="zh")
    return result.get("text", "").strip()


def transcribe_audio(audio_path, config=None):
    """语音转文字的统一入口

    优先级：
    1. 百度语音识别 API（如果已配置密钥）
    2. Whisper 本地模型（如果已安装）
    3. 抛出异常提示用户
    """
    if config:
        app_id = config.get("app_id")
        api_key = config.get("api_key")
        secret_key = config.get("secret_key")
        if app_id and api_key and secret_key:
            return transcribe_audio_baidu(audio_path, app_id, api_key, secret_key)

    # 尝试使用 Whisper
    try:
        import whisper  # noqa: F401
        return transcribe_audio_whisper(audio_path)
    except ImportError:
        pass

    # 都不可用，返回空字符串（后续用元数据生成摘要）
    return ""


# -------------------------------------------------------------------
# 4. LLM 摘要生成
# -------------------------------------------------------------------
async def generate_summary(title, author, description, tags, transcribe_text, config=None):
    """使用大模型生成内容摘要和核心要点

    如果配置了千帆 API Key，使用 ERNIE 模型；否则使用本地规则生成
    """
    # 构造提示词
    tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
    info_parts = [f"标题: {title}"]
    if author:
        info_parts.append(f"作者: {author}")
    if description:
        info_parts.append(f"描述: {description}")
    if tag_str:
        info_parts.append(f"标签: {tag_str}")
    if transcribe_text:
        info_parts.append(f"语音转写文本: {transcribe_text}")

    video_info = "\n".join(info_parts)

    prompt = f"""请分析以下抖音视频的信息，生成内容摘要和核心要点。

{video_info}

请严格按照以下 JSON 格式输出（不要包含其他内容）：
{{
  "summary": "用2-3句话概括视频的主要内容",
  "keypoints": ["要点1", "要点2", "要点3"],
  "tags": ["AI生成的标签1", "AI生成的标签2"]
}}

注意：
- summary 应简明扼要，说明视频讲了什么
- keypoints 提取3-5个核心要点
- tags 生成3-5个内容标签
- 如果转写文本为空，仅根据标题、描述和标签进行分析"""

    # 尝试使用千帆 SDK
    if config and config.get("api_key") and config.get("secret_key"):
        try:
            return await _generate_with_qianfan(prompt, config)
        except Exception as e:
            print(f"千帆 API 调用失败: {e}, 使用本地规则生成")

    # 回退：本地规则生成
    return _generate_local_summary(title, author, description, tags, transcribe_text)


async def _generate_with_qianfan(prompt, config):
    """使用千帆 SDK 调用 ERNIE 模型"""
    import qianfan

    os.environ["QIANFAN_AK"] = config["api_key"]
    os.environ["QIANFAN_SK"] = config["secret_key"]

    chat_comp = qianfan.ChatCompletion()
    resp = chat_comp.do(
        model="ERNIE-4.0-Turbo-8K",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_output_tokens=800,
    )

    # 千帆 SDK 返回迭代器，需要遍历取最终结果
    if hasattr(resp, "__iter__") and not isinstance(resp, dict):
        result_text = ""
        for item in resp:
            if hasattr(item, "get"):
                result_text = item.get("result", "")
            elif isinstance(item, dict):
                result_text = item.get("result", "")
            elif hasattr(item, "result"):
                result_text = item.result
        text = result_text
    else:
        text = resp["result"] if isinstance(resp, dict) else str(resp)
    return _parse_llm_response(text)


def _parse_llm_response(text):
    """解析 LLM 返回的 JSON"""
    import re
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)

    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return {
                "summary": data.get("summary", ""),
                "keypoints": data.get("keypoints", []),
                "tags": data.get("tags", []),
            }
        except json.JSONDecodeError:
            pass

    return {
        "summary": text.strip()[:300],
        "keypoints": [],
        "tags": [],
    }


# -------------------------------------------------------------------
# 本地内容分析知识库
# -------------------------------------------------------------------

# 常见技术工具/平台映射
_TECH_TOOLS = {
    # AI/编程
    "codex": "AI 编程助手（GitHub Copilot / OpenAI Codex）",
    "copilot": "AI 编程助手（GitHub Copilot）",
    "chatgpt": "AI 对话模型（ChatGPT）",
    "claude": "AI 助手（Claude）",
    "deepseek": "国产 AI 大模型（DeepSeek）",
    "千帆": "百度千帆大模型平台",
    "文心一言": "百度文心大模型",
    "通义千问": "阿里云通义大模型",
    "ai": "人工智能技术",
    "人工智能": "人工智能技术",
    "大模型": "大语言模型技术",
    "llm": "大语言模型（LLM）",
    # 前端/开发
    "gsap": "专业网页动画库（GreenSock Animation Platform）",
    "react": "前端框架（React）",
    "vue": "前端框架（Vue.js）",
    "vue3": "前端框架（Vue 3）",
    "angular": "前端框架（Angular）",
    "nextjs": "React 全栈框架（Next.js）",
    "nuxt": "Vue 全栈框架（Nuxt）",
    "typescript": "TypeScript 编程语言",
    "ts": "TypeScript",
    "tailwind": "CSS 框架（Tailwind CSS）",
    "css": "层叠样式表（CSS）",
    "html": "超文本标记语言（HTML）",
    "javascript": "JavaScript 编程语言",
    "js": "JavaScript",
    "node": "Node.js 运行环境",
    "nodejs": "Node.js",
    "vite": "前端构建工具（Vite）",
    "webpack": "前端打包工具（Webpack）",
    # 后端/数据库
    "python": "Python 编程语言",
    "java": "Java 编程语言",
    "go": "Go 编程语言",
    "rust": "Rust 编程语言",
    "docker": "容器化技术（Docker）",
    "kubernetes": "容器编排（Kubernetes）",
    "k8s": "Kubernetes",
    "mysql": "关系型数据库（MySQL）",
    "redis": "内存数据库（Redis）",
    "mongodb": "文档数据库（MongoDB）",
    "postgres": "关系型数据库（PostgreSQL）",
    # 设计/创意
    "figma": "设计协作工具（Figma）",
    "sketch": "设计工具（Sketch）",
    "photoshop": "图像处理软件（Photoshop）",
    "pr": "视频剪辑软件（Premiere）",
    "ae": "动效设计软件（After Effects）",
    "blender": "3D 建模软件（Blender）",
    "ui": "用户界面设计（UI）",
    "ux": "用户体验设计（UX）",
    # 办公/效率
    "excel": "电子表格软件（Excel）",
    "ppt": "演示文稿（PowerPoint）",
    "word": "文字处理软件（Word）",
    "notion": "知识管理工具（Notion）",
    "obsidian": "笔记软件（Obsidian）",
    # 其他
    "抖音": "短视频平台（抖音）",
    "b站": "视频平台（哔哩哔哩）",
    "小红书": "内容社区（小红书）",
    "微信": "即时通讯/社交平台（微信）",
    "公众号": "微信公众号平台",
}

# 内容类型判断规则
_CONTENT_TYPES = [
    ("技能教程", ["教程", "教学", "入门", "基础", "怎么做", "如何使用", "步骤", "手把手", "实战", "案例", "skill", "指南", "攻略", "技巧", "方法", "一招", "秒懂", "快速"]),
    ("知识科普", ["科普", "是什么", "原理", "介绍", "讲解", "了解", "知多少", "冷知识", "你知道吗", "解读", "揭秘", "深度"]),
    ("产品评测", ["评测", "测评", "对比", "体验", "测试", "试用", "开箱", "上手", "真机", "实测", "到底", "值不值"]),
    ("经验分享", ["分享", "干货", "经验", "心得", "总结", "复盘", "踩坑", "避坑", "血泪", "教训", "建议", "忠告", "踩过的坑"]),
    ("工具推荐", ["推荐", "神器", "宝藏", "必备", "利器", "效率工具", "生产力", "超好用", "太好用", "私藏", "压箱底"]),
    ("行业资讯", ["行业", "趋势", "动态", "最新消息", "发布", "新品", "更新", "重磅", "来了", "官宣", "宣布", "推出"]),
    ("职场成长", ["职场", "面试", "简历", "求职", "晋升", "管理", "沟通", "汇报", "领导", "同事", "工作", "职业发展", "副业", "赚钱", "创业", "搞钱"]),
    ("生活分享", ["生活", "日常", "vlog", "记录", "家居", "美食", "旅行", "穿搭", "健身", "养生"]),
]

# 受众判断规则
_AUDIENCE_MAP = [
    ("前端开发者", ["前端", "web", "html", "css", "js", "javascript", "react", "vue", "angular", "ts", "typescript", "tailwind", "gsap", "dom", "浏览器", "网页"]),
    ("后端开发者", ["后端", "server", "api", "数据库", "mysql", "redis", "docker", "k8s", "kubernetes", "微服务", "架构"]),
    ("AI/算法工程师", ["ai", "人工智能", "大模型", "机器学习", "深度学习", "算法", "神经网络", "nlp", "cv", "模型训练", "微调"]),
    ("设计师", ["设计", "ui", "ux", "figma", "sketch", "视觉", "配色", "排版", "动效", "平面", "品牌"]),
    ("产品经理", ["产品", "需求", "prd", "交互", "用户研究", "竞品分析", "数据分析", "增长"]),
    ("运营/市场", ["运营", "营销", "推广", "流量", "转化", "获客", "投放", "私域", "社群", "内容运营"]),
    ("创业者", ["创业", "商业", "商业模式", "融资", "股权", "管理", "团队", "老板", "生意", "项目"]),
    ("学生/求职者", ["学生", "求职", "面试", "校招", "秋招", "春招", "实习", "考研", "考公", "证书"]),
    ("普通用户/小白", ["小白", "新手", "零基础", "入门", "简单", "傻瓜式", "不用懂", "一学就会", "宝妈", "上班族"]),
]


def _clean_description(text):
    """清洗描述文本，去除话题标签和多余空格"""
    if not text:
        return ""
    # 去掉 #话题标签
    text = re.sub(r'#\S+', '', text)
    # 去掉 URL
    text = re.sub(r'https?://\S+', '', text)
    # 去掉 @提及
    text = re.sub(r'@\S+', '', text)
    # 去掉多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _detect_tools(text):
    """识别视频中提到的技术工具/平台"""
    text_lower = text.lower()
    found = []
    for keyword, description in _TECH_TOOLS.items():
        if keyword.lower() in text_lower and description not in found:
            found.append(description)
    return found[:3]  # 最多返回3个


def _detect_content_type(text):
    """判断视频内容类型"""
    text_lower = text.lower()
    scores = {}
    for ctype, keywords in _CONTENT_TYPES:
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[ctype] = score
    if not scores:
        return "内容分享"
    return max(scores, key=lambda k: scores[k])


def _detect_audience(text, tags):
    """识别目标受众"""
    text_lower = text.lower()
    tag_text = ' '.join(tags).lower()
    combined = text_lower + ' ' + tag_text
    
    scores = {}
    for audience, keywords in _AUDIENCE_MAP:
        score = sum(1 for kw in keywords if kw.lower() in combined)
        if score > 0:
            scores[audience] = score
    
    if not scores:
        return ["通用受众"]
    # 返回得分最高的1-2个
    sorted_audiences = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [a[0] for a in sorted_audiences[:2]]


def _extract_core_topic(title, description, tags):
    """提取视频核心主题"""
    clean_title = _clean_description(title)
    clean_desc = _clean_description(description)
    
    # 核心主题优先从标题提取（标题通常包含最关键信息）
    if clean_title:
        # 去掉疑问词、语气词
        topic = re.sub(r'[？?！!。\.]', '', clean_title)
        topic = re.sub(r'^(这个|那个|这条|一个|一款|推荐|分享|干货)\s*', '', topic)
        return topic[:60]
    
    if clean_desc:
        # 取描述的第一句话
        first_sentence = re.split(r'[。！？\n]', clean_desc)[0]
        return first_sentence[:60]
    
    return ' '.join(tags[:3]) if tags else "未知主题"


def _generate_intelligent_summary(tools, content_type, topic, audience, title, description, transcribe_text):
    """生成自然、有信息量的内容摘要

    避免模板化句式，根据内容类型动态生成不同风格的摘要。
    """
    clean_title = _clean_description(title)
    clean_desc = _clean_description(description)

    # 构建核心信息
    sentences = []

    # 技术/工具类：重点说明能学到什么
    if tools and content_type in ("技能教程", "知识科普"):
        tool_names = '、'.join(t.split('（')[0] for t in tools)
        if content_type == "技能教程":
            sentences.append(f"教程类视频，讲解{tool_names}的具体操作方法")
        else:
            sentences.append(f"科普类内容，系统介绍{tool_names}的核心概念和应用场景")
    elif tools:
        tool_names = '、'.join(t.split('（')[0] for t in tools)
        sentences.append(f"涉及{tool_names}，属于{content_type}类内容")

    # 补充描述中的关键信息
    if clean_desc and len(clean_desc) > 15 and clean_desc != clean_title:
        sentences.append(clean_desc[:120])

    # 主题概述（如果没有工具信息）
    if not tools and len(sentences) == 0:
        if topic and len(topic) > 4:
            sentences.append(f"围绕{topic}相关话题")

    # 受众指向
    if audience and audience != ["通用受众"]:
        aud_str = '、'.join(audience)
        sentences.append(f"面向{aud_str}群体")

    # 转写文本补充（如果有）
    if transcribe_text and len(transcribe_text) > 60:
        key_sentences = [s.strip() for s in re.split(r'[。！？\n]', transcribe_text)
                         if 15 < len(s.strip()) < 80][:2]
        if key_sentences:
            sentences.append(f"核心观点：{'；'.join(key_sentences)}")

    if not sentences:
        return clean_title or "暂无详细内容描述"

    return '。'.join(sentences) + '。'


def _generate_intelligent_keypoints(tools, content_type, topic, audience, title, description, transcribe_text, tags):
    """生成有实际价值的核心要点"""
    keypoints = []
    clean_desc = _clean_description(description)

    # 要点1: 核心内容
    if tools:
        t_names = [t.split('（')[0] for t in tools]
        keypoints.append(f"涉及：{'、'.join(t_names)}")
    elif topic:
        keypoints.append(f"主题：{topic}")

    # 要点2: 内容类型 + 你能获得什么
    value_map = {
        "技能教程": "掌握具体的操作步骤和技巧",
        "知识科普": "理解核心概念和原理",
        "产品评测": "了解产品优缺点，辅助购买决策",
        "经验分享": "学习实战经验，避免踩坑",
        "工具推荐": "发现提升效率的实用工具",
        "行业资讯": "了解最新行业动态和趋势",
        "职场成长": "获取职业发展的思路和方法",
        "生活分享": "获得生活灵感或实用建议",
        "内容分享": "获取该领域的知识和信息",
    }
    val = value_map.get(content_type, value_map["内容分享"])
    keypoints.append(val)

    # 要点3: 适合人群
    if audience and audience != ["通用受众"]:
        keypoints.append(f"适合{'、'.join(audience)}")

    # 要点4: 具体知识点/技能点
    if clean_desc:
        skills = re.findall(
            r'(?:使用|利用|借助|通过|掌握|学会|实现|创建|制作|开发|设计|优化|解决|提升|完成|搭建|配置|部署|调试|测试|分析|整理|规划)[^，。！？\n]{2,25}',
            clean_desc
        )
        if skills:
            keypoints.append(f"涉及技能：{'；'.join(skills[:2])}")

    # 要点5: 转写亮点
    if transcribe_text and len(transcribe_text) > 100:
        sents = [s.strip() for s in re.split(r'[。！？\n]', transcribe_text)
                 if 15 < len(s.strip()) < 80][:2]
        for sent in sents:
            keypoints.append(sent)

    # 去重
    seen = set()
    return [kp for kp in keypoints if not (kp[:15] in seen or seen.add(kp[:15]))][:6]


def _generate_intelligent_tags(tools, topic, content_type, original_tags):
    """生成更精准的内容标签"""
    ai_tags = []

    # 从工具名提取标签（去掉描述部分）
    for tool_desc in tools:
        tag = tool_desc.split('（')[0].strip()
        if tag and tag not in ai_tags and len(tag) <= 12:
            ai_tags.append(tag)

    # 内容类型作为标签
    if content_type and content_type not in ai_tags and content_type != "内容分享":
        ai_tags.append(content_type)

    # 从原始标签筛选有意义的
    for tag in original_tags:
        if not tag or tag in ai_tags:
            continue
        # 过滤太长的标签（通常是句子碎片）
        if len(tag) <= 8:
            ai_tags.append(tag)

    # 从主题中推断领域标签
    if topic:
        topic_lower = topic.lower()
        domains = {
            "前端": "前端开发", "后端": "后端开发", "全栈": "全栈开发",
            "ai": "人工智能", "人工智能": "人工智能", "大模型": "大模型",
            "设计": "设计", "产品": "产品", "运营": "运营",
            "创业": "创业", "副业": "副业", "赚钱": "商业",
            "面试": "面试", "求职": "求职", "职场": "职场",
            "考研": "考研", "留学": "留学",
            "美食": "美食", "旅游": "旅游", "健身": "健身",
        }
        for keyword, domain_tag in domains.items():
            if keyword in topic_lower and domain_tag not in ai_tags:
                ai_tags.append(domain_tag)

    return ai_tags[:8]


def suggest_category_from_analysis(ai_summary, ai_tags, ai_keypoints):
    """根据 AI 分析结果建议更准确的分类

    当 AI 分析完成后调用，结合摘要和 AI 标签重新判断最佳分类。
    返回建议的分类名称，如果无法确定则返回 None。

    Returns:
        str or None: 建议的分类名称
    """
    # 合并所有分析结果作为分类判断的输入
    combined = f"{ai_summary} {' '.join(ai_tags)} {' '.join(ai_keypoints)}"

    # 导入分类模块进行判断
    try:
        from category import auto_category
        suggested = auto_category(ai_tags, ai_summary, "")
        return suggested if suggested and suggested != "其他" else None
    except Exception:
        return None


def _generate_local_summary(title, author, description, tags, transcribe_text):
    """增强的本地规则生成摘要（无需 API 密钥）

    基于视频元数据做深度内容分析：
    - 识别核心技术工具
    - 判断内容类型（教程/科普/评测/分享等）
    - 提取核心主题
    - 识别目标受众
    - 生成结构化摘要（讲什么+学什么）
    - 提取知识要点和学习价值
    """
    # 标准化输入
    title = (title or "").strip()
    description = (description or "").strip()
    tags = tags if isinstance(tags, list) else ([tags] if tags else [])
    
    # 合并文本用于分析
    combined_text = f"{title} {description}"
    
    # 执行多维度分析
    tools = _detect_tools(combined_text)
    content_type = _detect_content_type(combined_text)
    topic = _extract_core_topic(title, description, tags)
    audience = _detect_audience(combined_text, tags)
    
    # 生成摘要
    summary = _generate_intelligent_summary(
        tools, content_type, topic, audience, title, description, transcribe_text
    )
    
    # 生成要点
    keypoints = _generate_intelligent_keypoints(
        tools, content_type, topic, audience, title, description, transcribe_text, tags
    )
    
    # 生成标签
    ai_tags = _generate_intelligent_tags(tools, topic, content_type, tags)
    
    return {
        "summary": summary,
        "keypoints": keypoints,
        "tags": ai_tags,
    }


# -------------------------------------------------------------------
# 5. 完整分析流程
# -------------------------------------------------------------------
async def analyze_video(video_url, title, author, description, tags, config=None):
    """完整 AI 分析流程

    Args:
        video_url: 视频下载地址
        title, author, description, tags: 视频元数据
        config: 配置字典，包含 baidu_speech 和 qianfan 的 API 密钥

    Returns:
        dict: {summary, keypoints, tags, transcribe_text}
    """
    config = config or {}
    baidu_config = config.get("baidu_speech", {})
    qianfan_config = config.get("qianfan", {})

    transcribe_text = ""
    audio_extracted = False

    if video_url:
        # 创建临时目录
        tmp_dir = tempfile.mkdtemp(prefix="douyin_analyze_")
        video_path = os.path.join(tmp_dir, "video.mp4")
        audio_path = os.path.join(tmp_dir, "audio.wav")

        try:
            # 步骤 1: 下载视频
            await download_video(video_url, video_path)

            # 检查文件大小
            if os.path.getsize(video_path) < 1000:
                raise RuntimeError("下载的视频文件过小，可能无效")

            # 步骤 2: 提取音频
            extract_audio(video_path, audio_path)
            audio_extracted = True

            # 步骤 3: 语音转文字
            transcribe_text = transcribe_audio(audio_path, baidu_config)

        except Exception as e:
            # 音频提取或转写失败，继续用元数据生成摘要
            print(f"音频处理失败: {e}, 将仅使用元数据生成摘要")
            transcribe_text = ""
        finally:
            # 清理临时文件
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        # 没有视频 URL，仅基于元数据生成摘要
        transcribe_text = ""

    # 步骤 4: 生成摘要
    result = await generate_summary(
        title, author, description, tags, transcribe_text, qianfan_config
    )
    result["transcribe_text"] = transcribe_text

    return result
