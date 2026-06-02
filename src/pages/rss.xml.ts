import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import config from "@/config";

const daily = await getCollection("daily");
const monthly = await getCollection("monthly");
const trending = await getCollection("trending");

const allEntries = [...daily, ...monthly, ...trending].sort(
  (a, b) => b.data.pubDatetime.getTime() - a.data.pubDatetime.getTime()
);

export const GET = () =>
  rss({
    title: config.site.title,
    description: config.site.description,
    site: config.site.url,
    items: allEntries.map(entry => ({
      title: entry.data.title,
      description: entry.data.description || "",
      pubDate: entry.data.pubDatetime,
      link: `/${entry.collection}/${entry.id}/`,
    })),
  });
