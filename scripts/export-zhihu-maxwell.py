#!/usr/bin/env python3
"""Export the complete Maxwell-equations MDX lecture to offline Zhihu Markdown.

Render figures from the actual Astro components first with render-zhihu-maxwell.mjs.
No network calls, no publication, and no author/site references in article.md.
"""
import argparse
import json
import re
from pathlib import Path

FIGURES = (
    "field", "differential-plane", "potential-slopes", "potential",
    "flux-plane", "flux", "divergence", "volume-cancel", "charge",
    "curl", "cancellation", "forms", "mixed-partials", "boundary-square",
    "gauss-sphere", "gauss-cone", "coupling", "wave-shift",
)
LAB_STATES = {
    "field": ("constant", "source", "rotation", "both", "saddle"),
    "capacitor": ("s1", "s2"),
    "wave": ("phase-0", "phase-1", "phase-2"),
}
LAB_HEADING = {
    "field": "五种矢量场：比较散度与旋度",
    "capacitor": "固定回路 C：比较两张积分曲面",
    "wave": "不同时刻：电场与磁场一起传播",
}
COMPONENT = re.compile(r'<(TeachingFigure|MaxwellLab)\s+kind="([a-z-]+)"\s*/>')
DETAILS = re.compile(r'<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>', re.S)
FRONTMATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.S)
PERSONAL = re.compile(r'(?i)(?:annouimo|why[-_ ]?notes|https?://|www\.|github\.com|个人网站|我的博客|博客地址|阅读原文)')


def ensure_metadata(raw, directory):
    if set(raw.get("figures", {})) != set(FIGURES):
        raise ValueError("Screenshot metadata must contain exactly 18 original figures")
    if set(raw.get("labs", {})) != set(LAB_STATES):
        raise ValueError("Screenshot metadata must contain exactly 3 labs")
    files = []
    for kind in FIGURES:
        fig = raw["figures"][kind]
        if not fig.get("title") or not fig.get("caption"):
            raise ValueError("Figure missing title/caption: " + kind)
        files.append(f"figure-{kind}.png")
    for lab, states in LAB_STATES.items():
        labdata = raw["labs"][lab]
        if [s.get("id") for s in labdata.get("states", [])] != list(states):
            raise ValueError("Lab screenshot states are incomplete: " + lab)
        files += [f"lab-{lab}-{state}.png" for state in states]
    for filename in files:
        path = directory / "images" / filename
        if not path.is_file() or path.stat().st_size < 2500:
            raise ValueError("Missing or suspicious screenshot: " + str(path))
    if len(files) != 28:
        raise ValueError(f"Expected 28 illustrations, got {len(files)}")
    return files


def clean_caption(value):
    s = " ".join(value.split())
    if "<" in s or ">" in s or "http" in s.lower():
        raise ValueError("Unexpected HTML/URL in figure caption")
    return s


