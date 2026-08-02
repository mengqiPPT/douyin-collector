# 抖音视频收藏夹 · AI 智能分析系统

## 产品文档

> 版本：2.0 | 更新日期：2026-08-03

---

## 一、项目简介与产品定位

### 1.1 项目概述

**抖音视频收藏夹**是一个桌面端全栈工具，用于收藏、管理和深度分析抖音视频内容。用户粘贴抖音分享链接即可一键收藏，系统自动提取视频元数据，并通过 **DeepSeek + 通义千问（Qwen）双引擎** 进行 AI 内容分析，将零散的视频收藏转化为可检索、可回顾的个人知识库。

### 1.2 产品定位

| 维度 | 说明 |
|------|------|
| **目标用户** | 日常刷抖音时积累大量收藏、希望系统化管理和回顾内容的个人用户 |
| **核心价值** | 收藏 → 自动 AI 分析 → 智能分类 → 全文检索，形成闭环 |
| **差异化** | 不只是"收藏夹"，而是带 AI 内容理解能力的知识管理工具 |
| **运行方式** | 本地启动前后端，浏览器访问操作 |

### 1.3 核心功能

| 功能 | 说明 |
|------|------|
| **一键收藏** | 粘贴抖音分享文本，自动提取标题、作者、描述、话题标签、封面图、视频地址、作者头像、点赞/评论/转发数、时长 |
| **多引擎 AI 分析** | DeepSeek（主力文本分析）+ Qwen（多模态 VL/Audio），自动生成摘要、核心要点、AI 标签、内容质量评分 |
| **收藏即分析** | 收藏后自动在后台触发 AI 分析，无需手动点击 |
| **智能分类** | 8 大类 35 子分类，含"AI 内容创作"专属分类（AI 短剧/动漫/漫剧），LLM 辅助精准归类 |
| **全文检索** | SQLite FTS5 全文搜索 + AI 查询语义扩展 |
| **卡片式浏览** | 响应式网格布局，分类筛选，作者头像、互动数据展示，详情弹窗 |

---

## 二、在线链接

本项目为**本地运行**工具，启动后访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | `http://localhost:5173` | Vue 3 开发服务器 |
| 后端 API | `http://localhost:8000` | FastAPI 服务 |
| API 文档 | `http://localhost:8000/docs` | Swagger 交互式文档 |
| 环境检查 | `http://localhost:8000/api/env-check` | 返回 AI Provider、FFmpeg 状态 |

---

## 三、启动方式与环境变量

### 3.1 环境要求

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | ≥ 3.12 | 后端运行时 |
| Node.js | ≥ 18 | 前端构建 |
| FFmpeg | 任意版本 | 视频音频提取（可选，AI 分析 Full 模式需要） |
| pip | — | Python 包管理 |
| npm | — | Node 包管理 |

### 3.2 快速启动

**第一步：启动后端**

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端启动在 `http://localhost:8000`，接口文档见 `http://localhost:8000/docs`。

**第二步：启动前端**

```bash
cd frontend
npm install
npm run dev
```

前端启动在 `http://localhost:5173`，Vite DevServer 自动将 `/api` 请求代理到后端。

### 3.3 环境变量

系统通过环境变量读取 API 密钥。**最低只需配置 `DEEPSEEK_API_KEY` 即可启用 AI 文本分析**。

| 变量名 | 必填 | 说明 | 申请地址 |
|--------|------|------|----------|
| `DEEPSEEK_API_KEY` | 推荐 | DeepSeek 文本分析（中文强、价格低） | https://platform.deepseek.com |
| `QWEN_API_KEY` | 可选 | 通义千问多模态（封⾯理解 + 音频分析） | https://dashscope.aliyun.com |
| `BAIDU_APP_ID` | 可选 | 百度语音识别 App ID | https://ai.baidu.com |
| `BAIDU_API_KEY` | 可选 | 百度语音识别 API Key | https://ai.baidu.com |
| `BAIDU_SECRET_KEY` | 可选 | 百度语音识别 Secret Key | https://ai.baidu.com |
| `QIANFAN_AK` | 可选 | 百度千帆大模型 Access Key | https://console.bce.baidu.com |
| `QIANFAN_SK` | 可选 | 百度千帆大模型 Secret Key | https://console.bce.baidu.com |
| `FFMPEG_PATH` | 可选 | FFmpeg 可执行文件路径（系统自动检测） | — |

