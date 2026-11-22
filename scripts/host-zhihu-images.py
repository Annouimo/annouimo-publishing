#!/usr/bin/env python3
"""Build a standalone Zhihu Markdown with anonymous, temporary HTTPS image URLs.

This script never publishes to Zhihu. Network upload is opt-in (--upload), uses\n0x0.st by default (Litterbox remains optional), and checks downloaded image bytes.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

HOST_URL = 'https://litterbox.catbox.moe/resources/internals/api.php'
IMAGE_HOSTS = {'litterbox': 'files.catbox.moe', '0x0': '0x0.st'}
ZEROX_URL = 'https://0x0.st'
EXPECTED = {'sine.png', 'square.png', 'root.png', 'oscillation.png',
            'damped.png', 'inverse.png', 'chirp.png'}
IMAGE_RE = re.compile(r'!\[([^\]\n]*)\]\((images/([a-z]+\.png))\)')
PRIVATE_RE = re.compile(r'(?i)(?:annouimo|why[-_ ]?notes|https?://(?!files\.catbox\.moe)|github\.com|个人网站|我的博客|阅读原文)')
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.now(timezone.utc)


def check_url(url, provider):
    p = urlsplit(url)
    if (p.scheme != 'https' or p.hostname != IMAGE_HOSTS[provider] or p.username or
            p.password or p.port or p.query or p.fragment or
            not re.fullmatch(r'/[A-Za-z0-9_-]+\.png', p.path)):
        raise ValueError(f'Unexpected image-host URL: {url!r}')
    return url


def source_images(markdown, directory):
    if PRIVATE_RE.search(markdown):
        raise ValueError('Source contains a possible personal-site reference or external URL')
    matches = list(IMAGE_RE.finditer(markdown))
    names = [m.group(3) for m in matches]
    if len(matches) != len(EXPECTED) or set(names) != EXPECTED:
        raise ValueError(f'Expected 7 known local images, found: {names}')
    if re.search(r'!\[[^\]]*\]\((?!images/)[^)]*\)', markdown):
        raise ValueError('Unrecognized image link; refusing partial conversion')
    files = {}
    for name in names:
        path = directory / 'images' / name
        data = path.read_bytes()
        if not data.startswith(PNG_MAGIC) or len(data) > 10_000_000:
            raise ValueError(f'Image is not a valid, reasonably sized PNG: {path}')
        files[name] = data
    return files


def multipart_png(filename, payload, expiry):
    boundary = '----ZhihuTemp' + uuid.uuid4().hex
    def field(key, val):
        return (f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n').encode()
    body = field('reqtype', 'fileupload') + field('time', expiry)
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="fileToUpload"; '
             f'filename="{filename}"\r\nContent-Type: image/png\r\n\r\n').encode()
    body += payload + f'\r\n--{boundary}--\r\n'.encode()
    return body, f'multipart/form-data; boundary={boundary}'


def multipart_0x0(name, payload):
    boundary = '----ZhihuTemp' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; '
            f'name="file"; filename="{name}"\r\n'
            f'Content-Type: image/png\r\n\r\n').encode()
    body += payload + f'\r\n--{boundary}--\r\n'.encode()
    return body, f'multipart/form-data; boundary={boundary}'


def upload_image(name, data, expiry, provider):
    if provider == '0x0':
        body, content_type = multipart_0x0(name, data)
        endpoint = ZEROX_URL
    else:
        body, content_type = multipart_png(name, data, expiry)
        endpoint = HOST_URL
    request = urllib.request.Request(endpoint, data=body,
        headers={'Content-Type': content_type, 'User-Agent': 'ZhihuNotesOfflineExport/1.0'},
        method='POST')
    with urllib.request.urlopen(request, timeout=50) as response:
        url = response.read(1024).decode('utf-8').strip()
    return check_url(url, provider)


def verify_image(url, original, provider):
    check_url(url, provider)
    request = urllib.request.Request(url, headers={'User-Agent': 'ZhihuNotesOfflineExport/1.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read(len(original) + 1)
    if digest(data) != digest(original):
        raise ValueError(f'Uploaded image did not round-trip exactly: {url}')


def read_manifest(path, provider):
    if path.exists():
        content = json.loads(path.read_text(encoding='utf-8'))
        if content.get('provider') != provider or not isinstance(content.get('images'), dict):
            raise ValueError('Unknown manifest format')
        return content
    return {'provider': provider, 'images': {}}


def save_manifest(path, manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def active_record(record, data, provider, min_hours=1):
    try:
        expires = datetime.fromisoformat(record['expires_at'])
        return (digest(data) == record['sha256'] and
                expires > utc_now() + timedelta(hours=min_hours) and
                bool(check_url(record['url'], provider)))
    except (TypeError, KeyError, ValueError):
        return False


def rewrite(markdown, urls, provider):
    def replacement(match):
        name = match.group(3)
        return f'![{match.group(1)}]({check_url(urls[name], provider)})'
    result = IMAGE_RE.sub(replacement, markdown)
    if result.count('https://' + IMAGE_HOSTS[provider] + '/') != 7:
        raise ValueError('Incorrect number of hosted image links')
    without_images = re.sub(r'!\[[^\]\n]*\]\((?:images/[^)]+|https://(?:files\.catbox\.moe|0x0\.st)/[^)]+)\)', '', result)
    if PRIVATE_RE.search(without_images) or re.search(r'!\[[^\]]*\]\(images/', result):
        raise ValueError('Unconverted links or personal-site reference remains')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('dist/zhihu/uniform-continuity/article.md'))
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--provider', choices=('0x0','litterbox'), default='0x0')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upload', action='store_true', help='Upload seven images anonymously; external network access')
    mode.add_argument('--reuse', action='store_true', help='Reuse already uploaded images from a manifest')
    parser.add_argument('--expiry', choices=('1h', '12h', '24h', '72h'), default='72h')
    args = parser.parse_args(argv)
    source = args.input.resolve()
    out = (args.output or source.with_name('article.zhihu.md')).resolve()
    if source == out:
        parser.error('--output must not overwrite original Markdown')
    raw = source.read_text(encoding='utf-8')
    files = source_images(raw, source.parent)
    if not (args.upload or args.reuse):
        print(f'Checked {len(files)} local PNG images and article Markdown; nothing uploaded.')
        print(f'Next: python3 {Path(__file__).name} --input "{source}" --upload')
        return 0
    manifest_path = source.with_name('hosted-images-' + args.provider + '.json')
    manifest = read_manifest(manifest_path, args.provider)
    urls = {}
    for name in sorted(files):
        data = files[name]
        record = manifest['images'].get(name)
        if not (record and active_record(record, data, args.provider)):
            if args.reuse:
                raise ValueError(f'Missing or expired uploaded URL for {name}; run with --upload')
            print(f'Uploading {name}...', flush=True)
            url = upload_image(name, data, args.expiry, args.provider)
            verify_image(url, data, args.provider)
            # 0x0.st retains small files longer than the immediate test horizon.
            # Do not promise a specific expiry; require fresh validation on reuse.
            expire_time = utc_now() + timedelta(hours=int(args.expiry[:-1]))
            manifest['images'][name] = {
                'url': url, 'sha256': digest(data), 'expires_at': expire_time.isoformat()
            }
            save_manifest(manifest_path, manifest)
        else:
            url = record['url']
            verify_image(url, data)
            print(f'Reusing verified {name}', flush=True)
        urls[name] = url
    hosted_md = rewrite(raw, urls, args.provider)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(hosted_md, encoding='utf-8')
    print(f'OK: {len(urls)} remote PNG images verified; wrote {out}')
    print('IMPORTANT: third-party URLs may expire. Confirm Zhihu has rehosted them BEFORE publishing.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TimeoutError) as e:
        print(f'Export failed: {e}', file=sys.stderr)
        sys.exit(1)
