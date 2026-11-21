import type { MarkdownInstance } from 'astro';
import { sectionLabels } from './sections';

interface Frontmatter {
  title: string;
  subtitle?: string;
  date: string;
  lastmod: string;
  summary?: string;
  description?: string;
}

export const { notes: _notes, ...sections } = sectionLabels;

export const articles = Object.entries(import.meta.glob<MarkdownInstance<Frontmatter>>(
  '../content/writing/*/*.md', { eager: true },
)).map(([file, article]) => {
  const [, section, slug] = file.match(/\/([^/]+)\/([^/]+)\.md$/)!;
  const { title, subtitle } = article.frontmatter;
  return { ...article, section: section as keyof typeof sections, slug,
    title: subtitle ? `${title}：${subtitle}` : title, href: `/${section}/${slug}/` };
}).sort((a, b) => b.frontmatter.date.localeCompare(a.frontmatter.date));
