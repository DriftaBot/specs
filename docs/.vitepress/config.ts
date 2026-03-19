import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DriftaBot Registry',
  description: 'The central, always-up-to-date repository for public API specifications — with automatic breaking change detection.',
  base: '/registry/',

  themeConfig: {
    logo: '/logo.png',

    nav: [
      { text: 'Guide', link: '/how-it-works' },
      { text: 'Status', link: '/status' },
      { text: 'Agent ↗', link: 'https://github.com/marketplace/actions/driftabot-agent', target: '_blank' },
      { text: 'GitHub', link: 'https://github.com/DriftaBot/registry' },
    ],

    sidebar: [
      {
        text: 'Overview',
        items: [
          { text: 'How It Works', link: '/how-it-works' },
          { text: 'Registry Status', link: '/status' },
        ],
      },
      {
        text: 'Providers',
        items: [
          { text: 'Add a Provider', link: '/providers' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'Local Development', link: '/local-dev' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/DriftaBot/registry' },
    ],

    footer: {
      message: 'Released under the MIT License.',
    },
  },
})
