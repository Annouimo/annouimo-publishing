#!/usr/bin/env node
/**
 * Screenshot the real Astro teaching components, not re-drawn approximations.
 * This reads an isolated localhost-only capture page and writes 28 high-DPI
 * PNGs plus associated figure headings/captions. No uploads or site links.
 *
 * Usage:
 *   ZHIHU_CAPTURE_URL=http://127.0.0.1:4321/zhihu-capture-offline \
 *   node scripts/render-zhihu-maxwell.mjs
 */
import { chromium } from 'playwright-core';
import { access, mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

const figureKinds = [
  'field', 'differential-plane', 'potential-slopes', 'potential',
  'flux-plane', 'flux', 'divergence', 'volume-cancel', 'charge',
  'curl', 'cancellation', 'forms', 'mixed-partials', 'boundary-square',
  'gauss-sphere', 'gauss-cone', 'coupling', 'wave-shift'
];
const labStates = {
  field: ['constant', 'source', 'rotation', 'both', 'saddle'],
  capacitor: ['s1', 's2'],
  wave: ['phase-0', 'phase-1', 'phase-2'],
};
const output = path.resolve(process.env.ZHIHU_OUTPUT || 'dist/zhihu/maxwell-equations');
const imageDir = path.join(output, 'images');
const url = process.env.ZHIHU_CAPTURE_URL || 'http://127.0.0.1:4321/zhihu-capture-offline';

function getChrome() {
  if (process.env.CHROME_BIN) return process.env.CHROME_BIN;
  for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    try {
      const location = execFileSync('which', [name], {encoding: 'utf8'}).trim();
      if (location) return location;
    } catch { /* try next */ }
  }
  throw new Error('Cannot find Chrome/Chromium. Set CHROME_BIN.');
}
async function safeShot(locator, filename) {
  if (await locator.count() !== 1) throw new Error('Expected one SVG for ' + filename);
  await locator.screenshot({path: path.join(imageDir, filename), animations: 'disabled', timeout: 25000});
  if ((await stat(path.join(imageDir, filename))).size < 2500) {
    throw new Error('Unexpectedly tiny exported screenshot: ' + filename);
  }
}
function textOrThrow(value, name) {
  const text = (value || '').trim().replace(/\s+/g, ' ');
  if (!text) throw new Error('Missing descriptive text: ' + name);
  return text;
}

