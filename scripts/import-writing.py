"""Import explicitly published Obsidian articles into the Astro build."""
import argparse
from datetime import date, datetime
from pathlib import Path
import re
import shutil
from types import SimpleNamespace

import yaml

from obsidian_links import process_body

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = {"随笔": "blog", "研究": "research", "社会": "society", "个人经历": "about"}
FIELDS = {"标题": "title", "副标题": "subtitle", "发表日期": "date",
          "更新日期": "lastmod", "标签": "tags", "分类": "categories",
          "描述": "description", "摘要": "summary"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){0,5}")


def load_articles(source):
    articles = []
    keys = set()
    for path in sorted(source.rglob("*.md")):
        relative = path.relative_to(source)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError(f"{relative}: unsupported symbolic link")
        parts = re.split(r"^---[ \t]*$", path.read_text(encoding="utf-8-sig"), maxsplit=2, flags=re.M)
        if len(parts) != 3 or parts[0]:
            continue
        meta = yaml.safe_load(parts[1]) or {}
        if not isinstance(meta, dict):
            raise ValueError(f"{relative}: front matter must be a mapping")
        if type(meta.get("publish", False)) is not bool or type(meta.get("draft", False)) is not bool:
            raise ValueError(f"{relative}: publish and draft must be booleans")
        if meta.get("publish") is not True or meta.get("draft") is True:
            continue
        for original, target in FIELDS.items():
            if original in meta:
                meta.setdefault(target, meta[original])
        section = SECTIONS.get(relative.parts[0])
        slug = meta.get("slug")
        if not section or not meta.get("title") or not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise ValueError(f"{relative}: expected section, title and valid slug")
        for field in ("date", "lastmod"):
            value = meta.get(field, meta.get("date"))
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            if not isinstance(value, str):
                raise ValueError(f"{relative}: missing {field}")
            datetime.fromisoformat(value)
            meta[field] = value
        if (section, slug) in keys:
            raise ValueError(f"Duplicate route: /{section}/{slug}/")
        keys.add((section, slug))
        articles.append(dict(src=path, meta=meta, body=parts[2].lstrip("\n"), section=section, slug=slug))
    if not articles:
        raise ValueError("No publishable articles")
    return articles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    source = parser.parse_args().source.resolve(strict=True)
    articles = load_articles(source)
    index = {a["src"]: (a["section"], a["slug"]) for a in articles}
    names = {}
    for path in index:
        names.setdefault(path.stem, path)
    config = SimpleNamespace(obsidian_dir=source, image_url_prefix="/images/", md_ext=".md")
    images = {}
    outputs = {}
    for article in articles:
        body, used, warnings = process_body(article["body"], article, index, names, config)
        if warnings:
            raise ValueError(f"{article['src'].relative_to(source)}: {'; '.join(warnings)}")
        for image in used:
            if not image.is_relative_to(article["src"].parent) or not image.is_relative_to(source):
                raise ValueError(f"Image outside article directory: {image.name}")
            if images.setdefault(image.name, image) != image:
                raise ValueError(f"Duplicate image filename: {image.name}")
        meta = article["meta"]
        keep = ("title", "subtitle", "date", "lastmod", "description", "summary", "tags", "categories")
        front = yaml.safe_dump({k: meta[k] for k in keep if k in meta}, allow_unicode=True)
        filename = Path(article["section"]) / f"{article['slug']}.md"
        outputs[filename] = f"---\n{front}---\n{body}"
    content = ROOT / "src/content/writing"
    assets = ROOT / "public/images"
    for directory in (content, assets):
        shutil.rmtree(directory, ignore_errors=True)
        directory.mkdir(parents=True)
    for filename, text in outputs.items():
        destination = content / filename
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    for name, image in images.items():
        shutil.copyfile(image, assets / name)
    print(f"Imported {len(articles)} articles and {len(images)} images")


if __name__ == "__main__":
    main()
