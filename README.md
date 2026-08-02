# 抖音视频收藏夹 · AI智能分析版

> 一个基于 FastAPI + Vue3 的抖音视频收藏管理工具，支持自动解析、AI内容分析、智能分类和全文检索，帮助你将零散的视频收藏转化为可检索的个人知识库。

---

## 功能特性

- **一键收藏** — 粘贴抖音分享链接，自动提取标题、作者、描述、标签、封面图
- **AI内容分析** — 基于本地规则引擎识别视频主题、内容类型、目标受众，自动生成结构化摘要（无需外部API密钥也可工作）
- **智能分类** — 根据标签和描述关键词自动归类（教育/科技/美食/娱乐等），支持手动调整
- **全文检索** — SQLite FTS5 全文搜索，支持跨标题、描述、标签、AI分析摘要的多维搜索
- **卡片式浏览** — 响应式网格布局，支持分类筛选、状态标识、封面图代理加载
- **详情弹窗** — 居中小卡片展示视频完整信息，支持重新分析、分类编辑、跳转原视频

---

## 技术架构

| 层级 | 技术栈 | 说明 |
|------|--------|------|
| 后端 | Python 3.12+, FastAPI, Uvicorn | RESTful API + 异步处理 |
| 数据库 | SQLite + FTS5 | 轻量级全文检索 |
| 前端 | Vue 3, Element Plus, Vite | 组件化UI框架 |
| 数据抓取 | httpx + BeautifulSoup4 + lxml | 移动端UA解析抖音分享页 |
| AI分析 | 本地规则引擎 + 可选百度API | 双模式：basic（本地）/ full（API） |

---

## 快速开始

### 1. 环境要求

- Python 3.12+
- Node.js 18+
- FFmpeg（可选，用于 full 模式的音频提取）

### 2. 安装后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端启动在 `http://localhost:8000`，API 文档见 `http://localhost:8000/docs`

### 3. 安装前端

```bash
cd frontend
npm install
npm run dev
```

前端启动在 `http://localhost:5173`

### 4. 使用

1. 打开 `http://localhost:5173`
2. 点击左侧「+ 收藏视频」或右上角搜索栏旁的收藏按钮
3. 粘贴抖音分享文本（例如：`7.12 复制打开抖音，看看【xxx】的作品 https://v.douyin.com/xxxxx/`）
4. 系统自动解析并保存
5. 在视频库页面可以搜索、筛选、查看详情

---

## 项目结构

```
douyin-collector/
├── backend/
│   ├── main.py              # FastAPI 入口，REST API 路由
│   ├── database.py          # SQLite 数据层（CRUD + FTS5 全文索引）
│   ├── parser.py            # 抖音链接解析器（短链转视频ID + 元数据提取）
│   ├── analyzer.py          # AI 分析模块（本地规则引擎 + 可选外部API）
│   ├── category.py          # 自动分类器（关键词匹配）
│   ├── requirements.txt     # Python 依赖
│   └── data/
│       └── videos.db        # SQLite 数据库（运行时自动创建）
├── frontend/
│   ├── package.json         # npm 配置
│   ├── vite.config.js       # Vite 构建配置
│   ├── index.html           # 入口 HTML
│   └── src/
│       ├── main.js          # Vue 应用启动
│       ├── App.vue          # 主页面组件（侧边栏 + 路由页 + 弹窗）
│       └── api.js           # Axios API 客户端
├── README.md                # 本文件
└── DEVELOPMENT.md           # 开发文档（架构设计、API详情、扩展指南）
```

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/videos` | 收藏视频（body: `{"share_text": "..."}`） |
| GET | `/api/videos` | 视频列表（query: `page`, `size`, `q`, `category`） |
| GET | `/api/videos/{id}` | 视频详情 |
| DELETE | `/api/videos/{id}` | 删除视频 |
| PATCH | `/api/videos/{id}` | 更新分类（body: `{"category": "..."}`） |
| POST | `/api/videos/{id}/analyze` | 触发 AI 分析 |
| GET | `/api/videos/{id}/analyze` | 查询分析状态/结果 |
| GET | `/api/categories` | 分类列表（含计数） |
| GET | `/api/env-check` | 环境检查（返回 whisper/ffmpeg/API 状态） |
| GET | `/api/proxy-image` | 封面图代理（query: `url`） |

详见 [DEVELOPMENT.md](DEVELOPMENT.md) 中的「API 详细说明」章节。

---

## AI 分析双模式

本系统支持两种 AI 分析模式，自动根据环境配置选择：

| 模式 | 触发条件 | 能力 |
|------|----------|------|
| **basic** | 默认模式（无 API 密钥） | 基于元数据 + 本地规则引擎：识别技术工具、内容类型、目标受众，生成结构化摘要 |
| **full** | 配置百度语音识别 + 千帆大模型 API 密钥后 | 下载视频 → 提取音频 → 语音转写 → 大模型生成深度摘要和关键词 |

**无需配置密钥即可使用**，basic 模式已能覆盖大部分场景。

---

## 部署说明

### 开发环境（默认）

前后端分离运行，前端通过 Vite DevServer 代理 API 请求到后端。

### 生产部署

```bash
# 前端构建
cd frontend
npm run build
# 产物输出到 frontend/dist/

# 后端直接运行（或使用 gunicorn/uvicorn 生产配置）
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

前端构建产物为纯静态文件，可部署到任意 Web 服务器（Nginx、Vercel、GitHub Pages 等）。

### 环境变量

```bash
# 可选：启用 full 模式
BAIDU_APP_ID=xxx
BAIDU_API_KEY=xxx
BAIDU_SECRET_KEY=xxx
QIANFAN_ACCESS_KEY=xxx
QIANFAN_SECRET_KEY=xxx
```

---

## 后续开发计划

- [ ] 浏览器插件：一键收藏当前页抖音视频
- [ ] 批量导入：支持 Excel/JSON 批量导入已有收藏
- [ ] 视频播放：内嵌播放器直接观看（需处理抖音反爬）
- [ ] 导出功能：支持导出为 Markdown/Notion/飞书文档
- [ ] 定时同步：自动检查收藏视频状态（是否删除/不可见）

---

## 截图

> 项目界面截图可在此处补充

### 数据概览页

![数据概览](screenshots/dashboard.png)

### 视频库浏览

![视频库](screenshots/library.png)

### 收藏弹窗

![收藏视频](screenshots/collect.png)

### 详情弹窗

![视频详情](screenshots/detail.png)

---

## 许可证

MIT License
