#!/usr/bin/env python3
"""
AI工具导航 — 自动采集生成器
从 Arxiv + HackerNews 采集最新 AI 资讯，生成 index.html
"""

import json
import os
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
TEMPLATE_PATH = BASE_DIR / "template.html"
OUTPUT_PATH = BASE_DIR / "index.html"

# ── 工具数据（稳定内置） ──────────────────────────────────────────
TOOLS = [
    # Chat
    {"n": "ChatGPT", "c": "chat", "i": "💬", "d": "OpenAI 旗舰对话式 AI"},
    {"n": "Claude", "c": "chat", "i": "🤖", "d": "Anthropic 安全可信 AI"},
    {"n": "DeepSeek", "c": "chat", "i": "🧠", "d": "深度求索推理模型"},
    {"n": "Gemini", "c": "chat", "i": "✨", "d": "Google 多模态大模型"},
    {"n": "Grok", "c": "chat", "i": "🚀", "d": "xAI 实时知识助手"},
    {"n": "Kimi", "c": "chat", "i": "📘", "d": "月之暗面长文本助手"},
    {"n": "通义千问", "c": "chat", "i": "🌊", "d": "阿里云超大模型"},
    {"n": "文心一言", "c": "chat", "i": "📖", "d": "百度知识增强大模型"},
    {"n": "豆包", "c": "chat", "i": "🟢", "d": "字节跳动 AI 助手"},
    # Image
    {"n": "Midjourney", "c": "image", "i": "🎨", "d": "顶级 AI 艺术创作"},
    {"n": "DALL·E 3", "c": "image", "i": "🖼️", "d": "OpenAI 文生图模型"},
    {"n": "Stable Diffusion", "c": "image", "i": "🌈", "d": "开源图像生成"},
    {"n": "ComfyUI", "c": "image", "i": "⚡", "d": "节点式 AI 工作流"},
    {"n": "Flux", "c": "image", "i": "🔥", "d": "Black Forest Lab 新锐"},
    {"n": "Canva AI", "c": "image", "i": "✏️", "d": "在线设计 + AI 生成"},
    {"n": "Recraft", "c": "image", "i": "🎯", "d": "矢量 & 品牌设计 AI"},
    # Code
    {"n": "GitHub Copilot", "c": "code", "i": "💻", "d": "AI 结对编程助手"},
    {"n": "Cursor", "c": "code", "i": "🖥️", "d": "AI-first IDE"},
    {"n": "Windsurf", "c": "code", "i": "🏄", "d": "代理式 AI 编程"},
    {"n": "Claude Code", "c": "code", "i": "🔧", "d": "终端内 AI 开发工具"},
    {"n": "Codeium", "c": "code", "i": "⚙️", "d": "免费 AI 代码补全"},
    {"n": "Replit Agent", "c": "code", "i": "🔄", "d": "浏览器端全栈 AI 开发"},
    # Video
    {"n": "Sora", "c": "video", "i": "🎬", "d": "OpenAI 视频生成"},
    {"n": "Runway Gen-3", "c": "video", "i": "🎥", "d": "专业 AI 视频工具"},
    {"n": "Pika", "c": "video", "i": "⭐", "d": "创意视频生成平台"},
    {"n": "Kling", "c": "video", "i": "🎞️", "d": "可灵 AI 视频生成"},
    {"n": "HeyGen", "c": "video", "i": "👤", "d": "AI 数字人视频"},
    # Audio
    {"n": "ElevenLabs", "c": "audio", "i": "🎙️", "d": "超逼真 AI 语音"},
    {"n": "Suno", "c": "audio", "i": "🎵", "d": "AI 音乐生成"},
    {"n": "Udio", "c": "audio", "i": "🎶", "d": "高质量 AI 作曲"},
    {"n": "Whisper", "c": "audio", "i": "🎧", "d": "OpenAI 语音识别"},
    # Productivity
    {"n": "Notion AI", "c": "productivity", "i": "📝", "d": "智能笔记 & 协作"},
    {"n": "Perplexity", "c": "productivity", "i": "🔍", "d": "AI 搜索引擎"},
    {"n": "Grammarly", "c": "productivity", "i": "✍️", "d": "AI 写作优化"},
    {"n": "Gamma", "c": "productivity", "i": "📊", "d": "AI 生成演示文稿"},
    {"n": "Otter.ai", "c": "productivity", "i": "🗣️", "d": "AI 会议转录"},
    {"n": "Beautiful.ai", "c": "productivity", "i": "📈", "d": "AI 智能幻灯片"},
    # Other
    {"n": "HuggingFace", "c": "other", "i": "🤗", "d": "开源模型社区"},
    {"n": "Replicate", "c": "other", "i": "🔬", "d": "云端模型运行平台"},
    {"n": "Poe", "c": "other", "i": "🗂️", "d": "多模型聚合平台"},
    {"n": "Leonardo AI", "c": "other", "i": "🦁", "d": "游戏素材 AI 生成"},
]