**配置方式**（以 DeepSeek 为例）：

```bash
# Linux / macOS
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Windows PowerShell
$env:DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Windows CMD
set DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3.4 分析模式与降级路径

系统根据可用 API 自动选择分析模式：

```
DEEPSEEK_API_KEY 可用 ──→ DeepSeek 主力文本分析 ✨ (最佳)
         │
         ├── QWEN_API_KEY 可用 ──→ Qwen-VL 封面画面理解 🖼️
         │                         Qwen-Audio 音频内容转写 🎙️
         │
         └── 无任何 API ──→ 本地规则引擎回退 (关键词匹配)
```

**无 API 时也能跑**：收藏正常，分类靠关键词匹配，分析用本地模板引擎生成基础摘要。配置 DeepSeek 后质量质变。

---

## 四、核心使用流程与 AI 介入环节

### 4.1 总体流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① 粘贴链接   │───▶│  ② 解析存储   │───▶│  ③ 自动分析   │───▶│  ④ 检索回顾   │
│  分享文本     │    │  元数据提取   │    │  AI 后台执行   │    │  搜索/分类    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 4.2 各环节详解

#### 环节 ①：收藏视频

**操作**：点击「收藏视频」，粘贴抖音分享文本。

**输入示例**：
```
6.61 复制打开抖音，看看【菲菲】的作品 https://v.douyin.com/owuA_MZHJOE/
```

**AI 介入**：正则提取抖音 URL（支持短链中下划线格式如 `owuA_MZHJOE`）。

#### 环节 ②：解析存储

**AI 介入**：三层回退策略抓取视频元数据。

| 策略 | 方式 | 说明 |
|------|------|------|
| **策略 1** | 完整 JSON 解析（RENDER_DATA / item_list） | 最可靠，解析页面内嵌结构化数据 |
| **策略 2** | 正则片段提取（desc / nickname / hashtag / cover） | 策略 1 失败时的回退 |
| **策略 3** | SEO meta 标签回退（og:title / og:image） | 最终兜底方案 |

**提取字段**：

| 字段 | 说明 |
|------|------|
| title | 视频标题 |
| author | 作者昵称 |
| author_avatar | 作者头像 URL |
| description | 视频描述 |
| tags | 话题标签列表 |
| cover_url | 封面图 URL |
| video_url | 视频播放地址 |
| like_count | 点赞数 |
| comment_count | 评论数 |
| share_count | 转发数 |
| duration | 视频时长（秒） |

**初始分类**：解析完成后，本地关键词引擎执行初始分类。内置 8 大类 35 子分类：

| 大类 | 子分类 |
|------|--------|
| **编程开发** | 前端开发、后端开发、AI/算法、移动开发、DevOps |
| **AI 与数据** | AI 工具应用、**AI 内容创作**、数据分析、AI 资讯 |
| **设计创意** | UI/UX 设计、平面/品牌、三维/动效、视频剪辑 |
| **科技数码** | 手机/平板、电脑/硬件、数码产品、软件/App |
| **职场商业** | 求职面试、职场技能、商业/创业、产品/运营 |
| **学习成长** | 编程学习、语言学习、考试考证、通识/科普 |
| **生活兴趣** | 美食烹饪、旅行摄影、健身运动、家居/穿搭、宠物/植物 |
| **娱乐综艺** | 综艺/搞笑、影视剧、音乐/舞蹈、游戏电竞 |

其中 **AI 内容创作** 是专为 AI 生成内容设计的分类，覆盖 AI 短剧、AI 动漫、AI 漫剧、AI 动画、AIGC、数字人等垂直领域，能准确区分"AI 技术教程"和"AI 生成作品"。

#### 环节 ③：AI 深度分析（自动后台执行）

**AI 介入：多引擎接力分析，这是系统最核心的 AI 环节。**

收藏成功后系统**自动在后台**启动四阶段分析：

```
┌──────────────────────────────────────────────────┐
│  阶段 1：本地语音引擎                              │
│  下载视频 → FFmpeg 提取音频 → ASR 语音转文字       │
│  失败自动跳过，不影响后续分析                       │
├──────────────────────────────────────────────────┤
│  阶段 2：Qwen-VL 多模态画面理解（需 QWEN_API_KEY）  │
│  分析封面图 → 描述场景、人物、文字、氛围            │
├──────────────────────────────────────────────────┤
│  阶段 3：DeepSeek / Qwen LLM 深度内容分析          │
│  输入：标题 + 描述 + 标签 + 语音转写 + 画面描述     │
│  输出：自然语言摘要 + 核心要点 + AI 标签 + 质量评分  │
│  优先 DeepSeek → 回退 Qwen → 回退本地规则引擎      │
├──────────────────────────────────────────────────┤
│  阶段 4：LLM 智能分类修正                          │
│  基于分析结果建议最佳分类，覆盖初始关键词分类        │
└──────────────────────────────────────────────────┘
```

**分析输出示例**（AI 动漫短剧《我凭发疯出道》）：

| 输出项 | 内容 |
|--------|------|
| **摘要** | "一部 AI 生成的动漫短剧合集《我凭发疯出道》1-5 集，讲述主角通过发疯式行为在职场逆袭的搞笑故事…" |
| **要点** | [AI 生成的国漫短剧 5 集合一完整故事线, 主角通过出格行为对抗职场不公, AIGC 技术赋能动漫创作…] |
| **AI 标签** | [AIGC, AI 动漫, AI 动画, 国漫, 逆袭, 搞笑短剧] |
| **分类** | 初始"AI/算法" → LLM 修正为 **"AI 内容创作"** |

#### 环节 ④：搜索与检索

**AI 介入**：用户输入搜索词后，系统调用 LLM 将查询语义扩展为多个同义/相关词，提升 FTS5 全文搜索召回率。

```
用户输入 "AI漫画"
    ↓ LLM 扩展
