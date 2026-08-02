# 抖音视频收藏夹 · AI 智能分析系统

## 产品文档

> 版本：2.0.0 | 更新日期：2026-08-02

---

## 一、项目简介与产品定位

### 1.1 项目概述

**抖音视频收藏夹**是一个基于 FastAPI + Vue 3 的抖音视频收藏管理工具。用户粘贴抖音分享链接即可一键收藏，系统自动提取视频元数据（标题、作者、封面图、点赞/评论/转发数据、作者头像），并通过 **DeepSeek + 通义千问（Qwen）双引擎 AI** 进行深度内容分析与智能分类，将零散的视频收藏转化为可检索、可发现、可回顾的个人知识库。

### 1.2 产品定位

| 维度 | 定位 |
|------|------|
| **目标用户** | 日常刷抖音时积累大量收藏、希望系统化管理和回顾视频内容的个人用户 |
| **核心价值** | 收藏 → 自动 AI 分析 → 智能分类 → 全文检索，形成闭环 |
| **差异化** | 不是简单的"收藏夹"，而是带 AI 内容理解能力的知识管理工具 |
| **使用场景** | 技术教程收藏后自动归类到"编程学习"；AI 短剧/动漫自动识别为"AI 内容创作"；搜索"Python 数据分析"能扩展到同义词匹配 |

### 1.3 核心功能矩阵

| 功能 | 说明 |
|------|------|
| **一键收藏** | 粘贴抖音分享文本，自动提取标题、作者、描述、标签、封面图、视频地址、作者头像、点赞/评论/转发数、时长 |
| **多引擎 AI 分析** | DeepSeek 主力文本分析 + Qwen 多模态（VL 封面理解 + Audio 语音理解），自动生成摘要、核心要点、AI 标签 |
| **智能分类** | 8 大类 35 个子分类（含 AI 短剧/动漫/漫剧 的"AI 内容创作"专属分类），LLM 辅助精准归类 |
| **收藏即分析** | 收藏成功后自动触发后台 AI 分析，无需手动操作 |
| **全文检索** | SQLite FTS5 全文搜索 + AI 搜索查询扩展（如搜"AI漫画"自动扩展为"AI短剧"、"AIGC"、"AI动画"） |
| **封面图代理** | 后端中转抖音封面图，解决跨域加载问题 |
| **响应式 UI** | 侧边栏导航、数据概览仪表盘、卡片网格浏览、详情弹窗 |

---

## 二、在线链接

| 环境 | 地址 | 说明 |
|------|------|------|
| **前端页面** | `http://localhost:5173` | Vue 3 开发服务器 |
| **后端 API** | `http://localhost:8000` | FastAPI 服务 |
| **API 文档（Swagger）** | `http://localhost:8000/docs` | 交互式 API 文档 |
| **环境检查** | `http://localhost:8000/api/env-check` | 返回 AI Provider 状态、FFmpeg 可用性等 |

---

## 三、启动方式与环境变量

### 3.1 环境要求

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| Python | ≥ 3.12 | 后端运行时 |
| Node.js | ≥ 18 | 前端构建与开发 |
| FFmpeg | 任意版本 | 视频音频提取（AI 分析 full 模式需要，basic 模式可选） |
| pip | — | Python 包管理 |
| npm | — | Node 包管理 |

### 3.2 快速启动

**第一步：安装并启动后端**

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端启动后在 `http://localhost:8000` 提供 API 服务，`http://localhost:8000/docs` 可查看交互式 API 文档。

**第二步：安装并启动前端**

```bash
cd frontend
npm install
npm run dev
```

前端启动后在 `http://localhost:5173` 提供页面服务，Vite DevServer 自动将 `/api` 请求代理到后端 `http://localhost:8000`。

### 3.3 环境变量

系统支持通过环境变量配置所有 API 密钥，优先级：**环境变量 > 代码内默认值**。

