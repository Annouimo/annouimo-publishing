#!/usr/bin/env python3
"""Package verified offline Zhihu Markdown + ordered PNGs for manual insertion.

Usage:
  python3 scripts/package-zhihu-manual.py \
      dist/zhihu/maxwell-equations --expected 28

No network access; no publishing action; input PNGs stay unchanged.
"""
import argparse
import html
import re
import shutil
import struct
import zipfile
from pathlib import Path

IMAGE = re.compile(r'!\[([^\]\n]*)\]\((images/[^)\n]+\.png)\)')


def package(source, expected):
    original = (source / 'article.md').read_text(encoding='utf-8')
    found = list(IMAGE.finditer(original))
    if len(found) != expected:
        raise ValueError(f'Expected {expected} Markdown images, got {len(found)}')
    if len(re.findall(r'!\[', original)) != expected:
        raise ValueError('Unrecognized embedded image format')
    if re.search(r'(?i)(?:https?://|www\.|annouimo|github\.com|个人网站|阅读原文)', original):
        raise ValueError('An external URL or personal-site reference leaked into the article')

    target = source.with_name(source.name + '-manual-package')
    if target.exists():
        shutil.rmtree(target)
    (target / 'images').mkdir(parents=True)
    standard, manual, entries = [], [], []
    position = 0
    for number, m in enumerate(found, 1):
        alt, old_name = m.group(1), m.group(2)
        picture = source / old_name
        content = picture.read_bytes()
        if content[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Not a PNG: ' + old_name)
        width, height = struct.unpack('>II', content[16:24])
        if min(width, height) < 400:
            raise ValueError('Image resolution too small: ' + old_name)
        new_name = f'{number:02d}-' + picture.name
        (target / 'images' / new_name).write_bytes(content)
        standard.append(original[position:m.start()])
        manual.append(original[position:m.start()])
        standard.append(f'![{alt}](images/{new_name})')
        manual.append(f'**【插图 {number:02d}：{alt}】**\n\n'
                      f'*此处上传 images/{new_name}，确认成功后删除这两行占位文字。*')
        entries.append((number, new_name, alt, width, height))
        position = m.end()
    standard.append(original[position:])
    manual.append(original[position:])
    (target / 'article.md').write_text(''.join(standard), encoding='utf-8')
    (target / 'article.manual.md').write_text(''.join(manual), encoding='utf-8')
    (target / '插图顺序.txt').write_text(
        '\n'.join(f'{number:02d}. {name}  |  {alt}  |  {w}×{h}'
                  for number, name, alt, w, h in entries) + '\n', encoding='utf-8'
    )
    (target / '使用说明.txt').write_text(
        '知乎手动图文导入包\n\n'
        '1. 在知乎新建文章，导入 article.manual.md。\n'
        '2. 找到正文的【插图 01】至【插图 28】占位符，'
        '在原位从 images 文件夹上传编号一致的 PNG。\n'
        '3. 每次上传成功后删除对应的占位文字，保存草稿、刷新后检查全部图片与数学公式。\n'
        '4. article.md 采用标准本地相对图片路径，适合本地预览和未来使用图床，'
        '但知乎不会自动上传这些本地文件。\n'
        '5. 不要向知乎文章附加个人网站地址、GitHub 或其他引流信息。\n',
        encoding='utf-8')
    figures = ''.join(
        f'<figure><figcaption>{number:02d} · {html.escape(alt)}</figcaption>'
        f'<img src="images/{html.escape(name)}" alt="{html.escape(alt)}"></figure>'
        for number, name, alt, _, _ in entries
    )
    (target / '图片预览索引.html').write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>讲义插图索引</title>'
        '<style>body{max-width:850px;margin:auto;padding:20px;background:#f8f8f6;'
        'font:16px/1.7 system-ui,sans-serif;color:#222}'
        'figure{border:1px solid #ddd;background:white;border-radius:8px;'
        'padding:12px;margin:24px 0}img{display:block;max-width:100%;height:auto;margin:auto}'
        'figcaption{font-weight:600;margin-bottom:8px}</style>'
        f'<h1>讲义插图（{expected} 张）</h1>' + figures + '</html>',
        encoding='utf-8'
    )
    archive = source.with_name(source.name + '-manual.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as z:
        for file in sorted(target.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(target))
    print(f'PASS: {expected} ordered PNGs, 2 Markdown formats, archive {archive}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--expected', type=int, default=28)
    args = parser.parse_args()
    package(args.source, args.expected)


if __name__ == '__main__':
    main()
