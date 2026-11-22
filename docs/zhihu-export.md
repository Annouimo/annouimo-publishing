# 知乎讲义 Markdown 导出与图片暂存

本流程只处理讲义，不连接知乎账号，也不进行自动发布。目前实验对象是《如何理解一致连续？》，实验分支为 `experiment/zhihu-markdown-export`。正式博客不受影响。

## 操作

```bash
# 在 annouimo-publishing 根目录
bash scripts/import-notes.sh
python3 -m venv dist/.venv-zhihu
dist/.venv-zhihu/bin/python -m pip install numpy matplotlib

# 先生成离线原稿和七张静态图
dist/.venv-zhihu/bin/python scripts/export-zhihu.py

# 先做不联网的结构检查
dist/.venv-zhihu/bin/python scripts/host-zhihu-cn-images.py

# 实际匿名上传七张图片（每分钟至多五张，脚本自动分批）
dist/.venv-zhihu/bin/python scripts/host-zhihu-cn-images.py --provider czl --upload
```

最终使用 `dist/zhihu/uniform-continuity/article.zhihu-cn.md` 手工导入知乎。图片临时放在 CZL 图床，真实直链域名为 `i.czl.net`。如果之前已经上传过同一张图片，脚本会先下载、校验完整性后复用，否则上传。

此前实验用的国外图床上传脚本已弃用并从分支中移除，避免误用；原始离线 Markdown 仍保留在生成目录中供验收。

## 保护与验收

- 只上传七张公开数学图，不上传 Markdown 正文，不联系知乎 API。
- 输出的知乎正文**不含**个人网站、GitHub、博客域名、作者介绍或“阅读原文”引流信息。导出器发现疑似个人信息或额外链接即拒绝继续。
- 正文内容和 LaTeX 不作更改；只有 Markdown 图片链接从 `images/*.png` 换成 HTTPS 图床直链。
- 导出结构含九个二级标题、六处块公式、七张插图。
- CZL 游客限制每分钟最多上传五张，脚本会暂停后继续；如果单张 PNG 太大，会自动转换为约 256 色调色板 PNG，保持原始像素尺寸。
- 上传后重新从图片直链下载图片，与**实际上传的 PNG** 比对 SHA-256；若托管服务重新编码，则核对图像像素及尺寸。
- 实际测试（2026-11-22）：<https://github.com/Annouimo/annouimo-publishing/actions/runs/44977577743>，七张图片全部上传并校验成功，Markdown 通过自动结构检查。
- 该记录只能证明 GitHub Actions 运行器的上传及访问成功；**不能代替中国大陆网络和知乎编辑器的实测**。
- CZL 提供 `expired_seconds=259200`（72 小时）请求参数，但游客组有权覆盖保留期；**不承诺确切保留时间**。请尽快导入，先保存草稿、刷新检查并验证图像已经转存到知乎自己的图片域名；如果仍是 `i.czl.net`，不要依赖临时图床长期公开发布。

实验分支尚未合入 `main`，也不修改已部署的网站。
