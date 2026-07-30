"""
InkAI 小说创作系统配置文件

配置优先级：环境变量 > 默认值（dashscope preset）
开源用户请设置环境变量：
  INKAI_API_KEY (必需)
  INKAI_PROVIDER (可选，dashscope/deepseek/openai，默认 dashscope)
  INKAI_EMBEDDING_API_KEY (LLM 非 dashscope 时必需)
"""
import os
from typing import Any, Dict, List
from urllib.parse import urlparse


# Provider 预设（支持多 LLM 提供商，embedding/rerank 独立配置）
PROVIDER_PRESETS: Dict[str, Dict[str, str]] = {
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.6-plus",
        "embedding_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "embedding_model": "text-embedding-v3",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        # DeepSeek 不提供 embedding，回退到 dashscope
        "embedding_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "embedding_model": "text-embedding-v3",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "embedding_base_url": "https://api.openai.com/v1",
        "embedding_model": "text-embedding-3-small",
    },
}


def _load_provider() -> str:
    """加载 provider：环境变量 > 默认 dashscope。"""
    provider = os.environ.get("INKAI_PROVIDER", "").strip().lower()
    if provider not in PROVIDER_PRESETS:
        provider = "dashscope"
    return provider


PROVIDER = _load_provider()
_preset = PROVIDER_PRESETS[PROVIDER]

# API配置 - 支持 multi-provider
API_KEY = os.environ.get("INKAI_API_KEY", "")
BASE_URL = os.environ.get("INKAI_BASE_URL", "") or _preset["base_url"]

# 模型配置
MODEL_NAME = os.environ.get("INKAI_MODEL", "") or _preset["model"]
BACKUP_MODEL = "qwen-max"
TEMPERATURE = 0.7

# Token配置
MAX_TOKENS = 32768
CHAPTER_MAX_TOKENS = 32768

# 上下文窗口配置
MAX_CONTEXT_TOKENS = 900000

# 长上下文模式配置
USE_LONG_CONTEXT_MODE = True
LONG_CONTEXT_RECENT_CHAPTERS = 20

# 嵌入模型配置 - 独立 key，不强制与主 LLM 同 provider（修复 Issue #2: DeepSeek 配置后 embedding 失败）
EMBEDDING_API_KEY = os.environ.get("INKAI_EMBEDDING_API_KEY", "") or API_KEY
EMBEDDING_BASE_URL = (
    os.environ.get("INKAI_EMBEDDING_BASE_URL", "") or _preset["embedding_base_url"]
)
EMBEDDING_MODEL = (
    os.environ.get("INKAI_EMBEDDING_MODEL", "") or _preset.get("embedding_model", "text-embedding-v3")
)

# 重排序模型配置 - 复用 embedding key
RERANK_API_KEY = os.environ.get("INKAI_RERANK_API_KEY", "") or EMBEDDING_API_KEY
RERANK_BASE_URL = os.environ.get("INKAI_RERANK_BASE_URL", "") or EMBEDDING_BASE_URL
RERANK_MODEL = "gte-rerank"


def _compute_embedding_status() -> Dict[str, str]:
    """诊断 embedding 配置：embedding 与 LLM 跨 host 且复用 key 时警告。"""
    if not EMBEDDING_API_KEY:
        return {"status": "error", "message": "未配置 embedding API key，知识图谱/语义检索不可用"}
    llm_host = urlparse(BASE_URL).netloc
    emb_host = urlparse(EMBEDDING_BASE_URL).netloc
    if llm_host != emb_host and EMBEDDING_API_KEY == API_KEY:
        return {
            "status": "warning",
            "message": (
                f"LLM provider={PROVIDER}（{llm_host}），embedding 回退到 {emb_host}，"
                f"但复用了 LLM key。{llm_host} 的 key 不能用于 {emb_host}，"
                f"请配 INKAI_EMBEDDING_API_KEY（{emb_host} 的 key）。"
            ),
        }
    return {"status": "ok", "message": ""}


EMBEDDING_STATUS = _compute_embedding_status()

# Milvus向量数据库配置
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION_NAME = "inkai_vectors"

