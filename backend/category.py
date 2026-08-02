"""分类工具：基于标签和描述关键词进行自动分类

分类层级：
  一级分类（8个）→ 二级子分类（2-5个/类）
  匹配逻辑：先匹配子分类关键词，再回退到一级分类
"""
import re

# 分类关键词映射表（一级分类 → 子分类 → 关键词）
CATEGORY_TREE = {
    "编程开发": {
        "_keywords": ["编程", "代码", "程序员", "开发", "软件工程"],
        "前端开发": ["前端", "web", "html", "css", "js", "javascript", "react", "vue", "angular",
                   "ts", "typescript", "tailwind", "gsap", "dom", "浏览器", "网页", "nextjs", "nuxt", "vite"],
        "后端开发": ["后端", "server", "api", "数据库", "mysql", "redis", "docker", "k8s",
                   "kubernetes", "微服务", "架构", "nodejs", "node", "postgres", "mongodb", "go", "rust", "python"],
        "AI/算法": ["人工智能", "大模型", "机器学习", "深度学习", "算法", "神经网络",
                   "nlp", "cv", "模型训练", "微调", "llm", "chatgpt", "claude", "deepseek", "千帆", "文心一言"],
        "移动开发": ["ios", "android", "flutter", "react native", "小程序", "app开发", "移动端"],
        "DevOps": ["devops", "ci/cd", "部署", "运维", "linux", "自动化", "jenkins", "git", "github"],
    },
    "AI与数据": {
        "_keywords": ["ai", "人工智能", "数据", "机器学习"],
        "AI工具应用": ["ai工具", "ai应用", "chatgpt", "claude", "deepseek", "copilot", "cursor", "codex",
                     "ai编程", "ai写作", "ai绘画", "midjourney", "dalle", "sora", "ai视频"],
        "AI内容创作": [
                     # AI 生成内容（短剧/动漫/漫画/动画/影视）
                     "ai漫剧", "ai短剧", "ai动漫", "ai漫画", "ai动画", "ai影视",
                     "ai生成", "ai创作", "ai作品", "ai故事", "ai绘画作品", "ai艺术",
                     "aigc", "ai cg", "ai视频", "ai大片",
                     # AI 创作工具
                     "stablediffusion", "可灵", "即梦", "pixverse", "runway", "kling",
                     "sora", "midjourney", "dalle",
                     # 数字人/虚拟人
                     "数字人", "虚拟人", "ai主播", "ai数字人",
                     # 内容型标签（AI创作相关的抖音话题）
                     "ai创作大赛", "开放赛道", "拾光故事", "归墟", "零号档案",
                     ],
        "数据分析": ["数据分析", "数据科学", "pandas", "excel", "sql", "python", "可视化",
                   "bi", "tableau", "数据挖掘", "大数据", "统计"],
        "AI资讯": ["ai资讯", "大模型", "agi", "openai", "谷歌", "微软", "llm", "gpt", "人工智能趋势"],
    },
    "设计创意": {
        "_keywords": ["设计", "创意", "视觉", "艺术"],
        "UI/UX设计": ["ui", "ux", "界面设计", "交互设计", "用户体验", "figma", "sketch",
                    "设计系统", "原型", "wireframe", "用户研究", "可用性"],
        "平面/品牌": ["平面设计", "品牌设计", "logo", "海报", "排版", "字体", "色彩",
                    "photoshop", "illustrator", "indesign", "canva"],
        "三维/动效": ["3d", "blender", "c4d", "ae", "动效", "动画", "建模", "渲染",
                    "motion", "after effects", "unity", "unreal"],
        "视频剪辑": ["剪辑", "视频制作", "pr", "premiere", "达芬奇", "final cut",
                   "剪辑教程", "调色", "转场", "卡点"],
    },
    "科技数码": {
        "_keywords": ["科技", "数码", "手机", "电脑", "硬件"],
        "手机/平板": ["手机", "iphone", "华为", "小米", "oppo", "vivo", "三星", "折叠屏",
                    "手机评测", "平板", "ipad", "旗舰机"],
        "电脑/硬件": ["电脑", "笔记本", "macbook", "thinkpad", "台式机", "显卡", "cpu",
                    "装机", "diy", "显示器", "键盘", "鼠标"],
        "数码产品": ["耳机", "音箱", "相机", "无人机", "手表", "智能家居", "数码",
                   "评测", "开箱", "体验"],
        "软件/App": ["软件", "app", "应用推荐", "效率工具", "插件", "扩展", "浏览器", "工具软件"],
    },
    "职场商业": {
        "_keywords": ["职场", "商业", "管理", "创业", "工作"],
        "求职面试": ["面试", "简历", "求职", "校招", "秋招", "春招", "实习", "跳槽",
                   "offer", "薪资", "谈薪", "内推"],
        "职场技能": ["职场", "沟通", "汇报", "ppt", "excel技巧", "时间管理", "效率",
                   "项目管理", "向上管理", "晋升", "同事"],
        "商业/创业": ["创业", "商业", "商业模式", "融资", "股权", "管理", "团队",
                    "老板", "生意", "项目", "搞钱", "副业", "赚钱"],
        "产品/运营": ["产品经理", "运营", "增长", "营销", "推广", "流量", "转化",
                    "获客", "私域", "社群", "内容运营", "数据分析"],
    },
    "学习成长": {
        "_keywords": ["学习", "教育", "知识", "技能", "成长"],
        "编程学习": ["学编程", "编程入门", "零基础学", "代码教程", "python教程", "java教程",
                   "前端教程", "后端教程", "自学编程"],
        "语言学习": ["英语", "日语", "韩语", "学外语", "背单词", "口语", "雅思", "托福", "留学"],
        "考试考证": ["考研", "高考", "考公", "考编", "教资", "法考", "cpa", "考证", "自考", "专升本"],
        "通识/科普": ["科普", "冷知识", "历史", "哲学", "心理学", "经济学", "法律", "人文",
                    "纪录片", "ted", "演讲"],
    },
    "生活兴趣": {
        "_keywords": ["生活", "日常", "兴趣", "爱好"],
        "美食烹饪": ["美食", "烹饪", "做菜", "食谱", "美食教程", "探店", "吃播", "烘焙",
                   "早餐", "午餐", "晚餐", "宵夜", "小吃", "甜点", "咖啡", "料理"],
        "旅行摄影": ["旅游", "旅行", "攻略", "打卡", "景点", "自驾", "户外", "民宿",
                   "酒店", "游记", "风景", "拍照", "摄影", "航拍", "vlog"],
        "健身运动": ["健身", "运动", "减肥", "减脂", "增肌", "瑜伽", "跑步", "马甲线",
                   "腹肌", "有氧", "无氧", "拉伸", "健身教程", "健康", "养生"],
        "家居/穿搭": ["家居", "收纳", "整理", "装修", "租房", "家具", "穿搭", "时尚",
                    "美妆", "护肤", "发型"],
        "宠物/植物": ["宠物", "猫", "狗", "养宠", "萌宠", "猫咪", "狗狗", "多肉", "绿植", "养花"],
    },
    "娱乐综艺": {
        "_keywords": ["娱乐", "搞笑", "综艺", "影视", "音乐"],
        "综艺/搞笑": ["综艺", "搞笑", "段子", "脱口秀", "喜剧", "相声", "整蛊", "沙雕", "名场面"],
        "影视剧": ["电影", "电视剧", "追剧", "网剧", "美剧", "日剧", "韩剧", "解说",
                 "影视解说", "影评", "经典片段", "短剧", "漫剧"],
        "音乐/舞蹈": ["音乐", "唱歌", "翻唱", "live", "演唱会", "乐器", "吉他", "钢琴",
                    "舞蹈", "街舞", "编舞", "kpop"],
        "游戏电竞": ["游戏", "英雄联盟", "王者荣耀", "原神", "吃鸡", "主机游戏", "steam",
                   "电竞", "直播", "游戏实况"],
    },
}