await mkdir(imageDir, {recursive: true});
const browser = await chromium.launch({
  headless: true,
  executablePath: getChrome(),
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
try {
  const context = await browser.newContext({
    viewport: {width: 1280, height: 900},
    deviceScaleFactor: 2,
    colorScheme: 'light',
    locale: 'zh-CN'
  });
  const page = await context.newPage();
  page.on('pageerror', error => {
    process.stderr.write('Browser error: ' + error.message + '\n');
  });
  const response = await page.goto(url, {waitUntil: 'networkidle', timeout: 90000});
  if (!response || !response.ok()) throw new Error('Capture page HTTP failure: ' + response?.status());
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => {
    const field = document.querySelector('[data-capture="lab-field"] svg[data-plot]');
    const wave = document.querySelector('[data-capture="lab-wave"] svg[data-wave]');
    return field && field.childElementCount > 10 && wave && wave.childElementCount > 10;
  }, null, {timeout: 30000});
  // Astro dev can show a Vite diagnostics overlay for unrelated hot reloads.
  // Capture its text for review, then hide it so it cannot obscure the export.
  const overlays = await page.evaluate(() => [...document.querySelectorAll('vite-error-overlay')]
    .map(el => el.shadowRoot?.textContent?.slice(0, 1500) || 'overlay without readable text'));
  for (const item of overlays) process.stderr.write('Vite overlay: ' + item + '\n');
  await page.addStyleTag({content: 'vite-error-overlay, astro-dev-toolbar, astro-dev-toolbar-dialog { display: none !important; pointer-events: none !important }'});
  await page.evaluate(() => {
    document.querySelectorAll('vite-error-overlay, astro-dev-toolbar, astro-dev-toolbar-dialog')
      .forEach(el => el.remove());
  });

  const metadata = {figures: {}, labs: {}};
  for (const kind of figureKinds) {
    const root = page.locator('[data-capture="teaching-' + kind + '"]');
    if (await root.count() !== 1) throw new Error('Missing TeachingFigure: ' + kind);
    const fig = root.locator('figure.teaching-figure');
    const title = textOrThrow(await fig.locator('.figure-top h3').innerText(), kind + ' title');
    const caption = textOrThrow(await fig.locator('figcaption').innerText(), kind + ' caption');
    await safeShot(fig.locator('svg').first(), 'figure-' + kind + '.png');
    metadata.figures[kind] = {title, caption};
    process.stdout.write('Figure: ' + kind + ' | ' + title + '\n');
  }

  const field = page.locator('[data-capture="lab-field"]');
  const fieldStates = [];
  const fieldFootnote = textOrThrow(await field.locator('.lab-footnote').innerText(), 'field footnote');
  for (const id of labStates.field) {
    const button = field.locator('button[data-field="' + id + '"]');
    const label = textOrThrow(await button.innerText(), 'field ' + id);
    await button.evaluate(element => element.click());
    const result = textOrThrow(await field.locator('[data-result]').innerText(), 'field result');
    await safeShot(field.locator('svg[data-plot]'), 'lab-field-' + id + '.png');
    fieldStates.push({id, label, result});
    process.stdout.write('Field lab: ' + id + '\n');
  }
  metadata.labs.field = {states: fieldStates, footnote: fieldFootnote};

  const capacitor = page.locator('[data-capture="lab-capacitor"]');
  const capacitorFootnote = textOrThrow(await capacitor.locator('.lab-footnote').innerText(), 'capacitor footnote');
  const capacitorStates = [];
  for (const [id, which] of [['s1','one'], ['s2','two']]) {
    const button = capacitor.locator('button[data-surface="' + which + '"]');
    const label = textOrThrow(await button.innerText(), 'capacitor ' + id);
    await button.evaluate(element => element.click());
    const result = textOrThrow(await capacitor.locator('[data-result]').innerText(), 'capacitor result');
    await safeShot(capacitor.locator('svg.lab-svg'), 'lab-capacitor-' + id + '.png');
    capacitorStates.push({id, label, result});
    process.stdout.write('Capacitor lab: ' + id + '\n');
  }
  metadata.labs.capacitor = {states: capacitorStates, footnote: capacitorFootnote};

  const wave = page.locator('[data-capture="lab-wave"]');
  const waveFootnote = textOrThrow(await wave.locator('.lab-footnote').innerText(), 'wave footnote');
  const waveStates = [];
  const slider = wave.locator('input[data-phase]');
  for (const [id, phase] of [['phase-0', '0'], ['phase-1', '1.55'], ['phase-2', '3.15']]) {
    await slider.evaluate((input, value) => {
      input.value = value;
      input.dispatchEvent(new Event('input', {bubbles: true}));
    }, phase);
    await page.waitForFunction(
      expected => document.querySelector('[data-capture="lab-wave"] [data-time]')?.textContent === expected,
      Number(phase).toFixed(2)
    );
    await safeShot(wave.locator('svg[data-wave]'), 'lab-wave-' + id + '.png');
    waveStates.push({
      id,
      label: '时刻参数 ' + Number(phase).toFixed(2),
      result: '三维图中 E 沿 y 方向、B 沿 z 方向振荡，波沿 x 方向传播；比较不同相位时波峰的位置。'
    });
    process.stdout.write('Wave lab: ' + id + '\n');
  }
  metadata.labs.wave = {states: waveStates, footnote: waveFootnote};
  const total = Object.keys(metadata.figures).length +
    Object.values(metadata.labs).reduce((n, lab) => n + lab.states.length, 0);
  if (total !== 28) throw new Error('Expected 28 exported PNGs, got ' + total);
  await writeFile(path.join(output, 'screenshots.json'), JSON.stringify(metadata, null, 2) + '\n', 'utf8');
  process.stdout.write('SUCCESS: 18 source SVGs + 10 lab states = 28 screenshots; titles/captions recorded\n');
  await context.close();
} finally {
  await browser.close();
}