```bash
# ===== LLM Provider（核心 AI 分析）=====

# DeepSeek API Key（主力文本分析模型，中文能力强、成本极低）
# 申请地址：https://platform.deepseek.com
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 通义千问 API Key（多模态 + 备选文本分析）
# 申请地址：https://dashscope.aliyun.com
export QWEN_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ===== 语音识别（可选，Full 模式需要）=====

# 百度语音识别
export BAIDU_APP_ID="xxxxxxxxx"
export BAIDU_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export BAIDU_SECRET_KEY="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 千帆大模型（可选，旧版兼容）
export QIANFAN_AK="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export QIANFAN_SK="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ===== 其他 =====

# FFmpeg 自定义路径（通常无需设置，系统自动检测）
export FFMPEG_PATH="/path/to/ffmpeg"
```

**LLM Provider 建议**：最低只需配置 `DEEPSEEK_API_KEY` 即可获得完整的 AI 文本分析能力。免费额度充足（注册赠送数百万 token），日常使用成本极低（约 ¥1/百万 token）。如需多模态能力（封面图画面理解、音频内容分析），再配置 `QWEN_API_KEY`。

### 3.4 生产部署

```bash
# 前端构建
cd frontend && npm run build
# 产物输出到 frontend/dist/

# 后端生产启动
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

前端构建产物为纯静态文件，可部署到任意 Web 服务器（Nginx、Vercel、GitHub Pages 等）。后端建议使用 Nginx 反向代理并配置 HTTPS。

---

## 四、核心使用流程与 AI 介入环节

### 4.1 总体流程

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  ① 粘贴链接   │───▶│  ② 解析存储   │───▶│  ③ 自动分析   │───▶│  ④ 检索回顾   │
│  分享文本     │    │  元数据提取   │    │  AI 后台执行   │    │  搜索/分类    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 4.2 详细流程与 AI 介入环节

#### 环节 ①：收藏视频

**操作**：用户点击「收藏视频」，粘贴抖音分享文本。

**输入示例**：
```
6.61 复制打开抖音，看看【菲菲】的作品 https://v.douyin.com/owuA_MZHJOE/
```

**系统动作**：
- 正则提取抖音短链/长链（支持 `v.douyin.com` 短链中的下划线格式）
- 解析 `video_id` 并获取视频元数据（三层回退策略，见 4.3）

**提取的元数据字段**：

| 字段 | 说明 |
|------|------|
| title | 视频标题 |
| author | 作者昵称 |
| author_avatar | 作者头像 URL |
| description | 视频描述文本 |
| tags | 话题标签列表 |
| cover_url | 封面图 URL |
| video_url | 视频播放地址 |
| like_count | 点赞数 |
| comment_count | 评论数 |
| share_count | 转发数 |
| duration | 视频时长（秒） |

#### 环节 ②：初始分类

**AI 介入：关键词规则引擎（本地，无需 API）**

收藏完成后立即执行关键词匹配分类。系统内置 8 大类 35 个子分类：

| 大类 | 子分类 |
|------|--------|
| 编程开发 | 前端开发、后端开发、AI/算法、移动开发、DevOps |
| AI 与数据 | AI 工具应用、**AI 内容创作**、数据分析、AI 资讯 |
| 设计创意 | UI/UX 设计、平面/品牌、三维/动效、视频剪辑 |
| 科技数码 | 手机/平板、电脑/硬件、数码产品、软件/App |
| 职场商业 | 求职面试、职场技能、商业/创业、产品/运营 |
| 学习成长 | 编程学习、语言学习、考试考证、通识/科普 |
| 生活兴趣 | 美食烹饪、旅行摄影、健身运动、家居/穿搭、宠物/植物 |
| 娱乐综艺 | 综艺/搞笑、影视剧、音乐/舞蹈、游戏电竞 |

其中 **AI 内容创作**是专为 AI 生成内容设计的分类，覆盖 AI 短剧、AI 动漫、AI 漫剧、AI 动画、AIGC、数字人等垂直领域。

#### 环节 ③：AI 深度分析（自动后台执行）

**AI 介入：多引擎接力分析，这是系统最核心的 AI 环节。**

收藏成功后，系统**自动在后台**启动四阶段 AI 分析：

```
┌─────────────────────────────────────────────────────────────────┐
│  阶段 1：本地语音引擎（20s 超时）                                │
│  ├─ 下载视频 → FFmpeg 提取音频 → 百度 ASR / Whisper 语音转文字  │
│  └─ 失败自动跳过，不影响后续分析                                  │
├─────────────────────────────────────────────────────────────────┤
│  阶段 2：Qwen-VL 多模态画面理解（需 QWEN_API_KEY）               │
│  ├─ 分析视频封面图，描述画面内容、场景、人物、文字信息            │
│  └─ 为 LLM 分析提供视觉上下文                                    │
├─────────────────────────────────────────────────────────────────┤
│  阶段 3：DeepSeek / Qwen LLM 深度内容分析                        │
│  ├─ 输入：标题 + 描述 + 标签 + 语音转写 + 画面描述               │
│  ├─ 输出：自然语言摘要（2-4 句）、核心要点（3-5 条）、AI 标签     │
│  ├─ 优先级：DeepSeek → 失败回退 Qwen → 失败回退本地规则引擎      │
│  └─ 关键区分：AI 技术教程 vs AI 生成作品（如 AI 短剧→AI 内容创作）│
├─────────────────────────────────────────────────────────────────┤
│  阶段 4：LLM 智能分类修正                                        │
│  ├─ DeepSeek/Qwen 基于分析结果建议最佳分类                       │
│  ├─ 覆盖初始关键词分类结果                                       │
│  └─ 失败回退到本地关键词辅助分类                                  │
└─────────────────────────────────────────────────────────────────┘
```

**AI 分析输出示例**（AI 动漫短剧《我凭发疯出道》）：

| 输出项 | 示例值 |
|--------|--------|
| 摘要 | "一部 AI 生成的动漫短剧合集《我凭发疯出道》1-5 集，讲述主角通过发疯式行为在职场逆袭的搞笑故事。作品呈现了 AI 在动漫创作领域的应用潜力，画面风格独特…" |
| 要点 | [AI 生成的国漫短剧 5 集合一, 主角通过出格行为对抗职场不公, AIGC 技术赋能动漫创作, …] |
| AI 标签 | [AIGC, AI 动漫, AI 动画, 国漫, 逆袭, 搞笑短剧] |
| 分类修正 | 初始分类 "AI/算法" → LLM 修正为 **"AI 内容创作"** |

#### 环节 ④：搜索与检索

**AI 介入：搜索查询语义扩展**

用户在搜索框输入关键词后，系统自动调用 LLM 将查询扩展为多个同义/相关词：

```
用户输入："AI漫画"
  ↓ LLM 扩展
