import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DriftaBot Specs',
  description: 'The central, always-up-to-date repository for public API specifications — with automatic breaking change detection and consumer notifications.',
  base: '/specs/',

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/how-it-works' },
      { text: 'Engine ↗', link: 'https://driftabot.github.io/engine', target: '_blank' },
      { text: 'GitHub', link: 'https://github.com/DriftaBot/specs' },
    ],

    sidebar: [
      {
        text: 'Overview',
        items: [
          { text: 'How It Works', link: '/how-it-works' },
        ],
      },
      {
        text: 'For API Providers',
        items: [
          { text: 'Add a Provider', link: '/providers' },
        ],
      },
      {
        text: 'For API Consumers',
        items: [
          { text: 'Register for Notifications', link: '/consumers' },
          { text: 'Consumer Issues', link: '/consumer-issues' },
          { text: 'Check Your Repo', link: '/check-consumer' },
        ],
      },
      {
        text: 'Reference',
        items: [
          { text: 'Drift Logs', link: '/drift-logs' },
          { text: 'Local Development', link: '/local-dev' },
        ],
      },
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/DriftaBot/specs' },
    ],

    footer: {
      message: 'Released under the MIT License.',
    },
  },
})
