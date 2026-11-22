# 知乎讲义手动导入：Markdown 与外链图片

实验分支：`experiment/zhihu-markdown-export`。只适配《如何理解一致连续？》；**不发布知乎文章、不修改博客生产环境、不合并 main**。

## 操作流程

```bash
# 在 annouimo-publishing 仓库根目录
bash scripts/import-notes.sh

# 首次安装数学绘图依赖
python3 -m venv dist/.venv-zhihu
dist/.venv-zhihu/bin/python -m pip install numpy matplotlib

# 离线生成原稿和七张本地图片
dist/.venv-zhihu/bin/python scripts/export-zhihu.py

# 先检查（不联网）
python3 scripts/host-zhihu-images.py

# 真正上传图片并逐张下载校验；默认采用已验证成功的 Pomf
python3 scripts/host-zhihu-images.py --upload --provider pomf
```

成功产物是 `dist/zhihu/uniform-continuity/article.zhihu.md`，直接作为知乎编辑器的 Markdown 文件导入。运行时只上传七张讲义图片，正文不会上传至临时图床。该 Markdown **不包含**个人网站、博客、GitHub 或任何与个人主页有关的内容。

若遇图床不可达，也保留 `--provider litterbox` 和 `--provider 0x0` 供独立测试；实际记录：2026-11-22 的 GitHub Actions 测试中，Litterbox 返回 HTTP 412，0x0.st 返回 HTTP 503，Pomf 上传并下载校验七张图片全部成功。

Pomf 生成的 URL 为 `https://pomf2.lain.la/f/....png`，它不是无限可靠的正式图床，也**不承诺恰好 72 小时的可用期**。即使预期只需很短的导入时间，仍应尽快完成操作和验收。保存的 `hosted-images-pomf.json` 中 72 小时是脚本对链接复用设置的保守截止时间，**不是图床服务商的有效期保证**。

## 验收要求

1. 上传程序会要求恰好七张预期 PNG，返回 URL 只允许指定的第三方图床，并逐张重新下载，用 SHA-256 确认字节不变。
2. 导出内容应有九个二级章节、六处块公式、七处正文插图；原稿正文保持一致，图片链接之外不做内容替换。
3. 将 `article.zhihu.md` 导入知乎，保存草稿并重新打开，确认七张图片全部可见、公式正确。
4. **必须验证知乎是否真正转存图片**：检查图片地址是否切换为知乎的 `zhimg.com` 等图片域名。如果保留 `pomf2.lain.la` 外链，就不能把这些图片当成稳定持久资源直接发布。
5. 不在知乎正文中添加任何个人网站或博客介绍、原文链接、来源标识、页脚。

## 自动化边界

`.github/workflows/zhihu-temp-images.yml` 只为测试运行：在 GitHub Actions 中生成图片、匿名上传第三方临时图床、输出可下载的 Markdown Artifact。它**不会**访问知乎账号或发布文章。成功测试：<https://github.com/Annouimo/annouimo-publishing/actions/runs/44973649039>。

实验分支保持独立；未经人工验证知乎编辑器表现前，不合入正式发布流程。
