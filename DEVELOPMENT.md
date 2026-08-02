# 开发文档

> 本文档面向开发者和贡献者，说明系统架构、模块职责、数据流、API 设计和扩展开发指南。

---

## 目录

- [系统架构](#系统架构)
- [模块职责](#模块职责)
- [数据流](#数据流)
- [数据库设计](#数据库设计)
- [API 详细说明](#api-详细说明)
- [AI 分析模块设计](#ai-分析模块设计)
- [前端架构](#前端架构)
- [扩展开发指南](#扩展开发指南)
- [常见问题](#常见问题)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ 浏览器访问   │  │ 收藏弹窗    │  │ 搜索/筛选   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      前端层 (Vue3)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ App.vue      │  │ api.js      │  │ Element Plus │     │
│  │ (页面路由)   │  │ (HTTP客户端) │  │ (UI组件库)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
└─────────┼─────────────────┼─────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端层 (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ main.py      │  │ parser.py   │  │ analyzer.py │     │
│  │ (API路由)    │  │ (链接解析)  │  │ (AI分析)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│  ┌──────┴───────┐  ┌─────┴────────┐  ┌─────┴────────┐   │
│  │ database.py  │  │ category.py │  │ 外部API      │   │
│  │ (数据持久化) │  │ (自动分类)  │  │ (可选)       │   │
│  └──────┬───────┘  └─────────────┘  └──────────────┘   │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层 (SQLite)                          │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ videos 表    │  │ videos_fts  │                       │
│  │ (主数据)     │  │ (全文索引)   │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块职责

### backend/main.py

FastAPI 应用入口，负责：
- CORS 配置（允许前端跨域访问）
- API 路由注册
- 生命周期管理（启动时初始化数据库）
- 静态文件服务（用于前端构建产物部署）

**核心路由组**：
- `/api/videos` — CRUD + 搜索 + 收藏
- `/api/videos/{id}/analyze` — AI 分析触发/查询
- `/api/categories` — 分类统计
- `/api/env-check` — 环境状态检查
- `/api/proxy-image` — 封面图代理（解决跨域）

### backend/database.py

SQLite 数据访问层，负责：
- 数据库连接管理（`sqlite3` + `fts5` 扩展）
- 表结构定义和迁移（`init_db()`）
- CRUD 操作（增删改查）
- FTS5 全文搜索（自动同步触发器）
- AI 分析结果字段的 JSON 序列化/反序列化

**核心表结构**：
```sql
videos (id, url, title, author, description, tags, cover_url, 
        category, created_at, analyze_status, ai_summary, 
        ai_keypoints, ai_tags, transcribe_text, analyzed_at)

videos_fts (FTS5 虚拟表，自动同步 videos 的 title/description/tags/author)
```

### backend/parser.py

抖音链接解析器，负责：
- 从分享文本中提取抖音 URL（短链 `v.douyin.com` 或长链）
- 短链重定向追踪获取真实 video_id
- 使用移动端 User-Agent 访问 `iesdouyin.com` 获取页面
- 解析页面内嵌 JSON 提取元数据：
  - `desc` → 标题/描述
  - `nickname` → 作者
  - `hashtag_name` → 标签数组
  - `cover` → 封面图 URL
  - `play_addr` → 视频地址

**关键设计**：必须使用移动端 UA，PC 端页面纯 JS 渲染无法直接抓取。

### backend/analyzer.py

AI 分析引擎，双模式架构：

#### Basic 模式（默认）

基于本地规则引擎，无需任何 API 密钥：
1. **技术词典匹配**：内置 60+ 技术工具/框架关键词，识别视频涉及的技术栈
2. **内容类型判断**：根据关键词匹配 8 种内容类型（教程/工具推荐/概念讲解等）
3. **受众识别**：根据语言风格判断 9 类目标受众（初学者/开发者/设计师等）
4. **价值推断**：判断视频的实用价值（入门/进阶/案例/趋势）
5. **结构化摘要**：组合上述分析生成格式化的核心要点

#### Full 模式（可选）

需要配置百度语音识别 + 千帆大模型 API：
1. 下载视频文件到本地临时目录
2. FFmpeg 提取音频为 WAV 格式
3. 百度语音识别 API 转写为文本（或 Whisper 本地转写）
4. 千帆大模型（ERNIE 等）基于转写文本生成深度摘要
5. 返回结构化结果：摘要、核心要点、关键词标签

**环境检查**：`env-check` API 返回当前可用的分析模式（`basic`/`full`）。

### backend/category.py

自动分类器，基于规则匹配：
- 定义多个分类的关键词映射表
- 遍历视频的 tags 和 description
- 统计每个分类的关键词命中次数
- 返回命中次数最多的分类（默认 "其他"）

**支持分类**：科技、教育、美食、旅行、娱乐、职场、生活、其他

---

## 数据流

### 1. 收藏视频流程

```
用户粘贴分享文本
    │
    ▼
POST /api/videos {share_text}
    │
    ▼
main.py: 提取 URL（短链/长链）
    │
    ▼
parser.py: 解析抖音页面 → 提取元数据
    │
    ▼
category.py: 自动分类
    │
    ▼
database.py: 保存到 SQLite + 同步 FTS5 索引
    │
    ▼
返回视频对象（含解析结果）
    │
    ▼
前端展示新卡片
```

### 2. AI 分析流程

```
用户点击「AI 分析」
    │
    ▼
POST /api/videos/{id}/analyze
    │
    ▼
database.py: 获取视频元数据
    │
    ▼
analyzer.py: 
  ├─ 检查环境（API密钥/FFmpeg/Whisper）
  ├─ 选择模式（basic / full）
  │   ├─ basic: 本地规则分析 → 生成摘要
  │   └─ full: 下载视频 → 提取音频 → 语音转写 → 大模型分析
  │
  └─ 更新数据库：ai_summary, ai_keypoints, ai_tags
    │
    ▼
GET /api/videos/{id}/analyze（轮询状态）
    │
    ▼
前端展示分析结果
```

### 3. 搜索流程

```
用户输入搜索词
    │
    ▼
GET /api/videos?q=关键词&category=分类
    │
    ▼
database.py: 
  ├─ 非空查询：FTS5 全文检索 videos_fts
  └─ 空查询：返回全部，支持 category 筛选
    │
    ▼
返回分页结果列表
    │
    ▼
前端渲染卡片网格
```

---

## 数据库设计

### videos 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增 ID |
| url | TEXT | 视频原链接 |
| title | TEXT | 视频标题 |
| author | TEXT | 作者昵称 |
| description | TEXT | 描述文本 |
| tags | TEXT (JSON) | 标签数组（JSON 字符串） |
| cover_url | TEXT | 封面图 URL |
| category | TEXT | 分类名称 |
| created_at | TEXT | 收藏时间（ISO 格式） |
| analyze_status | TEXT | 分析状态：pending/analyzing/done |
| ai_summary | TEXT | AI 生成的摘要 |
| ai_keypoints | TEXT (JSON) | 核心要点数组 |
| ai_tags | TEXT (JSON) | AI 标签数组 |
| transcribe_text | TEXT | 语音转写文本（full 模式） |
| analyzed_at | TEXT | 分析完成时间 |

### videos_fts 虚拟表

```sql
CREATE VIRTUAL TABLE videos_fts USING fts5(
    title, description, tags, author,
    content=videos, content_rowid=id
);

-- 自动同步触发器
INSERT/UPDATE/DELETE on videos → 自动同步 videos_fts
```

**搜索语法**：支持 `AND`/`OR`/`NOT` 和短语搜索（例如：`"Python" AND "教程"`）。

---

## API 详细说明

### POST /api/videos

收藏视频。

**请求体**：
```json
{
  "share_text": "7.12 复制打开抖音，看看【xxx】的作品 https://v.douyin.com/xxxxx/"
}
```

**响应**：
```json
{
  "id": 1,
  "url": "https://www.douyin.com/video/xxxx",
  "title": "视频标题",
  "author": "作者名",
  "description": "描述文本",
  "tags": ["标签1", "标签2"],
  "cover_url": "https://...",
  "category": "科技",
  "created_at": "2026-08-01 10:30:00",
  "analyze_status": "pending"
}
```

### GET /api/videos

视频列表（支持搜索和筛选）。

**Query 参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码（默认 1） |
| size | int | 否 | 每页数量（默认 20） |
| q | str | 否 | 搜索关键词 |
| category | str | 否 | 分类筛选 |

**响应**：
```json
{
  "total": 100,
  "items": [{...}, {...}]
}
```

### POST /api/videos/{id}/analyze

触发 AI 分析（异步执行，立即返回状态）。

**响应**：
```json
{
  "status": "analyzing",
  "mode": "basic",
  "mode_label": "基础分析（基于元数据）"
}
```

### GET /api/videos/{id}/analyze

查询分析结果。

**响应（完成状态）**：
```json
{
  "status": "done",
  "mode": "basic",
  "result": {
    "summary": "本视频介绍了...",
    "keypoints": ["要点1", "要点2"],
    "tags": ["AI", "编程"]
  }
}
```

### GET /api/env-check

环境检查，返回当前可用的分析能力。

**响应**：
```json
{
  "ffmpeg": true,
  "whisper": false,
  "baidu_asr": false,
  "qianfan": false,
  "mode": "basic",
  "mode_label": "基础分析（基于元数据）",
  "can_analyze": true
}
```

---

## AI 分析模块设计

### 本地规则引擎（Basic 模式）

核心逻辑位于 `analyzer.py` 的 `_generate_local_summary()` 方法。

#### 1. 技术词典

内置 60+ 技术关键词，按类别组织：
```python
TECH_TOOLS = {
    "ai": ["人工智能", "AI", "机器学习", "深度学习", "神经网络", ...],
    "web": ["前端", "后端", "全栈", "React", "Vue", "JavaScript", ...],
    "data": ["数据分析", "Python", "SQL", "大数据", ...],
    ...
}
```

#### 2. 内容类型判断

```python
CONTENT_TYPES = {
    "教程": ["教程", "教学", "入门", "基础", "从零开始", ...],
    "工具推荐": ["推荐", "工具", "软件", "App", ...],
    "概念讲解": ["是什么", "介绍", "科普", "原理", ...],
    ...
}
```

#### 3. 受众识别

```python
AUDIENCE_MAP = {
    "初学者": ["入门", "零基础", "新手", "小白", ...],
    "开发者": ["程序员", "工程师", "代码", "编程", ...],
    "设计师": ["设计", "UI", "UX", "Figma", ...],
    ...
}
```

#### 4. 分析流程

```
输入：视频元数据（title, description, tags）
  │
  ├─ 技术工具识别 → 命中关键词列表
  ├─ 内容类型判断 → 最高匹配类型
  ├─ 目标受众识别 → 受众群体
  ├─ 价值推断 → 实用价值描述
  │
  └─ 组合生成结构化输出：
      ├─ 一句话摘要
      ├─ 核心要点列表（3-5条）
      └─ AI 标签列表
```

### 外部 API 集成（Full 模式）

#### 百度语音识别（可选）

```python
from baidu_aip import AipSpeech

client = AipSpeech(app_id, api_key, secret_key)
result = client.asr(audio_data, 'wav', 16000, {'dev_pid': 1537})
```

#### Whisper（可选，本地）

```python
import whisper
model = whisper.load_model("base")
result = model.transcribe(audio_path)
```

#### 千帆大模型（可选）

```python
import qianfan
chat = qianfan.ChatCompletion()
response = chat.do(model="ERNIE-Speed", messages=[...])
```

---

## 前端架构

### 页面组织

`App.vue` 采用单页面应用（SPA）设计，通过 `activePage` 状态切换页面：

| 页面 | 变量值 | 说明 |
|------|--------|------|
| 数据概览 | `dashboard` | 统计卡片 + 分析流程 + 分类分布 + 最近收藏 |
| 视频库 | `library` | 搜索栏 + 卡片网格 + 分页 |

### 组件结构

```
App.vue
├── 侧边栏 (sidebar)
│   ├── Logo
│   ├── 页面导航（数据概览 / 视频库）
│   ├── 分类导航（全部分类 / 各分类）
│   └── 收藏按钮（固定在底部）
│
├── 主内容区 (main-content)
│   ├── 页面头部 (page-header)
│   │   ├── 标题 + 副标题
│   │   └── 搜索框（视频库页）
│   │
│   ├── 仪表盘页 (dashboard)
│   │   ├── 统计卡片行（已收藏 / 已分析 / 待分析 / 分类数）
│   │   ├── 分析流程（收藏 → AI分析 → 智能检索）
│   │   ├── 分类分布（柱状图）
│   │   └── 最近收藏列表
│   │
│   ├── 视频库页 (library)
│   │   ├── 搜索栏 + 收藏按钮
│   │   ├── 空状态 / 加载状态
│   │   ├── 视频卡片网格 (video-grid)
│   │   │   └── 视频卡片 (video-card)
│   │   │       ├── 封面图 (card-cover)
│   │   │       │   └── 状态角标（已分析/分析中/待分析）
│   │   │       └── 信息区 (card-info)
│   │   │           ├── 标题
│   │   │           ├── 作者 + 日期
│   │   │           ├── 标签
│   │   │           ├── AI 摘要
│   │   │           └── 底部分类标签
│   │   └── 分页栏
│   │
│   └── 弹窗层
│       ├── 收藏弹窗 (collect-dialog)
│       │   └── 分享文本输入框 + 收藏按钮
│       └── 详情弹窗 (detail-dialog)
│           ├── 封面图
│           ├── 标题 + 作者 + 日期
│           ├── 标签
│           ├── 操作按钮（AI分析 / 打开原视频 / 删除）
│           ├── 分类编辑（下拉选择 + 保存）
│           └── AI 分析结果区域
│               ├── 摘要文本
│               ├── 核心要点列表
│               ├── AI 标签
│               └── 转写文本（full 模式）
```

### 状态管理

使用 Vue 3 Composition API 的 `ref`/`reactive` 进行状态管理：

```javascript
// 核心状态
const activePage = ref('dashboard')      // 当前页面
const selectedCategory = ref('')          // 当前选中的分类
const searchQuery = ref('')               // 搜索关键词
const videos = ref([])                  // 视频列表
const detailVideo = ref(null)           // 当前详情视频
const showCollectDialog = ref(false)    // 收藏弹窗显示状态
const detailVisible = ref(false)         // 详情弹窗显示状态
```

### API 客户端

`api.js` 封装了所有后端 API 调用：

```javascript
export const api = {
  collectVideo: (shareText) => axios.post('/api/videos', { share_text: shareText }),
  getVideos: (params) => axios.get('/api/videos', { params }),
  getVideo: (id) => axios.get(`/api/videos/${id}`),
  deleteVideo: (id) => axios.delete(`/api/videos/${id}`),
  updateCategory: (id, category) => axios.patch(`/api/videos/${id}`, { category }),
  analyzeVideo: (id) => axios.post(`/api/videos/${id}/analyze`),
  getAnalyzeResult: (id) => axios.get(`/api/videos/${id}/analyze`),
  getCategories: () => axios.get('/api/categories'),
  getEnvCheck: () => axios.get('/api/env-check'),
}
```

---

## 扩展开发指南

### 1. 添加新的分类

编辑 `backend/category.py`：

```python
CATEGORY_KEYWORDS = {
    "新分类": ["关键词1", "关键词2", "关键词3"],
    # ... 现有分类
}
```

前端无需修改，分类会自动从后端获取并渲染。

### 2. 扩展本地规则引擎

编辑 `backend/analyzer.py`，在 `TECH_TOOLS` / `CONTENT_TYPES` / `AUDIENCE_MAP` 中添加新关键词：

```python
TECH_TOOLS = {
    "新领域": ["新技术1", "新技术2", ...],
    # ...
}
```

### 3. 接入新的语音识别服务

在 `analyzer.py` 中实现新的 `_transcribe_with_xxx()` 方法：

```python
def _transcribe_with_new_service(self, audio_path: str) -> str:
    # 调用新API
    result = new_api_client.transcribe(audio_path)
    return result["text"]
```

然后在 `analyze()` 方法中添加调用逻辑。

### 4. 更换大模型

在 `_generate_with_llm()` 中替换 `qianfan` 调用：

```python
def _generate_with_llm(self, text: str) -> dict:
    # 使用其他大模型API（OpenAI、Claude、本地模型等）
    response = other_llm_client.chat.completions.create(...)
    return self._parse_llm_response(response)
```

### 5. 前端主题定制

Element Plus 主题变量位于 `frontend/src/App.vue` 的 `<style>` 段，主要颜色：

```css
:root {
  --el-color-primary: #fe2c55;        /* 抖音红 */
  --el-color-success: #52c41a;        /* 成功绿 */
  --el-color-warning: #faad14;        /* 警告黄 */
  --el-color-danger: #f5222d;         /* 危险红 */
}
```

---

## 常见问题

### Q1: 收藏失败，提示 "无法解析链接"

**原因**：抖音页面结构变化，或分享文本格式不匹配。

**解决**：
1. 检查分享文本是否包含有效的抖音 URL（`v.douyin.com` 或 `douyin.com/video/`）
2. 检查 `parser.py` 中的正则表达式是否需要更新
3. 查看后端日志确认具体错误位置

### Q2: AI 分析结果不准确

**原因**：basic 模式基于关键词匹配，无法真正理解视频内容。

**解决**：
1. 配置百度语音识别 + 千帆大模型 API 启用 full 模式
2. 在 `analyzer.py` 中扩展 `TECH_TOOLS` 和 `CONTENT_TYPES` 词典
3. 手动修正分类和标签

### Q3: 封面图无法显示

**原因**：抖音图片域名跨域限制，或图片链接已失效。

**解决**：
1. 系统已内置 `/api/proxy-image` 代理接口
2. 前端自动使用代理 URL 加载图片
3. 如果仍不显示，可能是视频已被删除或设为私密

### Q4: 如何备份数据？

数据库文件位于 `backend/data/videos.db`，直接复制即可备份。

```bash
cp backend/data/videos.db backup/videos_$(date +%Y%m%d).db
```

### Q5: 如何部署到服务器？

1. 前端构建：`cd frontend && npm run build`
2. 将 `frontend/dist/` 放到后端静态文件目录或单独部署
3. 后端使用生产级 ASGI 服务器：
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
4. 使用 Nginx 反向代理，配置 HTTPS

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-08-01 | 初始版本：收藏、分类、搜索、基础 AI 分析 |

---

## 贡献指南

欢迎提交 Issue 和 PR：

1. Fork 本仓库
2. 创建 feature 分支：`git checkout -b feature/xxx`
3. 提交变更：`git commit -m "feat: xxx"`
4. 推送分支：`git push origin feature/xxx`
5. 提交 Pull Request

---

*文档最后更新：2026-08-01*