# 标签配置
TAG_CATEGORIES = {
    "类型标签": ["玄幻", "都市", "悬疑", "科幻", "言情", "历史", "军事", "武侠", "仙侠", "奇幻", "耽美", "百合", "轻小说", "同人", "游戏", "无限流", "系统", "修真", "灵异", "推理", "侦探", "西幻", "末世", "重生", "穿越", "历史架空", "军事战争", "科幻机甲", "赛博朋克", "克苏鲁"],
    "主题标签": ["复仇", "成长", "权谋", "治愈", "冒险", "爱情", "友情", "家庭", "职场", "校园", "救赎", "逆袭", "商战", "社会问题", "心理", "惊悚", "恐怖", "末日生存", "异能", "超能力", "时间旅行", "平行宇宙", "人工智能", "环保", "社会批判", "政治斗争", "经济斗争", "伦理", "探索", "寻宝", "谍战", "间谍", "悬疑解谜", "家庭伦理", "青春成长", "校园恋爱", "友情羁绊", "亲情", "爱情纠葛"],
    "风格标签": ["幽默诙谐", "严肃深刻", "文艺抒情", "热血激昂", "温馨治愈", "黑暗压抑", "轻松愉快", "悬疑紧张", "浪漫唯美", "冷峻写实", "奇幻瑰丽", "细腻描写", "快节奏", "慢节奏", "史诗感", "日常系", "沙雕", "虐心", "治愈系", "黑暗系", "现实主义", "超现实", "后现代", "哥特", "蒸汽朋克", "赛博朋克", "史诗", "轻松", "沉重", "光明", "冷酷", "讽刺", "荒诞", "诗意", "口语化", "叙事性强"],
    "受众标签": [ "青少年", "成年人", "女性向", "男性向", "全年龄", "儿童向", "少女向", "少男向", "中年向", "老年向", "学生", "上班族", "家庭主妇", "退休人员", "LGBTQ+群体", "二次元爱好者", "科幻迷", "历史爱好者", "游戏爱好者", "动漫爱好者", "家庭向", "情侣向", "亲子向", "特定兴趣群体"]
}

# 人物原型库
CHARACTER_ARCHETYPES = {
    "侦探": {
        "traits": ["观察力强", "逻辑思维", "独来独往", "正义感强"],
        "background": "通常有执法或调查背景",
        "motivation": "追求真相和正义"
    },
    "学生": {
        "traits": ["好奇心强", "学习能力", "年轻活力", "理想主义"],
        "background": "校园生活，青春年华",
        "motivation": "成长和探索世界"
    },
    "医生": {
        "traits": ["专业严谨", "救死扶伤", "冷静理性", "责任感强"],
        "background": "医学专业背景",
        "motivation": "拯救生命，医学研究"
    }
}

# 故事结构配置
STORY_STRUCTURE = {
    "三幕剧": {
        "第一幕": {
            "setup": "介绍世界观、主角目标、初始冲突",
            "length_ratio": 0.25
        },
        "第二幕": {
            "confrontation": "中期危机、低谷期、转折点",
            "length_ratio": 0.5
        },
        "第三幕": {
            "resolution": "高潮对决、结局",
            "length_ratio": 0.25
        }
    }
}

# 质量评估标准
QUALITY_THRESHOLD = 80
QUALITY_DIMENSIONS = {
    "情节连贯性": {"weight": 0.3, "description": "无前后矛盾，伏笔100%呼应"},
    "人物立体度": {"weight": 0.25, "description": "角色情绪变化自然，动机合理"},
    "语言风格": {"weight": 0.25, "description": "符合标签的紧张感"},
    "创新吸引力": {"weight": 0.2, "description": "读者停留率>60%，点赞率>30%"}
}

# 文件路径配置
DATA_DIR = "data"
NOVELS_DIR = os.path.join(DATA_DIR, "novels")
KNOWLEDGE_GRAPHS_DIR = os.path.join(DATA_DIR, "knowledge_graphs")
GENRES_DIR = os.path.join(DATA_DIR, "genres")
TEMPLATES_DIR = "templates"

# 确保目录存在
for directory in [DATA_DIR, NOVELS_DIR, KNOWLEDGE_GRAPHS_DIR, GENRES_DIR, TEMPLATES_DIR]:
    os.makedirs(directory, exist_ok=True)
