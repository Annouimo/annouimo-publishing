import { articles } from '../lib/writing';

const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

export function GET() {
  const site = 'https://blog.annouimo.com';
  const items = articles.map(article => {
    const url = escape(site + article.href);
    const description = escape(article.frontmatter.summary ?? article.frontmatter.description ?? '');
    return `<item><title>${escape(article.title)}</title><link>${url}</link><guid>${url}</guid><pubDate>${new Date(article.frontmatter.date).toUTCString()}</pubDate><description>${description}</description></item>`;
  });
  return new Response(`<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>Annouimo</title><link>${site}</link><description>Annouimo 的博客</description>${items.join('')}</channel></rss>`, {
    headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' },
  });
}