搜索词：["AI漫画", "AI短剧", "AI动漫", "AIGC", "AI动画"]
  ↓ FTS5 全文检索
返回所有匹配的视频结果
```

#### 环节 ⑤：详情查看与手动操作

在详情弹窗中，用户可以：
- 查看 AI 生成的摘要、要点、标签、分析来源
- 手动修改分类
- 点击「重新分析」触发新一轮 AI 分析
- 点击「打开原视频」跳转到抖音观看
- 查看作者头像、互动数据（点赞/评论/转发）、视频时长

### 4.3 元数据解析回退策略

抖音分享页解析采用三层策略，保障元数据提取的鲁棒性：

| 策略 | 方式 | 可靠性 |
|------|------|--------|
| **策略 1** | 完整 JSON 解析（RENDER_DATA / item_list） | 最高 |
| **策略 2** | 正则片段提取（desc / nickname / hashtag / cover） | 中等 |
| **策略 3** | SEO meta 标签回退（og:title / og:image） | 兜底 |

### 4.4 分析模式与降级路径

```
┌──────────────────────────────────────────┐
│ AI 能力可用性检测（启动时 + 每次分析前）  │
├──────────────────────────────────────────┤
│ DeepSeek API ──→ 可用 ──→ 主力文本分析   │
│     │                                    │
│     └── 不可用 ──→ Qwen API ──→ 备选文本  │
│                          │               │
│                          └── 不可用       │
│                               │           │
│                               ▼           │
│                          本地规则引擎      │
│                          (关键词匹配)      │
├──────────────────────────────────────────┤
│ Qwen-VL API ──→ 可用 ──→ 封面画面分析    │
│ Qwen-Audio ──→ 可用 ──→ 音频内容理解     │
│ FFmpeg ──→ 可用 ──→ 视频下载+音频提取    │
└──────────────────────────────────────────┘
```

**最低可用配置**：即使没有任何 API 密钥，系统仍能工作——收藏正常，分类靠关键词匹配，分析靠本地规则引擎生成模板化摘要。配置 DeepSeek API 后，分析质量质变。

---

## 五、技术栈清单

### 5.1 后端

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Web 框架** | FastAPI | 0.115.6 | RESTful API 服务 + Swagger 自动文档 |
| **ASGI 服务器** | Uvicorn | 0.34.0 | 异步 HTTP 服务 + 热重载开发模式 |
| **HTTP 客户端** | httpx | 0.28.1 | 异步 HTTP 请求（抖音页面抓取 + LLM API 调用 + 图片代理） |
| **HTML 解析** | BeautifulSoup4 | 4.12.3 | HTML 解析（备用） |
| **XML 解析** | lxml | 5.3.0 | 快速 XML/HTML 解析器 |
| **文件上传** | python-multipart | 0.0.20 | 表单数据解析 |
| **数据库** | SQLite + FTS5 | 内置于 Python | 数据存储 + 全文检索索引 |
| **LLM Provider** | DeepSeek API | `deepseek-chat` | 主力文本分析（中文最强、成本极低） |
| **多模态 AI** | 通义千问 (Qwen) | `qwen-plus` / `qwen-vl-plus` / `qwen-audio-turbo` | 文本分析备选 + 封面图画面理解 + 音频内容理解 |
| **语音识别** | 百度 AI (baidu-aip) | 4.16.13 | 语音转文字（可选） |
| **本地 ASR** | OpenAI Whisper | 可选安装 | 本地语音识别（无需 API） |
| **大模型（旧版）** | 千帆 (qianfan) | 0.4.12.3 | 百度千帆 LLM（旧版兼容） |
| **音频处理** | FFmpeg | 任意版本 | 视频下载 → 音频提取（WAV 16kHz 单声道） |

### 5.2 前端

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | Vue 3 | ^3.4.21 | Composition API 组件化开发 |
| **UI 组件库** | Element Plus | ^2.7.0 | 弹窗、按钮、输入框、分页等 UI 组件 |
| **构建工具** | Vite | ^5.2.0 | 开发服务器 + HMR 热更新 + 生产构建 |
| **HTTP 客户端** | Axios | ^1.6.8 | API 请求 |
| **图标** | @element-plus/icons-vue | 内置于 Element Plus | 侧边栏、卡片、按钮图标 |

### 5.3 前端组件架构

```
frontend/src/
├── main.js                              # Vue 应用入口（Element Plus 全局注册）
├── api.js                               # Axios API 客户端封装
├── App.vue                              # 根组件：布局 + 状态管理 + 事件调度
└── components/
    ├── Sidebar.vue                      # 侧边栏（导航 + 分类列表 + AI 状态）
    ├── Dashboard.vue                    # 数据概览页（统计卡片 + 环形图 + 标签云 + 快捷操作）
    ├── VideoLibrary.vue                 # 视频库页（搜索栏 + 卡片网格 + 分页）
    ├── VideoCard.vue                    # 视频卡片（封面 + 作者头像 + 互动数据 + 标签）
    ├── CollectDialog.vue                # 收藏弹窗（分享文本输入）
    ├── DetailDialog.vue                 # 详情弹窗（AI 结果 + 分类编辑 + 删除）
    └── dashboard/
        ├── StatCard.vue                 # 统计卡片（渐变色条 + 数字动画）
        ├── AnalysisRing.vue             # SVG 环形分析进度图
        ├── CategoryCloud.vue            # 彩色分类标签云
        └── QuickActions.vue             # 快捷操作 / 新手指引
