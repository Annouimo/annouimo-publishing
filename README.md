# Annouimo Publishing

Astro 发布工程，负责博客与讲义的模板、正文样式、归档和 RSS。

- 博客原稿由 annouimo-writing 提供。导入只读取明确标记为可发布的 Markdown，构建目录是临时产物。
- 讲义及其专用组件由 annouimo-notes 提供，`notes.lock` 固定来源提交。`NOTES_SOURCE` 可指向本地 annouimo-notes 工作树。更新该锁文件后，在 annouimo-writing 的 Actions 手动运行 `Publish Astro blog`。
- 共用设计由 annouimo-home 提供，版本由 `design.lock` 固定。

```sh
npm ci
python -m pip install 'PyYAML>=6,<7'
python scripts/import-writing.py ../annouimo-writing
npm run build
```

`npm run build:preview` 允许预览讲义草稿，并标记页面 noindex。博客始终应用相同的发布筛选。Astro 静态产物位于 `.cloudflare/output/v0/workers/default/assets`。