["AI漫画", "AI短剧", "AI动漫", "AIGC", "AI动画"]
    ↓ FTS5 全文检索
→ 返回所有匹配视频
```

#### 环节 ⑤：详情查看与手动操作

在详情弹窗中可操作：
- 查看 AI 分析结果（摘要、要点、标签、分析来源）
- 手动修改分类（下拉菜单即时切换）
- 点击「重新分析」触发新一轮 AI 分析
- 点击「打开原视频」跳转抖音观看
- 查看作者头像、互动数据（⭐点赞 💬评论 ↗转发）

---

## 五、技术栈清单

### 5.1 后端

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.115.6 | RESTful API + Swagger 文档 |
| ASGI 服务器 | Uvicorn | 0.34.0 | 异步 HTTP + 热重载 |
| HTTP 客户端 | httpx | 0.28.1 | 抖音页面抓取 + LLM API 调用 |
| HTML 解析 | BeautifulSoup4 | 4.12.3 | HTML 解析 |
| XML 解析 | lxml | 5.3.0 | 快速 XML/HTML 解析 |
| 文件上传 | python-multipart | 0.0.20 | 表单数据解析 |
| 数据库 | SQLite + FTS5 | 内置于 Python | 数据存储 + 全文索引 |
| **LLM 主力** | **DeepSeek API** | `deepseek-chat` | 文本分析（中文最强、成本极低） |
| **多模态 AI** | **通义千问 (Qwen)** | `qwen-plus / qwen-vl-plus / qwen-audio-turbo` | 文本备选 + 封面理解 + 音频理解 |
| 语音识别 | 百度 AI (baidu-aip) | 4.16.13 | 语音转文字（可选） |
| 本地 ASR | OpenAI Whisper | 可选安装 | 本地语音识别（无需 API） |
| 大模型（旧版） | 千帆 (qianfan) | 0.4.12.3 | 百度千帆 LLM（可选） |
| 音频处理 | FFmpeg | 任意版本 | 视频 → 音频提取 |

### 5.2 前端

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Vue 3 | ^3.4.21 | Composition API |
| UI 库 | Element Plus | ^2.7.0 | 弹窗、按钮、表格等组件 |
| 构建工具 | Vite | ^5.2.0 | 开发服务器 + 生产构建 |
| HTTP | Axios | ^1.6.8 | API 请求 |
| 图标 | @element-plus/icons-vue | 内置于 Element Plus | 图标组件 |

### 5.3 项目结构

```
douyin-collector/
├── README.md                         # 项目说明
├── DEVELOPMENT.md                    # 开发文档（架构设计、API 详情）
├── PRODUCT.md                        # 本文件（产品文档）
├── vercel.json                       # Vercel 部署配置
├── requirements.txt                  # Python 依赖（根目录副本）
│
├── backend/                          # 后端（Python + FastAPI）
│   ├── main.py                       # API 入口 + 路由 + 异常处理
│   ├── database.py                   # SQLite 数据层 + FTS5 全文索引
│   ├── parser.py                     # 抖音链接解析器（三层回退）
│   ├── analyzer.py                   # 本地分析引擎 + FFmpeg 音频处理
│   ├── category.py                   # 自动分类器（8 大类 35 子分类）
│   ├── requirements.txt              # Python 依赖
│   └── ai/                           # AI Provider 模块
│       ├── base.py                   # AnalysisResult + BaseAIProvider 接口
│       ├── deepseek.py               # DeepSeek Provider
│       ├── qwen.py                   # Qwen Provider（含 VL/Audio 多模态）
│       ├── provider.py               # AIProviderHub 多引擎调度中心
│       └── prompts.py                # 统一 Prompt 模板
│
├── frontend/                         # 前端（Vue 3 + Vite）
│   ├── index.html                    # 入口 HTML
│   ├── package.json                  # npm 配置
│   ├── vite.config.js                # Vite 构建配置
│   ├── .env.example                  # 环境变量示例
│   └── src/
│       ├── main.js                   # Vue 应用启动
│       ├── App.vue                   # 根组件（布局 + 状态管理）
│       ├── api.js                    # Axios API 客户端
│       └── components/
│           ├── Sidebar.vue           # 侧边栏导航
│           ├── Dashboard.vue         # 数据概览仪表盘
│           ├── VideoLibrary.vue      # 视频库（卡片网格）
│           ├── VideoCard.vue         # 视频卡片组件
│           ├── CollectDialog.vue     # 收藏弹窗
│           ├── DetailDialog.vue      # 详情弹窗
│           └── dashboard/            # 仪表盘子组件
│               ├── StatCard.vue      # 统计卡片
│               ├── AnalysisRing.vue  # 环形分析进度图
│               ├── CategoryCloud.vue # 分类标签云
│               └── QuickActions.vue  # 快捷操作
│
└── api/                              # Vercel Serverless 入口
    └── index.py