```

### 5.4 后端模块架构

```
backend/
├── main.py                              # FastAPI 入口（路由 + CORS + 异常处理 + AI Hub 初始化）
├── database.py                          # SQLite 数据层（CRUD + FTS5 全文索引 + 安全查询）
├── parser.py                            # 抖音链接解析器（三层回退 + 元数据提取）
├── analyzer.py                          # 本地分析引擎（FFmpeg 音频提取 + ASR + 关键词规则）
├── category.py                          # 自动分类器（8 大类 35 子分类，短关键词降权）
└── ai/
    ├── __init__.py                      # AI 模块入口
    ├── base.py                          # AnalysisResult 数据类 + BaseAIProvider 抽象接口
    ├── deepseek.py                      # DeepSeek Provider（Chat Completion API）
    ├── qwen.py                          # Qwen Provider（文本 + Qwen-VL + Qwen-Audio）
    ├── provider.py                      # AIProviderHub 多引擎调度中心（自动回退）
    └── prompts.py                       # 统一 Prompt 模板（分析/标签/分类/搜索扩展）
```

### 5.5 API 接口清单

| 方法 | 路径 | 说明 | AI 介入 |
|------|------|------|---------|
| `POST` | `/api/videos` | 收藏视频 | 初始关键词分类 + 自动触发后台 AI 分析 |
| `GET` | `/api/videos` | 视频列表（分页+搜索+分类过滤） | LLM 搜索查询扩展 |
| `GET` | `/api/videos/{id}` | 视频详情 | — |
| `DELETE` | `/api/videos/{id}` | 删除视频 | — |
| `PATCH` | `/api/videos/{id}` | 更新分类 | — |
| `POST` | `/api/videos/{id}/analyze` | 触发 AI 分析 | 四阶段 LLM 分析管線 |
| `GET` | `/api/videos/{id}/analyze` | 查询分析状态 | — |
| `GET` | `/api/categories` | 分类列表（含计数） | — |
| `GET` | `/api/env-check` | 环境检查 | 返回 AI Provider 状态 |
| `GET` | `/api/proxy-image` | 封面图代理 | — |

---

## 附录

### A. 数据库表结构

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
| analyze_status | TEXT | 分析状态：pending/analyzing/done/failed |
| ai_summary | TEXT | AI 生成摘要 |
| ai_keypoints | TEXT (JSON) | 核心要点数组 |
| ai_tags | TEXT (JSON) | AI 标签数组 |
| transcribe_text | TEXT | 语音转写文本 |
| analyzed_at | TEXT | 分析完成时间 |

**videos_fts 虚拟表**（FTS5 全文索引，自动同步 videos 表）

| 索引字段 |
|----------|
| title |
| description |
| tags |
| author |

### B. AI 分析质量评分维度

LLM 在分析视频时评估以下维度并输出结构化结果：

| 维度 | 说明 |
|------|------|
| **summary** | 2-4 句自然语言摘要，AI 生成内容注明具体的生成类型 |
| **keypoints** | 3-5 条核心要点，有剧情则提取关键剧情节点 |
| **tags** | 3-8 个精准标签（2-8 字），优先中文，标注内容类型 |
| **category** | LLM 建议的最佳分类，覆盖初始关键词分类 |
| **audience** | 适合观看的人群描述 |
| **difficulty** | 入门/进阶/高级（娱乐内容可为"娱乐"） |
| **quality_score** | 内容质量评分 0-100（AI 生成内容关注画面质量和剧情完整度） |

---

*文档版本 2.0.0 | 最后更新 2026-08-02*