# 扁平化所有分类及关键词，保留分类路径
def _flatten_categories():
    """将所有子分类展平为 {分类路径: 关键词列表}"""
    flat = {}
    for parent, children in CATEGORY_TREE.items():
        parent_kws = children.pop("_keywords", [])
        # 子分类
        for child_name, keywords in children.items():
            flat[child_name] = keywords
        # 父分类兜底关键词
        flat[parent] = parent_kws
    return flat

CATEGORY_KEYWORDS = _flatten_categories()


def auto_category(tags, description="", title=""):
    """根据标签和描述自动判断分类（含子分类）

    Args:
        tags: 标签列表或逗号分隔字符串
        description: 视频描述
        title: 视频标题

    Returns:
        分类名称字符串，未匹配返回空字符串
    """
    # 统一标签为列表
    if isinstance(tags, str):
        try:
            import json
            tags = json.loads(tags)
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    elif not isinstance(tags, list):
        tags = []

    # 合并所有文本用于匹配
    all_text = " ".join(tags) + " " + description + " " + title
    all_lower = all_text.lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            kw_len = len(kw_lower)
            # 短关键词（≤2字符）降权，避免 "ai" "go" "ts" 等过度匹配
            weight = 1 if kw_len <= 2 else (3 if kw_len >= 4 else 2)

            count = all_lower.count(kw_lower)
            if count > 0:
                score += count * weight
            # 标签命中权重更高（精确子串匹配）
            for tag in tags:
                if kw_lower in tag.lower():
                    score += 5 * weight
        if score > 0:
            scores[category] = score

    if not scores:
        return "其他"

    # 取分数最高的
    return max(scores, key=scores.get)
