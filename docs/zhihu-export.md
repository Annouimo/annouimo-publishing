# 知乎讲义导出：先完整转换，再人工验收与发布

该功能仅位于 `experiment/zhihu-markdown-export` 实验分支，**不连接知乎账号、不自动发布、不修改博客生产环境**。知乎文章只保留讲义本身，不含个人主页、博客、GitHub、原文地址或引流说明。

## 当前采用的流程：手动插图

《麦克斯韦方程组》讲义保留全部数学内容。源文件来自 `notes.lock` 指向的 `annouimo-notes` MDX。全部教学图直接从原有 Astro 组件浏览器渲染导出，不另起一套不一定准确的绘图代码。

```bash
# annouimo-publishing 根目录，在已有 Node 24 环境中
npm ci
npm install --no-save playwright-core
npm run prepare:content

# 临时将 scripts/zhihu-maxwell-capture.astro
# 复制到 src/pages/zhihu-capture-offline.astro，
# 启动带 devToolbar:{enabled:false} 的独立本地 Astro 服务
# 然后截图。推荐直接使用本分支的 GitHub Actions 工作流进行重现。
node scripts/render-zhihu-maxwell.mjs
python3 scripts/export-zhihu-maxwell.py
python3 scripts/package-zhihu-manual.py dist/zhihu/maxwell-equations --expected 28
```

成功后，`dist/zhihu/maxwell-equations-manual.zip` 包含：

- `article.manual.md`：知乎手动导入用，带插图 01—28 的明确占位标记。
- `images/`：28 张以 01—28 编号的高清 PNG；分别是 18 张原始 SVG 和 10 张交互关键状态。
- `article.md`：完整标准 Markdown，保留本地相对图片路径，方便离线预览和未来转换。
- `插图顺序.txt`、`图片预览索引.html`、`使用说明.txt`。

**手动导入的操作：** 在知乎新建文章 → 导入 `article.manual.md` → 从 `images/` 依编号上传图片 → 确认插入成功后删掉占位提示 → 保存草稿、刷新检查全部图片、数学公式、章节 → 人工决定是否发表。

## 内容验收

- 14 个二级章节、12 处折叠解释完整保留；把 1 处单独的单美元符号公式修正为块公式分隔符。
- 18 个 `TeachingFigure` 图准确提取原组件 SVG，独立保存 PNG；标题和图注仍以 Markdown 正文形式出现。
- 三个 `MaxwellLab` 的状态按数学意图展开：矢量场五种、电容器两种、电磁波三种，合计 10 张。
- 禁止未转换的 MDX 标签；全部 28 张图必须存在于 Markdown 原位，图片相对路径完整可读。
- 使用无悬浮开发工具栏的独立截图页面，2× 像素比截图；按实际导出的 PNG 做人工视觉验收。
- 全程不登录知乎，也没有将文章或图片上传外部图床。

## 以后再决定图床

公共图床和自建图床的选择**暂时搁置**。之前的上传适配脚本 `scripts/host-zhihu-cn-images.py` 只是既往实验，不属于当前默认流程；不能让其上传额度、图片压缩或中国大陆连通性反过来决定讲义画质。

《一致连续》已有的 Markdown 导出脚本继续保留，先不再调整该篇。
