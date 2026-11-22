# 知乎讲义导出试验（Markdown + 临时外链图片）

实验分支：`experiment/zhihu-markdown-export`。**不发布知乎文章、不修改博客生产环境、不合并 main。** 当前只适配《如何理解一致连续？》。本流程专注独立讲义发布；输出的文章不包含个人主页、博客、GitHub、作者介绍或引流文字。

## 生成流程

在 `annouimo-publishing` 根目录运行：

```bash
# 1. 按 notes.lock 获取 MDX 原稿（需要联网）
npm run prepare:content

# 2. 仅第一次：为数学图生成器准备依赖
python3 -m venv dist/.venv-zhihu
dist/.venv-zhihu/bin/python -m pip install numpy matplotlib

# 3. 离线导出：article.md + images/ 下的 7 张 PNG
dist/.venv-zhihu/bin/python scripts/export-zhihu.py

# 4. 不联网的预检查（推荐先执行）
python3 scripts/host-zhihu-images.py

# 5. 显式上传 7 张图到匿名临时图床，并生成外链 Markdown
python3 scripts/host-zhihu-images.py --upload
```

最终供知乎“导入 Markdown”使用的文件：`dist/zhihu/uniform-continuity/article.zhihu.md`。

首次成功后还会保存 `hosted-images.json`：记录每张图的 URL、原图 SHA-256 和预计过期时间。重复运行 `--upload` 时会复用仍然有效的图片并重新检验实际下载内容；加 `--reuse` 可以只验证并重建，不再上传新图片。

如果只想测试上传步骤，而不运行原始项目的依赖，可使用包含 `article.md`、`images/` 和 `host-zhihu-images.py` 的离线测试包，从其目录运行：

```bash
python3 host-zhihu-images.py --input article.md --upload
```

上传脚本只用 Python 标准库；不需要知乎 Cookie、API 密钥或任何额外账号。

## 暂存与失效风险

Litterbox 暂存最长 72 小时，返回 `https://files.catbox.moe/...png` 的公开 URL。**暂存不是最终图床**：

1. Markdown 导入知乎后，先保存草稿并重新打开。
2. 对全部七张图分别检查：图片的实际地址应属于知乎图片服务器（例如 `picx.zhimg.com` 或 `pic*.zhimg.com`），且刷新后仍能显示。
3. 如果仍指向 `files.catbox.moe`，说明知乎没有转存；**不要正式发布依赖会过期外链的文章**。
4. 如果知乎导入失败，查看上传日志；该图床可能因网络地区、访问限制或防护策略而无法供知乎抓取。可再选择其他不关联个人身份的图片托管方案。

图片由第三方公开托管期间，拥有 URL 的人都可以访问图片内容；不要用于任何私人材料。本工具不会自动清理，暂存图由服务商到期处理。

## 内容及安全验收

- 唯一原稿仍是 `annouimo-notes` 的 MDX，先由旧脚本完成有限的静态化措辞调整。
- 七张插图保留原本的正文位置，LaTeX 保持原样；不压缩或重新改写讲义。
- 第二步脚本**只替换图片 Markdown 链接**，不动其他文字。
- 上传前要求存在恰好七张预期 PNG，并拒绝已含个人站点信息或未转换的图片链接的文章。
- 上传后逐张从公网下载，验证 SHA-256 与本地 PNG 一致。
- 任一步失败都会退出，不生成新的可导入外链 Markdown；旧的 `article.md` 不被覆盖。
- `dist/` 已被 Git 忽略，图片 URL 和导出文件不进入公共仓库。
- 仍需人工检查公式、图文对应关系以及知乎草稿保存后的图片是否真正转存。

这些脚本**从不调用知乎登录或发布接口**。由使用者手工将最终 Markdown 导入知乎并检查草稿。