#!/usr/bin/env python3
"""Export the reviewed uniform-continuity MDX as an offline Zhihu import package.

Install numpy + matplotlib first. This command never calls any publishing API,
logs in, uploads anything, or edits source MDX.
"""
import argparse
import re
from pathlib import Path

SCENES = {
    "sine": ("y = sin x", (-3.8, 3.8, -1.65, 1.65), [(-2.5,.4,"① 左侧"),(0,.4,"② 原点"),(2.5,.4,"③ 右侧")]),
    "square": ("y = x²", (-.2, 3.7, -.8, 12), [(.8,.2,"① 初始：满足"),(2,.2,"② 右移：失效"),(2,.1,"③ 收窄：满足"),(3.2,.1,"④ 再右移：失效")]),
    "root": ("y = √x", (-.55, 2.9, -.65, 2.3), [(0,.25,"① 原点附近"),(1.8,.25,"② 向右移动")]),
    "oscillation": ("y = sin(1/x)", (0,1.15,-1.65,1.65), [(.6,.06,"① 远离零"),(.16,.06,"② 接近零"),(.12,.03,"③ 收窄后")]),
    "damped": ("y = x sin(1/x)", (-.12,1.12,-1.55,1.55), [(.6,.025,"① 远离零"),(.08,.025,"② 接近零"),(0,.025,"③ 原点")]),
    "inverse": ("y = 1/x", (0,2,-.7,7), [(1,.15,"① 远离零"),(.3,.15,"② 接近零"),(.2,.075,"③ 收窄后")]),
    "chirp": ("y = sin(x²)", (0,5.4,-1.65,1.65), [(1,.2,"① 较低频率"),(4.3,.2,"② 右侧振荡"),(4.8,.1,"③ 收窄后")]),
}

# Approved small changes needed when the original interactive component is static.
TEXT_ADAPTATIONS = {
    "**试一试**：拖动中心点，或用左右按钮移动。走过上升段、波峰和波谷，看看曲线有没有在左右边界之间触及红线。":
      "**看图比较**：小框在曲线不同位置保持同一大小。经过上升段、波峰和波谷时，曲线有没有在绿色左右边界之间触及红线？",
    "框移到了新位置，曲线在框里的样子也变了，但这个宽度一直够用。":
      "三个位置的曲线形状不同，但这只宽度相同的小框都能容纳曲线。",
    "拖动只能展示我们走过的位置。": "有限张图只能展示所选位置。",
    "**先向右移动**。开始时合适的框，能一直合适下去吗？":
      "**比较前两幅图**：最初合适的小框，向右移动后还能合适吗？",
    "遇到红线以后，试试“收窄”。半高不变，只把半宽缩小。当前位置可能重新合适了。":
      "看第三幅：遇到红线以后，只缩小半宽、保持半高不变，当前位置又能装得下曲线了。",
    "**收窄后，继续向右移动，看看会不会再次失败。**":
      "**再看第四幅**：保持收窄后的宽度，继续向右移动，小框仍会再次失败。",
    "图中只保留足以比较这几步的观察范围和宽度。到达演示边界后按钮会停止；任意正半宽为什么都会失败，由下面的推导说明。":
      "静态图只展示选定的几个位置和宽度；为什么任意正半宽最终都可能失败，需要下面的推导。",
    "先观察原点处的角点，再向右移动小框。": "比较原点和向右移动后的小框。",
    "在选定范围内把中心向左移动；收窄后继续靠近零。":
      "比较图中由右向左的三个位置；收窄后仍可继续靠近零。",
    "因而水平距离趋于零时，全部位置的高度差都一起变小。图中的状态使用保守界限；如果把框加宽到界限不再足以保证安全，会显示“当前尺度尚不能确认满足要求”，而不会把采样没有发现失败当作证明。":
      "因而水平距离趋于零时，全部位置的高度差都一起变小。静态图仅帮助观察包络线；能否统一控制高度差，需要使用上述数学界限，而不是依赖有限采样。",
    "向左移动小框，收窄后再向左比较。":
      "比较图中由右向左的三个状态：即使收窄小框，继续靠近零仍会遇到困难。",
    "看 $\\sin(x^2)$ 在 $[0,\\infty)$ 上的图像，向右移动小框。":
      "看 $\\sin(x^2)$ 在 $[0,\\infty)$ 上的图像，比较小框沿曲线向右移动的几个状态。",
}

def curve(kind, xx, np):
    with np.errstate(divide='ignore', invalid='ignore'):
        return {
            "sine": lambda x: np.sin(x), "square": lambda x: x*x,
            "root": lambda x: np.sqrt(np.where(x >= 0, x, np.nan)),
            "oscillation": lambda x: np.sin(1/x),
            "damped": lambda x: np.where(x == 0, 0, x*np.sin(1/np.where(x == 0, np.nan, x))),
            "inverse": lambda x: 1/x, "chirp": lambda x: np.sin(x*x),
        }[kind](xx)

