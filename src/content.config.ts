import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const baseSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  pubDatetime: z.coerce.date(),
  modDatetime: z.coerce.date().optional(),
  tags: z.array(z.string()).default(["AI"]),
  draft: z.boolean().default(false),
});

const daily = defineCollection({
  loader: glob({
    pattern: "**/202[0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md",
    base: "./daily-reports",
    generateId: ({ entry }) => {
      // e.g. "2026/06/2026-06-02.md" → "2026-06-02"
      const parts = entry.split("/");
      return parts[parts.length - 1]!.replace(".md", "");
    },
  }),
  schema: baseSchema.extend({
    type: z.literal("daily").default("daily"),
  }),
});

const monthly = defineCollection({
  loader: glob({
    pattern: "**/*-monthly.md",
    base: "./daily-reports",
    generateId: ({ entry }) => {
      const parts = entry.split("/");
      return parts[parts.length - 1]!.replace(".md", "");
    },
  }),
  schema: baseSchema.extend({
    type: z.literal("monthly").default("monthly"),
  }),
});

const trending = defineCollection({
  loader: glob({
    pattern: "**/trending/*.md",
    base: "./daily-reports",
    generateId: ({ entry }) => {
      const parts = entry.split("/");
      return parts[parts.length - 1]!.replace(".md", "");
    },
  }),
  schema: baseSchema.extend({
    type: z.literal("trending").default("trending"),
  }),
});

export const collections = { daily, monthly, trending };
