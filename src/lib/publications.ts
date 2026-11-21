import { articles } from './writing';
import { notes } from './notes';

export const publications = [
  ...articles,
  ...notes.map(note => ({
    title: note.frontmatter.title,
    href: `/notes/${note.slug}/`,
    section: 'notes' as const,
    frontmatter: note.frontmatter,
  })),
].sort((a, b) => b.frontmatter.date.localeCompare(a.frontmatter.date));
