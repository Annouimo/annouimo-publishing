import type { MarkdownInstance } from 'astro';

interface Frontmatter {
  title: string;
  subtitle?: string;
  date: string;
  lastmod: string;
  summary?: string;
  description?: string;
}

export const sections = { blog: '随笔', research: '研究', society: '社会', about: '个人经历' } as const;

export const articles = Object.entries(import.meta.glob<MarkdownInstance<Frontmatter>>(
  '../content/writing/*/*.md', { eager: true },
)).map(([file, article]) => {
  const [, section, slug] = file.match(/\/([^/]+)\/([^/]+)\.md$/)!;
  const { title, subtitle } = article.frontmatter;
  return { ...article, section: section as keyof typeof sections, slug,
    title: subtitle ? `${title}：${subtitle}` : title, href: `/${section}/${slug}/` };
}).sort((a, b) => b.frontmatter.date.localeCompare(a.frontmatter.date));
