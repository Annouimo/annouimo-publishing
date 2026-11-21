import os
import re
from urllib.parse import quote
from pathlib import Path


def find_image(name: str, current_file: Path, config):
    p = (current_file.parent / name).resolve()
    if p.is_file():
        return p
    target = Path(name).name
    for root, _, files in os.walk(config.obsidian_dir):
        if target in files:
            return (Path(root) / target).resolve()
    return None


def process_body(body: str, info: dict, slug_index: dict, name_index: dict, config):
    warnings = []
    images = []
    src_file = info["src"]
    prefix = config.image_url_prefix
    md_ext = config.md_ext

    def repl_md_img(m):
        alt, path = m.group(1), m.group(2)
        if path.startswith(("http://", "https://", "/")):
            return m.group(0)
        img = find_image(path, src_file, config)
        if not img:
            warnings.append(f"图片未找到: {path}")
            return m.group(0)
        images.append(img)
        return f"![{alt}]({prefix}{quote(img.name)})"

    def repl_wiki_img(m):
        path = m.group(1).split("|")[0].strip()
        if path.startswith(("http://", "https://", "/")):
            return m.group(0)
        img = find_image(path, src_file, config)
        if not img:
            warnings.append(f"图片未找到: {path}")
            return m.group(0)
        images.append(img)
        return f"![]({prefix}{quote(img.name)})"

    body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl_md_img, body)
    body = re.sub(r"!\[\[([^\]]+)\]\]", repl_wiki_img, body)

    def make_ref(target_file: Path, text: str):
        if target_file not in slug_index:
            warnings.append(f"链接目标不在同步范围: {target_file.name}")
            return None
        sec, slug = slug_index[target_file]
        return f'[{text}](/{sec}/{slug}/)'

    def repl_md_link(m):
        text, path = m.group(1), m.group(2)
        if path.startswith(("http://", "https://", "mailto:", "#", "/")):
            return m.group(0)
        if not path.endswith(md_ext):
            return m.group(0)
        target = (src_file.parent / path).resolve()
        if target not in slug_index:
            target_name = Path(path).name
            for k in slug_index:
                if k.name == target_name:
                    target = k
                    break
        ref = make_ref(target, text)
        return ref if ref else m.group(0)

    def repl_wiki_link(m):
        inner = m.group(1)
        parts = inner.split("|", 1)
        name = parts[0].split("#")[0].strip()
        text = parts[1].strip() if len(parts) > 1 else name
        if name.endswith(md_ext):
            name = name[: -len(md_ext)]
        if name in name_index:
            ref = make_ref(name_index[name], text)
            return ref if ref else m.group(0)
        warnings.append(f"wikilink 目标未找到: {name}")
        return m.group(0)

    body = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", repl_md_link, body)
    body = re.sub(r"(?<!!)\[\[([^\]]+)\]\]", repl_wiki_link, body)

    return body, images, warnings
