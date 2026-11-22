# 知乎讲义导出试验

仅转换讲义内容；**不登录知乎、不上传图片、不发布文章、不修改正式站点**。目前只支持《如何理解一致连续》，不假定其他 MDX 组件能自动转换。实验完成前保留在 `experiment/zhihu-markdown-export` 分支。

## 用法

在 `annouimo-publishing` 根目录：

```bash
# 先导入固定版本的讲义原稿（需要正常访问 GitHub）
npm run prepare:content

# 为导出功能准备独立 Python 环境
python3 -m venv .venv-zhihu
.venv-zhihu/bin/python -m pip install numpy matplotlib

# 生成 article.md + images/*.png
.venv-zhihu/bin/python scripts/export-zhihu.py
```

输出位置：`dist/zhihu/uniform-continuity/`。也可使用 `--source` 和 `--output` 指定路径。

## 内容原则

- 唯一原稿仍是 `annouimo-notes` 中的 MDX；转换只针对交互说明作有限的静态化措辞调整，不擅自删减论证。
- 7 个 `ContinuityBox` 分别转换为包含多个位置的 PNG 图；原公式保持 `$...$` / `$$...$$`，4 处折叠内容展开为正文。
- 不添加作者简介、博客链接、个人网站、Github、页脚、二维码、宣传内容或来源说明。导出脚本遇到明显的站点字符串或未经适配的 MDX 组件直接报错。
- **静态图展示的是几个经过选择的位置，不能代替对全部定义域的数学证明。**
- 不要把生成目录提交到仓库；请将其视为需要人工验收的临时产物。

## 人工导入验收

先打开 `article.md`，检查九个二级标题、6 处块公式、7 处图片位置及最后的复习问题。图片为**本地相对路径**，在 Markdown 预览软件中可正常显示；知乎的 Markdown 导入是否自动上传这些图片取决于其当前编辑器实现，不能保证。

在知乎编辑器导入 `article.md` 后先保存草稿、刷新检查。若图片没有自动转存，则从 `images/` 手工将七张图插入对应标记位置；务必在草稿中检查数学公式是否变成可阅读的公式。检查完毕再自行点击发布。

本试验不包含自动发表，也不包含对其他讲义的自动转换。