def make_export(source, directory, raw):
    input_md = source.read_text(encoding="utf-8")
    front = FRONTMATTER.match(input_md)
    if not front:
        raise ValueError("MDX is missing expected frontmatter")
    title_match = re.search(r"(?m)^title:\s*(.*?)\s*$", front.group(1))
    if not title_match:
        raise ValueError("Lecture title not found")
    title = title_match.group(1).strip().strip("\"'")
    body = input_md[front.end():]
    body, count = re.subn(r"(?m)^import\s+[^\n]+\n", "", body)
    if count != 2:
        raise ValueError(f"Expected two Astro component imports, saw {count}")

    # Expand all educational aside details rather than silently omitting them.
    def unfold(m):
        return "\n\n**" + m.group(1).strip() + "**\n\n" + m.group(2).strip() + "\n\n"
    body, expanded = DETAILS.subn(unfold, body)
    if expanded != 12:
        raise ValueError(f"Expected twelve collapsible explanations; got {expanded}")

    # One display equation is delimited by standalone single dollars in the MDX.
    # Normalize its Markdown delimiter without modifying any mathematics.
    body, standalone = re.subn(r"(?m)^\$\s*$", "$$", body)
    if standalone != 2:
        raise ValueError(f"Expected exactly two standalone single-dollar lines; got {standalone}")

    seen_figures, seen_labs = [], []

    def replace_component(m):
        category, kind = m.group(1), m.group(2)
        if category == "TeachingFigure":
            if kind not in FIGURES or kind in seen_figures:
                raise ValueError("Unknown/duplicated TeachingFigure: " + kind)
            seen_figures.append(kind)
            data = raw["figures"][kind]
            t = clean_caption(data["title"])
            c = clean_caption(data["caption"])
            return f"\n\n**{t}**\n\n![{t}](images/figure-{kind}.png)\n\n*{c}*\n\n"

        if kind not in LAB_STATES or kind in seen_labs:
            raise ValueError("Unknown/duplicated MaxwellLab: " + kind)
        seen_labs.append(kind)
        data = raw["labs"][kind]
        chunks = ["\n\n**" + LAB_HEADING[kind] + "（静态图比较）**\n\n"]
        for state in data["states"]:
            label = clean_caption(state["label"])
            result = clean_caption(state["result"])
            image = f"images/lab-{kind}-{state['id']}.png"
            chunks.append(f"![{LAB_HEADING[kind]}：{label}]({image})\n\n*{label}：{result}*\n\n")
        note = clean_caption(data.get("footnote", ""))
        if note:
            chunks.append(note + "\n\n")
        return "".join(chunks)

    body = COMPONENT.sub(replace_component, body)
    if seen_figures != list(FIGURES):
        raise ValueError("Original TeachingFigure ordering unexpectedly changed")
    if seen_labs != list(LAB_STATES):
        raise ValueError("Original MaxwellLab ordering unexpectedly changed")

    # Replace the one instruction that explicitly requires a slider.
    old = ("你可以拖动时间滑块，观察两者的方向始终互相垂直，"
           "以及同一波峰如何沿 $+x$ 移动。")
    new = ("比较图中不同时刻的状态，观察电场和磁场的振荡方向始终互相垂直，"
           "以及同一波峰如何沿 $+x$ 移动。")
    if body.count(old) != 1:
        raise ValueError("Could not locate the interactive time-slider instruction")
    body = body.replace(old, new)

    if re.search(r'<(?:TeachingFigure|MaxwellLab|details|summary)\b', body):
        raise ValueError("MDX or HTML components remain unconverted")
    if PERSONAL.search(body):
        raise ValueError("Potential personal website/external link in lecture text")
    output = "# " + title + "\n\n" + body.strip() + "\n"

    md_path = directory / "article.md"
    md_path.write_text(output, encoding="utf-8")
    paths = re.findall(r'!\[[^\]\n]*\]\((images/[^)]+\.png)\)', output)
    if len(paths) != 28 or len(set(paths)) != 28:
        raise ValueError(f"Markdown should reference 28 unique PNGs, got {len(paths)}")
    for rel in paths:
        if not (directory / rel).is_file():
            raise ValueError("Broken relative image reference: " + rel)
    if output.count("$$") != input_md.count("$$") + 2:
        raise ValueError("Block-math delimiters unexpectedly changed")
    return md_path, paths, expanded


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("src/content/notes/maxwell-equations/index.mdx"))
    p.add_argument("--output", type=Path, default=Path("dist/zhihu/maxwell-equations"))
    a = p.parse_args()
    raw = json.loads((a.output / "screenshots.json").read_text(encoding="utf-8"))
    files = ensure_metadata(raw, a.output)
    md, paths, expanded = make_export(a.source, a.output, raw)
    print(f"VALID: {md} | {len(files)} images, {expanded} expanded explanations")
    print(f"Markdown: {md.stat().st_size} bytes, images: {len(paths)}")
    print("No personal-site links or web URLs in the offline article.")


if __name__ == "__main__":
    main()