CAT_MAP = {
    "chat": ("对话助手", "💬"),
    "image": ("图像生成", "🎨"),
    "code": ("编程开发", "💻"),
    "video": ("视频创作", "🎬"),
    "audio": ("音频处理", "🎙️"),
    "productivity": ("效率工具", "📝"),
    "other": ("其他", "🔧"),
}

# ── RSS 深度新闻源（已验证可用 · 2026-07） ─────────────────────
# cat: ai_deep=AI深度, tech_biz=科技商业, life=效率生活, en=英文资讯
# 来源参考 GitHub: weekend-project-space/top-rss-list、SuYxh/ai-news-aggregator
RSS_FEEDS = [
    {"name": "机器之心", "url": "https://decemberpei.cyou/rssbox/wechat-jiqizhixin.xml", "cat": "ai_deep"},
    {"name": "量子位", "url": "https://decemberpei.cyou/rssbox/wechat-liangziwei.xml", "cat": "ai_deep"},
    {"name": "新智元", "url": "https://decemberpei.cyou/rssbox/wechat-xinzhiyuan.xml", "cat": "ai_deep"},
    {"name": "甲子光年", "url": "https://decemberpei.cyou/rssbox/wechat-jiaziguangnian.xml", "cat": "ai_deep"},
    {"name": "晚点LatePost", "url": "https://decemberpei.cyou/rssbox/wechat-wandian.xml", "cat": "tech_biz"},
    {"name": "36氪", "url": "https://decemberpei.cyou/rssbox/wechat-36ke.xml", "cat": "tech_biz"},
    {"name": "虎嗅", "url": "https://decemberpei.cyou/rssbox/wechat-huxiuapp.xml", "cat": "tech_biz"},
    {"name": "极客公园", "url": "https://decemberpei.cyou/rssbox/wechat-jikegongyuan.xml", "cat": "tech_biz"},
    {"name": "少数派", "url": "https://sspai.com/feed", "cat": "life"},
    {"name": "爱范儿", "url": "https://www.ifanr.com/feed", "cat": "life"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/full.xml", "cat": "en"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "cat": "en"},
]

RSS_CAT_LABEL = {
    "ai_deep": "AI深度",
    "tech_biz": "科技商业",
    "life": "效率生活",
    "en": "英文资讯",
}

# 优先用于小红书素材的类别（深度、可延展成长文）
XIAOHONGSHU_CATS = ("ai_deep", "tech_biz")


def strip_html(s):
    """去掉 HTML 标签并压缩空白。"""
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def esc_attr(s):
    """转义 HTML 属性中的特殊字符。"""
    return (s or "").replace("&", "&amp;").replace('"', "&quot;")


# ── 预设兜底评测（网络不通时使用） ─────────────────────────────
FALLBACK_REVIEWS = [
    ("Claude Sonnet vs GPT-4o：创意写作横评",
     "深度对比两款旗舰模型在创意写作、代码生成和推理能力上的表现，Sonnet 在长文本连贯性上略胜一筹。",
     ["模型对比", "Claude", "GPT-4o"]),
    ("Cursor vs Windsurf：AI IDE 巅峰对决",
     "两款 AI-first IDE 在上下文理解、代码补全精度、多文件重构能力上的全面测试。",
     ["IDE", "编程", "评测"]),
    ("Suno V4 实测：AI 音乐终于有了'灵魂'",
     "Suno 最新版本在旋律结构、歌词契合度和音质上取得突破，测试 10 种音乐风格。",
     ["音乐", "Suno", "生成"]),
    ("11 款 RAG 工具横向对比：谁是最强知识库",
     "从检索精度、延迟、部署成本三个维度测评主流 RAG 框架。",
     ["RAG", "知识库", "企业"]),
    ("AI 编程进化史：从 Copilot 到 Agent 时代",
     "回顾 2024-2025 AI 编程工具变迁，分析 Agent 模式的真正价值与局限。",
     ["编程", "趋势", "深度"]),
    ("Flux.1 Pro vs Midjourney V7：设计出图谁更强",
     "从构图、光影、文字渲染、品牌一致性四个维度进行盲测对比。",
     ["图像", "Flux", "Midjourney"]),
]

# 每周测评轮换数据
WEEKLY_DATASET = [
    {
        "title": "⚡ 效能跃升周",
        "scores": {"整体效率": 92, "工具适配": 88, "创意产出": 85, "满意度": 90},
        "detail": "本周重点测试了 Claude Code + Cursor 组合工作流。在代码审查场景中效率提升 40%，但在大型重构项目中仍需要人工介入。AI 编程工具的上下文管理能力是本周期最大亮点。",
    },
    {
        "title": "🚀 自动化探索周",
        "scores": {"整体效率": 89, "工具适配": 92, "创意产出": 82, "满意度": 87},
        "detail": "Deep Research 类工具在信息收集场景中表现亮眼，Perplexity + NotebookLM 组合将调研时间缩短 55%。建议团队建立标准化的 AI 工具评估框架。",
    },
    {
        "title": "🎨 创意爆发周",
        "scores": {"整体效率": 86, "工具适配": 84, "创意产出": 94, "满意度": 91},
        "detail": "Midjourney V7 + Recraft 的工作流在设计团队中反响极好。从草图到最终方案的时间压缩了 65%。AI 辅助创意不再是\"辅助\"而是\"核心生产力\"。",
    },
    {
        "title": "🔬 开源模型突破周",
        "scores": {"整体效率": 88, "工具适配": 90, "创意产出": 87, "满意度": 89},
        "detail": "DeepSeek V4 / Llama 4 / Qwen 3 等开源模型在本周密集发布，本地部署推理成本降至新低。小团队自建 AI 工作流的门槛正在快速消失。",
    },
    {
        "title": "🎥 多模态爆发周",
        "scores": {"整体效率": 85, "工具适配": 86, "创意产出": 91, "满意度": 88},
        "detail": "Sora 开放 API 后视频生成工作流大幅简化。本周重点测试了视频到视频翻译、自动剪辑和 AI 配音的端到端 pipeline，效率提升 3 倍。",
    },
]


# ── 数据采集 ──────────────────────────────────────────────────────

def fetch_url(url, timeout=15):
    """Fetch URL with timeout, return text or None."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "AI-Tools-Nav/1.0 (auto-collector)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        # 跟随重定向（308/301/302）
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            loc = e.headers["Location"]
            if loc.startswith("/"):
                from urllib.parse import urlparse
                base = urlparse(url)
                loc = f"{base.scheme}://{base.netloc}{loc}"
            print(f"  ↪️  重定向 {url[:50]} → {loc[:50]}")
            try:
                return fetch_url(loc, timeout=timeout)
            except Exception as ex:
                print(f"  ⚠️  重定向后请求失败: {ex}")
                return None
        print(f"  ⚠️  请求失败: {url[:80]}... -> {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  请求失败: {url[:80]}... -> {e}")
        return None


def fetch_arxiv_papers(max_results=8):
    """Fetch latest AI papers from Arxiv."""
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&"
        f"sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    text = fetch_url(url)
    if not text:
        return []

    papers = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(text)
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            summary = entry.find("atom:summary", ns)
            published = entry.find("atom:published", ns)
            authors = entry.findall("atom:author/atom:name", ns)
            papers.append({
                "title": title.text.strip().replace("\n", " ") if title is not None else "",
                "summary": summary.text.strip().replace("\n", " ") if summary is not None else "",
                "published": published.text[:10] if published is not None else "",
                "authors": [a.text for a in authors] if authors else [],
                "url": (entry.find("atom:id", ns).text.strip()
                        if entry.find("atom:id", ns) is not None else ""),
            })
    except ET.ParseError as e:
        print(f"  ⚠️  Arxiv XML 解析失败: {e}")

    return papers


def fetch_hn_stories(query="AI", hits=8):
    """Fetch AI-related stories from HackerNews via Algolia."""
    import urllib.parse
    url = (
        "https://hn.algolia.com/api/v1/search?"
        f"query={urllib.parse.quote(query)}&"
        f"tags=story&hitsPerPage={hits}"
    )
    text = fetch_url(url)
    if not text:
        return []

    try:
        data = json.loads(text)
        hits = data.get("hits", [])
        stories = []
        for h in hits:
            title = h.get("title", "")
            url = h.get("url", "") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"
            points = h.get("points", 0)
            author = h.get("author", "")
            stories.append({"title": title, "url": url, "points": points, "author": author})
        return stories
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️  HN JSON 解析失败: {e}")
        return []


def fetch_techcrunch_rss():
    """Fetch AI-related stories from TechCrunch."""
    url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    text = fetch_url(url)
    if not text:
        return []

    items = []
    try:
        root = ET.fromstring(text)
        ns = {"": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:6]:
            title = entry.find("{http://www.w3.org/2005/Atom}title")
            link = entry.find("{http://www.w3.org/2005/Atom}link")
            href = link.get("href", "") if link is not None else ""
            items.append({
                "title": title.text.strip() if title is not None else "",
                "url": href,
            })
    except ET.ParseError as e:
        print(f"  ⚠️  TechCrunch RSS 解析失败: {e}")
    return items


def fetch_rss_feeds(per_feed=2, timeout=12):
    """抓取全部 RSS 源，返回去重后的新闻条目列表。

    返回结构: [{"title", "url", "summary", "source", "cat", "published"}]
    """
    items = []
    for feed in RSS_FEEDS:
        text = fetch_url(feed["url"], timeout=timeout)
        if not text:
            continue
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            # 个别源可能含非法字符，尝试宽松解析
            try:
                root = ET.fromstring(text.encode("utf-8", "ignore").decode("utf-8", "ignore"))
            except ET.ParseError as e:
                print(f"  ⚠️  {feed['name']} RSS 解析失败: {e}")
                continue

        # 兼容 RSS 2.0 与 Atom
        entries = root.findall(".//item") or root.findall(
            ".//{http://www.w3.org/2005/Atom}entry"
        )
        if not entries:
            # 形如 <rss><channel><item> 已在 .//item 覆盖
            entries = root.findall("channel/item")

        count = 0
        for entry in entries:
            if count >= per_feed:
                break
            title = entry.findtext("title") or entry.findtext(
                "{http://www.w3.org/2005/Atom}title"
            )
            link = entry.findtext("link") or entry.findtext(
                "{http://www.w3.org/2005/Atom}link"
            )
            desc = entry.findtext("description") or entry.findtext(
                "{http://www.w3.org/2005/Atom}summary"
            )
            pub = entry.findtext("pubDate") or entry.findtext(
                "{http://www.w3.org/2005/Atom}updated"
            )
            # Atom link 可能是带属性的标签
            if not link:
                l = entry.find("{http://www.w3.org/2005/Atom}link")
                if l is not None:
                    link = l.get("href", "")

            if not title:
                continue
            title = strip_html(title)
            items.append({
                "title": title,
                "url": link or "",
                "summary": strip_html(desc)[:160] if desc else "",
                "source": feed["name"],
                "cat": feed["cat"],
                "published": pub or "",
            })
            count += 1
    return items


def dedup_items(items):
    """按标题去重，稳定顺序。"""
    seen = set()
    out = []
    for it in items:
        key = it["title"][:30]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


# ── 生成评测内容 ──────────────────────────────────────────────────

def make_daily_reviews(arxiv_papers, hn_stories):
    """从采集数据生成每日评测条目（不足则用兜底补全）。"""
    reviews = []
    today = datetime.now()

    # 从 Arxiv 生成
    for i, p in enumerate(arxiv_papers):
        title = p["title"][:80]
        if len(title) == 80:
            title += "…"
        # 提取核心关键词做标签
        tags = ["Arxiv", "论文"]
        summary_words = p["summary"][:160]
        for kw in ["模型", "训练", "数据", "推理", "生成", "transformer", "attention",
                    "RLHF", "RAG", "Lora", "对齐", "多模态", "视觉", "语言"]:
            if kw.lower() in p["summary"].lower() or kw.lower() in p["title"].lower():
                tags.append(kw)
                if len(tags) >= 3:
                    break
        reviews.append({
            "title": f"📄 {title}",
            "desc": f"新论文 — {', '.join(p['authors'][:2])} | {summary_words}…",
            "tags": tags[:3],
            "url": p.get("url", ""),
        })
        if len(reviews) >= 4:
            break

    # 从 HN 生成
    for i, s in enumerate(hn_stories):
        if len(reviews) >= 8:
            break
        title = s["title"][:80]
        if len(title) == 80:
            title += "…"
        reviews.append({
            "title": f"🔥 {title}",
            "desc": f"HackerNews 热点 · {s['points']} 票 · @{s['author']}",
            "tags": ["社区热议", "HackerNews"],
            "url": s.get("url", ""),
        })

    # 用兜底补全到至少 6 条
    for fallback_title, fallback_desc, fallback_tags in FALLBACK_REVIEWS:
        if len(reviews) >= 6:
            break
        reviews.append({"title": fallback_title, "desc": fallback_desc, "tags": fallback_tags, "url": ""})

    # 分配日期（从今天往前倒推）
    result = []
    for idx, r in enumerate(reviews[:8]):
        d = today - timedelta(days=idx)
        date_str = f"{d.month}/{d.day}"
        result.append({"date": date_str, "title": r["title"], "desc": r["desc"],
                       "tags": r["tags"], "url": r.get("url", "")})

    return result


def make_weekly_assessment():
    """基于 ISO 周号轮换周测评内容。"""
    now = datetime.now()
    week_num = now.isocalendar()[1]
    idx = week_num % len(WEEKLY_DATASET)
    data = WEEKLY_DATASET[idx]

    # 计算本周一和周日
    monday = now - timedelta(days=now.weekday())
    sunday = monday + timedelta(days=6)
    range_str = f"{monday.month}/{monday.day} - {sunday.month}/{sunday.day}"
    week_str = f"第 {week_num} 周"

    return data, range_str, week_str


# ── HTML 渲染 ─────────────────────────────────────────────────────

# ── 工具官网映射（点击卡片跳转）──
# 统一用根域名/官网首页，规避子路径被 Cloudflare 反爬拦截。
TOOL_URLS = {
    "ChatGPT": "https://openai.com",
    "Claude": "https://claude.ai",
    "DeepSeek": "https://www.deepseek.com",
    "Gemini": "https://gemini.google.com",
    "Grok": "https://grok.com",
    "Kimi": "https://kimi.moonshot.cn",
    "通义千问": "https://tongyi.aliyun.com",
    "文心一言": "https://yiyan.baidu.com",
    "豆包": "https://www.doubao.com",
    "Midjourney": "https://www.midjourney.com",
    "DALL·E 3": "https://openai.com",
    "Stable Diffusion": "https://stability.ai",
    "ComfyUI": "https://www.comfy.org",
    "Flux": "https://blackforestlabs.ai",
    "Canva AI": "https://www.canva.com",
    "Recraft": "https://www.recraft.ai",
    "GitHub Copilot": "https://github.com/features/copilot",
    "Cursor": "https://cursor.com",
    "Windsurf": "https://windsurf.com",
    "Claude Code": "https://claude.ai",
    "Codeium": "https://codeium.com",
    "Replit Agent": "https://replit.com",
    "Sora": "https://openai.com",
    "Runway Gen-3": "https://runwayml.com",
    "Pika": "https://pika.art",
    "Kling": "https://klingai.com",
    "HeyGen": "https://www.heygen.com",
    "ElevenLabs": "https://elevenlabs.io",
    "Suno": "https://suno.com",
    "Udio": "https://udio.com",
    "Whisper": "https://openai.com",
    "Notion AI": "https://www.notion.so/product/ai",
    "Perplexity": "https://www.perplexity.ai",
    "Grammarly": "https://www.grammarly.com",
    "Gamma": "https://gamma.app",
    "Otter.ai": "https://otter.ai",
    "Beautiful.ai": "https://www.beautiful.ai",
    "HuggingFace": "https://huggingface.co",
    "Replicate": "https://replicate.com",
    "Poe": "https://poe.com",
    "Leonardo AI": "https://leonardo.ai",
}


def render_tool_cards():
    """渲染工具卡片 HTML（可点击跳转官网，新标签页打开）。"""
    cards = []
    for t in TOOLS:
        url = TOOL_URLS.get(t["n"], "#")
        attr = f'href="{url}" target="_blank" rel="noopener"' if url != "#" else 'href="#"'
        cards.append(
            f'<a class="tool-card cat-{t["c"]}" {attr} data-name="{t["n"]}">'
            f'<div class="icon">{t["i"]}</div>'
            f'<h3>{t["n"]}</h3>'
            f'<p>{t["d"]}</p>'
            f"</a>"
        )
    return "\n            ".join(cards)


def render_reviews(reviews):
    """渲染评测条目 HTML（整条可点击跳转原文，新标签页打开）。"""
    items = []
    for r in reviews:
        tags_html = "".join(f'<span>{t}</span>' for t in r["tags"][:3])
        url = r.get("url", "")
        if url:
            item = (
                f'<a class="review-item" href="{esc_attr(url)}" target="_blank" rel="noopener">'
                f'<div class="review-date">{r["date"]}</div>'
                f'<div class="review-content">'
                f'<h4>{r["title"]} <span class="ext">↗</span></h4>'
                f'<p>{r["desc"]}</p>'
                f'<div class="tags">{tags_html}</div>'
                f"</div></a>"
            )
        else:
            item = (
                f'<div class="review-item">'
                f'<div class="review-date">{r["date"]}</div>'
                f'<div class="review-content">'
                f'<h4>{r["title"]}</h4>'
                f'<p>{r["desc"]}</p>'
                f'<div class="tags">{tags_html}</div>'
                f"</div></div>"
            )
        items.append(item)
    return "\n            ".join(items)


def render_scores(scores_dict):
    """渲染评分 HTML."""
    items = []
    for label, value in scores_dict.items():
        items.append(
            f'<div class="score-item">'
            f'<div class="value">{value}</div>'
            f'<div class="label">{label}</div>'
            f"</div>"
        )
    return "\n                ".join(items)


def render_deep_news(news_items):
    """渲染深度新闻条目 HTML（带来源标签）。"""
    items = []
    for n in news_items:
        cat_label = RSS_CAT_LABEL.get(n["cat"], "")
        items.append(
            f'<div class="review-item">'
            f'<div class="review-date">{esc_attr(n["source"])}</div>'
            f'<div class="review-content">'
            f'<h4><a href="{esc_attr(n["url"])}" target="_blank" rel="noopener">{esc_attr(n["title"])}</a></h4>'
            f'<p>{esc_attr(n["summary"])}</p>'
            f'<div class="tags"><span>{cat_label}</span><span>深度</span></div>'
            f"</div></div>"
        )
    return "\n            ".join(items)


def export_xiaohongshu_json(news_items, path):
    """导出深度新闻为 JSON，供小红书自动发布任务复用。"""
    picks = [n for n in news_items if n["cat"] in XIAOHONGSHU_CATS]
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "ai-tools-nav RSS 聚合",
        "candidates": [
            {
                "title": n["title"],
                "url": n["url"],
                "summary": n["summary"],
                "source": n["source"],
                "category": RSS_CAT_LABEL.get(n["cat"], ""),
            }
            for n in picks[:10]
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(payload["candidates"])


def _wechat_safe_url(url):
    """把 URL 中的 & 预编码为 %26，避免微信发送通道(iLink)按 & 拆分参数导致链接截断。
    微信点击时会自动把 %26 解码回 &，还原完整链接。"""
    return (url or "").replace("&", "%26")


def export_wechat_daily(news_items, path):
    """导出深度新闻日报 JSON，供微信推送任务复用（含全部源、按分类分组）。"""
    by_cat = {}
    for n in news_items:
        label = RSS_CAT_LABEL.get(n["cat"], "其他")
        by_cat.setdefault(label, []).append({
            "title": n["title"],
            "url": _wechat_safe_url(n["url"]),
            "summary": n["summary"],
            "source": n["source"],
        })
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "ai-tools-nav RSS 聚合",
        "total": len(news_items),
        "by_category": by_cat,
        "all": [
            {"title": n["title"], "url": _wechat_safe_url(n["url"]), "source": n["source"],
             "category": RSS_CAT_LABEL.get(n["cat"], "")}
            for n in news_items
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(news_items)


def build_page(reviews, week_data, week_range_str, week_str, generated_at, deep_news):
    """填充模板生成完整 HTML."""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now()

    tools_json = json.dumps([{"n": t["n"]} for t in TOOLS], ensure_ascii=False)

    replacements = {
        "{{TOOL_COUNT}}": str(len(TOOLS)),
        "{{TOOL_CARDS}}": render_tool_cards(),
        "{{DAILY_REVIEWS}}": render_reviews(reviews),
        "{{DEEP_NEWS}}": render_deep_news(deep_news),
        "{{DEEP_NEWS_DATE}}": f"{now.year}-{now.month:02d}-{now.day:02d}",
        "{{DAILY_DATE}}": f"{now.year}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}",
        "{{WEEK_TITLE}}": week_data["title"],
        "{{WEEK_RANGE}}": f"{week_str} · {week_range_str}",
        "{{WEEKLY_RANGE}}": week_range_str,
        "{{WEEK_SCORES}}": render_scores(week_data["scores"]),
        "{{WEEK_DETAIL}}": week_data["detail"],
        "{{GENERATED_AT}}": generated_at,
        "{{YEAR}}": str(now.year),
        "{{TOOLS_JSON}}": tools_json,
    }

    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    return html


# ── 主流程 ────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  🤖 AI 工具导航 · 自动采集生成器")
    print("=" * 50)

    now = datetime.now()
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. 采集
    print(f"\n[{generated_at}] 开始采集...")
    print("  📡 正在抓取 Arxiv 最新论文...")
    arxiv_papers = fetch_arxiv_papers()
    print(f"     → 获取 {len(arxiv_papers)} 篇论文")

    print("  📡 正在抓取 HackerNews AI 话题...")
    hn_stories = fetch_hn_stories()
    print(f"     → 获取 {len(hn_stories)} 条热帖")

    print("  📡 正在抓取 TechCrunch AI 资讯...")
    tc_items = fetch_techcrunch_rss()
    print(f"     → 获取 {len(tc_items)} 条资讯")

    print("  📡 正在抓取中文/英文 RSS 深度新闻源...")
    rss_items = fetch_rss_feeds(per_feed=2)
    rss_items = dedup_items(rss_items)
    print(f"     → 获取 {len(rss_items)} 条深度新闻")

    # 2. 生成
    print("\n  ✍️  生成每日评测...")
    # 合并 HN 和 Arxiv 生成评测
    all_stories = hn_stories + tc_items
    reviews = make_daily_reviews(arxiv_papers, all_stories)
    print(f"     → {len(reviews)} 条评测条目")

    print("  ✍️  生成每周测评...")
    week_data, week_range_str, week_str = make_weekly_assessment()
    print(f"     → {week_data['title']} ({week_range_str})")

    # 2.5 导出小红书候选素材
    xhs_path = BASE_DIR / "xiaohongshu_candidates.json"
    n_xhs = export_xiaohongshu_json(rss_items, xhs_path)
    print(f"  📤 导出小红书候选素材 → {n_xhs} 条 ({xhs_path.name})")

    # 2.6 导出微信深度新闻日报
    wx_path = BASE_DIR / "wechat_daily.json"
    n_wx = export_wechat_daily(rss_items, wx_path)
    print(f"  📲 导出微信日报素材 → {n_wx} 条 ({wx_path.name})")

    # 3. 构建页面
    print("\n  🏗️   生成 index.html...")
    html = build_page(reviews, week_data, week_range_str, week_str, generated_at, rss_items)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"     ✅ 已写入 {OUTPUT_PATH} ({size_kb:.1f} KB)")

    print(f"\n  ✅ 完成！运行耗时：{(datetime.now() - now).total_seconds():.1f}s")
    print("=" * 50)


if __name__ == "__main__":
    main()