def draw(kind: str, output: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import font_manager
    preferred = ['PingFang SC','Noto Sans CJK SC','Noto Sans CJK JP','Microsoft YaHei','SimHei']
    available = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.sans-serif'] = [next((f for f in preferred if f in available), 'DejaVu Sans')]
    plt.rcParams['axes.unicode_minus'] = False

    equation, limits, states = SCENES[kind]
    columns = 2 if len(states) in (2,4) else 3
    rows = (len(states) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(columns*5.3, rows*4.1), squeeze=False)
    fig.patch.set_facecolor('white')
    xmin,xmax,ymin,ymax = limits
    for ax,(center,delta,stage) in zip(axes.flat,states):
        lower = xmin if kind in ('sine','square') else max(0.0005,xmin)
        upper = xmax if kind in ('sine','square','root','inverse','chirp') else min(xmax,1)
        xs = np.linspace(lower,upper,20000 if kind in ('oscillation','damped') else 2800)
        if kind in ('oscillation','inverse'): xs = xs[xs>0]
        yy = curve(kind,xs,np)
        yy = np.where((yy >= ymin-1) & (yy <= ymax+1),yy,np.nan)
        ax.plot(xs,yy,color='#246ea1',linewidth=2.1)
        if kind=='damped':
            xx = np.linspace(0,1,200)
            ax.plot(xx,xx,color='#6b84a0',linestyle='--',linewidth=1.3)
            ax.plot(xx,-xx,color='#6b84a0',linestyle='--',linewidth=1.3)
        f0 = float(curve(kind,np.array([center]),np)[0])
        x1,x2=center-delta,center+delta
        y1,y2=f0-.5,f0+.5
        ax.fill([x1,x2,x2,x1],[y1,y1,y2,y2],color='#56a578',alpha=.09)
        ax.plot([x1,x1],[y1,y2],color='#168357',linewidth=2.5)
        ax.plot([x2,x2],[y1,y2],color='#168357',linewidth=2.5)
        ax.plot([x1,x2],[y1,y1],color='#d54b4b',linewidth=2.4)
        ax.plot([x1,x2],[y2,y2],color='#d54b4b',linewidth=2.4)
        ax.scatter([center],[f0],color='#165d90',s=31,zorder=7)
        ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.grid(alpha=.13)
        ax.set_title(f'{stage}   $x_0$={center:g}   δ={delta:g}',fontsize=11,pad=12)
        ax.set_xlabel('x',fontsize=10);ax.set_ylabel('y',fontsize=10,rotation=0,labelpad=9)
        ax.tick_params(labelsize=8)
        for side in ('top','right'): ax.spines[side].set_visible(False)
    for ax in list(axes.flat)[len(states):]: ax.axis('off')
    fig.suptitle(f'{equation}  |  固定半高 ε=0.5',fontsize=15,y=.99)
    fig.text(.5,.01,'绿色竖边：左右界限   ·   红色横边：上下界限   ·   图示为有限位置的观察，不能代替全域证明',ha='center',fontsize=9,color='#555555')
    fig.tight_layout(rect=[0,.045,1,.95],h_pad=2.3)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,dpi=180,facecolor='white')
    plt.close(fig)

def export(source: Path, out: Path):
    raw=source.read_text(encoding='utf-8')
    head=re.match(r'\A---\s*\n(.*?)\n---\s*\n',raw,re.S)
    if head is None: raise ValueError('Missing MDX frontmatter')
    title_match=re.search(r'^title:\s*(.+?)\s*$',head.group(1),re.M)
    if title_match is None: raise ValueError('Missing title')
    title=title_match.group(1).strip().strip('"\'')
    body=raw[head.end():]
    body=re.sub(r'^import\s+.*?;\s*$', '', body, flags=re.M)
    for before,after in TEXT_ADAPTATIONS.items():
        if before not in body: raise ValueError('Expected adaptation anchor not found: '+before[:55])
        body=body.replace(before,after,1)
    details=re.compile(r'<details>\s*<summary>(.*?)</summary>\s*(.*?)\s*</details>',re.S)
    body,count=details.subn(lambda m:'\n**'+m.group(1).strip()+'**\n\n'+m.group(2).strip()+'\n',body)
    if count!=4: raise ValueError(f'Expected 4 expanded details, got {count}')
    seen=[]
    component=re.compile(r'<ContinuityBox\s+kind="([\w-]+)"\s*/>')
    def replace_component(match):
        kind=match.group(1)
        if kind not in SCENES: raise ValueError('Unknown figure: '+kind)
        if kind in seen: raise ValueError('Duplicate figure: '+kind)
        seen.append(kind)
        return f'![{SCENES[kind][0]} 的固定小框比较图](images/{kind}.png)'
    body=component.sub(replace_component,body)
    if set(seen)!=set(SCENES): raise ValueError(f'Figures differ from expected: {seen}')
    if re.search(r'(?m)^\s*<\/?[A-Za-z][^>]*>',body): raise ValueError('Unconverted HTML / MDX element remains')
    if re.search(r'(?i)(?:https?://|www\.|annouimo|why.notes|github\.com|博客|个人网站)',body):
        raise ValueError('External/personal-site reference found')
    out.mkdir(parents=True,exist_ok=True)
    for kind in seen: draw(kind,out/'images'/f'{kind}.png')
    document='# '+title+'\n\n'+body.strip()+'\n'
    (out/'article.md').write_text(document,encoding='utf-8')
    return out/'article.md'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('src/content/notes/uniform-continuity/index.mdx'))
    parser.add_argument('--output',type=Path,default=Path('dist/zhihu/uniform-continuity'))
    args=parser.parse_args()
    result=export(args.source,args.output)
    print('Wrote:',result)
    for p in sorted((args.output/'images').glob('*.png')):
        print('  image:',p.name,p.stat().st_size,'bytes')

if __name__=='__main__': main()
