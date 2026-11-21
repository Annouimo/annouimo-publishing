import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkCallouts from './scripts/remark-callouts.mjs';

import cloudflare from '@astrojs/cloudflare';

const remarkPlugins = [remarkMath, remarkCallouts];
const rehypePlugins = [rehypeKatex];

export default defineConfig({
  site: 'https://blog.annouimo.com',
  output: 'static',
  session: false,
  trailingSlash: 'always',
  integrations: [mdx({ remarkPlugins, rehypePlugins })],
  markdown: {
    processor: unified({ remarkPlugins, rehypePlugins }),
  },
  adapter: cloudflare({ imageService: 'passthrough', prerenderEnvironment: 'node' }),
});
