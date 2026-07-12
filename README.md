# AI 工具导航 · 每日评测 · 每周测评

一个自包含的 AI 工具导航站，每日自动采集最新 AI 资讯并生成静态页面。

## 功能
- **工具导航**：对话 / 图像 / 代码 / 视频 / 办公等分类的 AI 工具索引。
- **每日资讯**：从 Arxiv + HackerNews 自动抓取当日 AI 动态。
- **每周测评**：人工精选的周期性评测栏目。
- **纯静态**：`index.html` 自包含（CSS 内联），可直接托管到任意静态空间。

## 目录结构
```
index.html         # 站点主页面（静态，可直接部署）
generate.py        # 自动采集生成器（从 Arxiv + HackerNews 生成 index.html）
template.html      # 页面模板（generate.py 使用）
```

## 本地重新生成
```bash
python3 generate.py
# 生成的 index.html 即为可部署的站点
```

## 部署（GitHub Pages，免费）
1. 在 GitHub 新建一个 **Public** 仓库（如 `ai-tools-nav`）。
2. 推送本仓库：
   ```bash
   git remote add origin https://github.com/<你的用户名>/ai-tools-nav.git
   git push -u origin main
   ```
3. 仓库 **Settings → Pages**，Source 选 `main` 分支、文件夹 `/(root)`，保存。
4. 等待 1–2 分钟，访问 `https://<你的用户名>.github.io/ai-tools-nav/` 即可。

> 想要更干净的域名，可把仓库命名为 `<用户名>.github.io`，站点即出现在 `https://<用户名>.github.io/`。
