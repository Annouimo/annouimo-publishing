#!/usr/bin/env python3
"""Prepare a Zhihu-ready Markdown using a mainland-facing public image host.

Only uploads the seven non-sensitive teaching figures; never contacts Zhihu.
Use --provider zjf (anonymous original-quality PNG), czl or scdn.
Each uploaded image is downloaded again and integrity-checked before output.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED = {"sine.png", "square.png", "root.png", "oscillation.png",
            "damped.png", "inverse.png", "chirp.png"}
RE_IMAGE = re.compile(r'!\[([^\]\n]*)\]\((images/([a-z]+\.png))\)')
SOURCE_DENY = re.compile(r'(?:annouimo|why[-_ ]?notes|github\.com|https?://|www\.|个人网站|我的博客|阅读原文)', re.I)
PNG = b'\x89PNG\r\n\x1a\n'
HOSTS = {
    'czl': {'img.czl.net', 'i.czl.net'},
    'scdn': {'esaimg.cdn1.vip', 'edgeoneimg.cdn1.vip', 'img.scdn.io'},
    'zjf': {'img.zjf.ai'},
}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NotesZhihuImport/1.0)',
           'Accept': 'application/json'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def multipart(fields, name, content):
    boundary = '----NotesZhihu' + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
                 f'{value}\r\n').encode('utf-8')
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name[0]}"; '
             f'filename="{name[1]}"\r\nContent-Type: image/png\r\n\r\n').encode()
    body += content
    body += f'\r\n--{boundary}--\r\n'.encode()
    return bytes(body), f'multipart/form-data; boundary={boundary}'


def request_bytes(url, body=None, headers=None, limit=15_000_000, timeout=35):
    req = urllib.request.Request(url, data=body, headers=headers or HEADERS,
                                 method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('Response larger than allowed')
            return raw, resp.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        detail = exc.read(320).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code} from {urlsplit(url).netloc}: {detail}') from exc


def checked_url(raw, provider):
    if not isinstance(raw, str):
        raise ValueError('Upload did not return an image URL')
    p = urlsplit(raw.strip())
    if (p.scheme != 'https' or p.hostname not in HOSTS[provider] or p.username
            or p.password or p.port or p.query or p.fragment
            or not re.fullmatch(r'/[A-Za-z0-9_./-]+\.png', p.path)
            or '..' in p.path.split('/')):
        raise ValueError(f'Untrusted or unexpected image URL: {raw!r}')
    return raw.strip()


def upload_png(name, content, provider):
    if provider == 'czl':
        url = 'https://img.czl.net/api/v1/upload'
        fields = {'expired_seconds': '259200'}
        filefield = 'file'
    elif provider == 'scdn':
        url = 'https://img.scdn.io/api/v1.php'
        fields = {'outputFormat': 'png', 'cdn_domain': 'esaimg.cdn1.vip'}
        filefield = 'image'
    elif provider == 'zjf':
        # Anonymous public upload, 5 MiB per file and 10 images / IP / day.
        # Explicitly disable server compression/watermarks; require original PNG fidelity.
        url = 'https://zjf.ai/api/upload'
        fields = {'compress': 'false', 'watermark': 'false', 'visibility': 'public'}
        filefield = 'file'
    else:
        raise ValueError('Unknown provider')
    body, mime = multipart(fields, (filefield, name), content)
    raw, _ = request_bytes(url, body, {**HEADERS, 'Content-Type': mime})
    try:
        data = json.loads(raw.decode('utf-8'))
    except ValueError as exc:
        raise ValueError('Upload response was not JSON: ' + raw[:250].decode('utf-8', errors='replace')) from exc
    if provider == 'czl':
        if not data.get('status'):
            raise RuntimeError(f"CZL refused upload: {str(data.get('message'))[:180]}")
        result = data.get('data') or {}
        link = (result.get('links') or {}).get('url')
    else:
        if not data.get('success'):
            raise RuntimeError(f"{provider} refused upload: {str(data.get('message') or data.get('error'))[:180]}")
        link = data.get('url') or (data.get('data') or {}).get('url')
    return checked_url(link, provider)


def verify_png(url, original, provider):
    checked_url(url, provider)
    received, mime = request_bytes(url, limit=12_000_000)
    if not received.startswith(PNG):
        raise ValueError(f'URL does not return a PNG: {url} (type={mime})')
    if sha(received) == sha(original):
        return 'identical bytes'
    # Some image hosts recompress losslessly; identical RGBA pixels are acceptable.
    from PIL import Image, ImageChops
    a = Image.open(io.BytesIO(original)).convert('RGBA')
    b = Image.open(io.BytesIO(received)).convert('RGBA')
    if a.size != b.size or ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox() is not None:
        raise ValueError(f'Uploaded image differs in pixel content: {url}')
    return 'identical pixels'


def fit_guest_limit(name, png_bytes):
    """Palettize unusually large charts; preserve their full pixel dimensions."""
    if len(png_bytes) <= 100_000:
        return png_bytes
    from PIL import Image
    image = Image.open(io.BytesIO(png_bytes)).convert('RGB')
    palette = image.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE)
    output = io.BytesIO()
    palette.save(output, format='PNG', optimize=True, compress_level=9)
    result = output.getvalue()
    if len(result) > 100_000:
        raise ValueError(f'Image still exceeds anonymous upload limit: {name} ({len(result)} bytes)')
    print(f'Compressed {name}: {len(png_bytes)} -> {len(result)} bytes; dimensions unchanged', flush=True)
    return result


def load_source(path):
    source = path.read_text(encoding='utf-8')
    if SOURCE_DENY.search(source):
        raise ValueError('Input Markdown contains external URLs or personal site references')
    matches = list(RE_IMAGE.finditer(source))
    names = [m.group(3) for m in matches]
    if len(names) != 7 or set(names) != EXPECTED or len(set(names)) != 7:
        raise ValueError(f'Expected seven teaching images in Markdown: {names!r}')
    if len(re.findall(r'!\[', source)) != 7:
        raise ValueError('Unknown image format in Markdown')
    files = {}
    for name in names:
        content = (path.parent / 'images' / name).read_bytes()
        if len(content) > 10_000_000 or not content.startswith(PNG):
            raise ValueError('Bad input PNG ' + name)
        files[name] = content
    return source, files


def export(args):
    path = args.input.resolve()
    output = (args.output or path.with_name('article.zhihu-cn.md')).resolve()
    if path == output:
        raise ValueError('Refusing to overwrite source Markdown')
    source, images = load_source(path)
    if args.provider == 'czl':
        images = {name: fit_guest_limit(name, content) for name, content in images.items()}
    else:
        # Preserve the full original image on hosts that allow much larger uploads.
        # No palette quantization or downscaling.
        if args.provider == 'zjf' and any(len(content) > 5_000_000 for content in images.values()):
            raise ValueError('ZJF anonymous upload limit is 5 MB per image')
    print(f'Input validated: {len(images)} PNGs, {source.count("$$") // 2} block equations', flush=True)
    if not args.upload:
        print('Dry run only. Nothing uploaded.')
        return
    manifest_path = path.with_name('hosted-images-' + args.provider + '.json')
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('provider') != args.provider:
            raise ValueError('Unexpected manifest provider')
    else:
        manifest = {'provider': args.provider, 'images': {}}

    urls = {}
    uploads_this_batch = 0
    for name in sorted(images):
        record = manifest['images'].get(name, {})
        if record.get('sha256') == sha(images[name]):
            try:
                verify_png(record['url'], images[name], args.provider)
                urls[name] = record['url']
                print('Verified existing:', name, flush=True)
                continue
            except (KeyError, ValueError, OSError, RuntimeError):
                pass
        if args.provider == 'czl' and uploads_this_batch >= 5:
            print('CZL anonymous rate limit: waiting 65 s before next batch...', flush=True)
            time.sleep(65)
            uploads_this_batch = 0
        print('Uploading:', name, flush=True)
        for retry in range(2):
            try:
                link = upload_png(name, images[name], args.provider)
                uploads_this_batch += 1
                break
            except RuntimeError as exc:
                if args.provider != 'czl' or retry or ('每分钟' not in str(exc) and 'HTTP 429' not in str(exc)):
                    raise
                print('CZL reported rate limit; waiting 65 s and retrying...', flush=True)
                time.sleep(65)
                uploads_this_batch = 0
        integrity = verify_png(link, images[name], args.provider)
        print('Verified:', name, integrity, link, flush=True)
        urls[name] = link
        manifest['images'][name] = {'url': link, 'sha256': sha(images[name]),
                                    'checked_at': datetime.now(timezone.utc).isoformat()}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # In particular, SCDN documents 5 uploads / 5 s for a given IP.
        time.sleep(1.25)

    rewritten = RE_IMAGE.sub(lambda m: f'![{m.group(1)}]({urls[m.group(3)]})', source)
    if len(re.findall(r'!\[[^\]\n]*\]\(https://', rewritten)) != 7:
        raise ValueError('Mismatch after link replacement')
    # Stronger check: replace each exact remote URL by original local link.
    reverse = dict((value, name) for name, value in urls.items())
    check = re.sub(r'!\[([^\]\n]*)\]\((https://[^)]+)\)',
                   lambda m: f'![{m.group(1)}](images/{reverse[m.group(2)]})', rewritten)
    if check != source or SOURCE_DENY.search(check):
        raise ValueError('Markdown prose or math changed during conversion')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rewritten, encoding='utf-8')
    print(f'SUCCESS: {args.provider}, 7 pictures verified, wrote {output}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('dist/zhihu/uniform-continuity/article.md'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--provider', choices=('zjf', 'czl', 'scdn'), default='czl')
    parser.add_argument('--upload', action='store_true', help='Explicitly upload publicly visible teaching PNGs')
    args = parser.parse_args()
    try:
        export(args)
    except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
        print('FAILED:', exc, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
