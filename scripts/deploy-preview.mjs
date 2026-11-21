import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { hash } from 'blake3-wasm';

const accountId = process.env.CLOUDFLARE_ACCOUNT_ID;
const apiToken = process.env.CLOUDFLARE_API_TOKEN;
const assetsDir = process.argv[2];
if (!accountId || !apiToken || !assetsDir) {
  throw new Error('Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN, and pass the built assets directory.');
}

const workerId = '2e831eee93ba41ef864efbaf2d3d213c';
const previewId = '8f80659a843a43d0906dd714cca66f95';
const api = 'https://api.cloudflare.com/client/v4';
const auth = { Authorization: `Bearer ${apiToken}` };

async function walk(dir, base = '') {
  const result = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const relative = path.posix.join(base, entry.name);
    const absolute = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...await walk(absolute, relative));
    else if (entry.isFile()) result.push({ relative, absolute });
  }
  return result;
}

async function request(url, init) {
  const response = await fetch(url, init);
  const json = await response.json();
  if (!response.ok || json.success === false) {
    throw new Error(`Cloudflare API ${response.status}: ${JSON.stringify(json.errors || json)}`);
  }
  return json.result;
}

const files = await walk(assetsDir);
if (!files.length) throw new Error('Build output contains no static assets.');

const byHash = new Map();
const manifest = {};
for (const file of files) {
  const bytes = await readFile(file.absolute);
  // Workers Assets manifests use the first 16 bytes of the BLAKE3 digest.
  const digest = hash(bytes).subarray(0, 16).toString('hex');
  manifest[`/${file.relative}`] = { hash: digest, size: bytes.length };
  byHash.set(digest, { bytes, relative: file.relative });
}

const session = await request(
  `${api}/accounts/${accountId}/workers/scripts/annouimo-blog/assets-upload-session`,
  { method: 'POST', headers: { ...auth, 'Content-Type': 'application/json' }, body: JSON.stringify({ manifest }) },
);
let completionToken = session.jwt;
for (const bucket of session.buckets || []) {
  const boundary = `----annouimo-${crypto.randomUUID()}`;
  const chunks = [];
  for (const digest of bucket) {
    const file = byHash.get(digest);
    if (!file) throw new Error(`Cloudflare requested unknown asset hash: ${digest}`);
    const extension = path.extname(file.relative).toLowerCase();
    const mime = ({ '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.svg': 'image/svg+xml', '.xml': 'application/xml', '.json': 'application/json', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp' })[extension] || 'application/octet-stream';
    chunks.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${digest}"\r\nContent-Type: ${mime}\r\n\r\n${file.bytes.toString('base64')}\r\n`));
  }
  chunks.push(Buffer.from(`--${boundary}--\r\n`));
  const result = await request(
    `${api}/accounts/${accountId}/workers/assets/upload?base64=true`,
    { method: 'POST', headers: { ...auth, Authorization: `Bearer ${session.jwt}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` }, body: Buffer.concat(chunks) },
  );
  completionToken = result.jwt || completionToken;
}
if (!completionToken) throw new Error('Cloudflare did not return a completion token for the asset set.');

const deployment = await request(
  `${api}/accounts/${accountId}/workers/workers/${workerId}/previews/${previewId}/deployments`,
  {
    method: 'POST',
    headers: { ...auth, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      compatibility_date: '2026-11-21',
      assets: { jwt: completionToken, config: { html_handling: 'force-trailing-slash', not_found_handling: '404-page' } },
    }),
  },
);
console.log(JSON.stringify({ deployment: deployment.id, urls: deployment.urls, files: files.length }, null, 2));
