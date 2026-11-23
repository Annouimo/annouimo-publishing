import { bindings, defineConfig } from 'cf/config';

export default defineConfig({
  worker: {
    name: 'annouimo-blog',
    compatibilityDate: '2024-03-20',
    env: { ASSETS: bindings.assets() },
    assets: { htmlHandling: 'force-trailing-slash', notFoundHandling: '404-page' },
    workersDev: false,
    previewUrls: false,
  },
});
