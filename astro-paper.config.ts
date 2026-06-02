import { defineAstroPaperConfig } from "./src/types/config";

export default defineAstroPaperConfig({
  site: {
    url: "https://jianzhnie.github.io/ai-news-daily/",
    title: "AI News Daily",
    description:
      "AI 领域每日信息聚合 — 日报、月报、GitHub Trending 中文解读",
    author: "AI News Bot",
    lang: "zh",
    timezone: "Asia/Shanghai",
  },
  posts: {
    perPage: 10,
    perIndex: 6,
  },
  features: {
    lightAndDarkMode: true,
    dynamicOgImage: false,
    showArchives: true,
    showBackButton: true,
    editPost: { enabled: false },
    search: false,
  },
  socials: [
    {
      name: "github",
      url: "https://github.com/jianzhnie/AI-News-Daily",
      linkTitle: "GitHub",
    },
    { name: "rss", url: "/rss.xml", linkTitle: "RSS" },
  ],
  shareLinks: [],
});