```

### 5.4 API 接口清单

| 方法 | 路径 | 说明 | AI 介入 |
|------|------|------|---------|
| `POST` | `/api/videos` | 收藏视频 | 初始关键词分类 + 自动触发后台 AI 分析 |
| `GET` | `/api/videos` | 视频列表（分页+搜索+分类） | LLM 搜索查询扩展 |
| `GET` | `/api/videos/{id}` | 视频详情 | — |
| `DELETE` | `/api/videos/{id}` | 删除视频 | — |
| `PATCH` | `/api/videos/{id}` | 更新分类 | — |
| `POST` | `/api/videos/{id}/analyze` | 触发 AI 分析 | 四阶段 LLM 分析管线 |
| `GET` | `/api/videos/{id}/analyze` | 查询分析状态/结果 | — |
| `GET` | `/api/categories` | 分类列表（含计数） | — |
| `GET` | `/api/env-check` | 环境检查 | 返回 AI Provider 状态 |
| `GET` | `/api/proxy-image` | 封面图代理 | — |

### 5.5 数据库表结构

**videos 表**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| url | TEXT UNIQUE | 抖音分享短链 |
| video_url | TEXT | 视频播放地址 |
| title | TEXT | 标题 |
| author | TEXT | 作者昵称 |
| author_avatar | TEXT | 作者头像 URL |
| description | TEXT | 描述文本 |
| tags | TEXT (JSON) | 话题标签数组 |
| cover_url | TEXT | 封面图 URL |
| category | TEXT | 分类名称 |
| like_count | INTEGER | 点赞数 |
| comment_count | INTEGER | 评论数 |
| share_count | INTEGER | 转发数 |
| duration | INTEGER | 时长（秒） |
| created_at | TEXT | 收藏时间（ISO 格式） |
| analyze_status | TEXT | 分析状态：pending / analyzing / done / failed |
| ai_summary | TEXT | AI 生成摘要 |
| ai_keypoints | TEXT (JSON) | 核心要点数组 |
| ai_tags | TEXT (JSON) | AI 标签数组 |
| transcribe_text | TEXT | 语音转写文本 |
| analyzed_at | TEXT | 分析完成时间 |

**videos_fts 虚拟表**（FTS5 全文索引，插入/更新/删除自动同步）

| 索引字段 |
|----------|
| title |
| description |
| tags |
| author |

---

*文档版本 2.0 | 最后更新 2026-08-03*
