#!/usr/bin/env python3
"""Generate OPML file for importing AI news sources into RSS readers (Folo, Feedly, etc.).

Reads config/sources.yaml and outputs an OPML 2.0 file with feeds organized by category.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_opml(config: dict) -> ET.ElementTree:
    categories = config["categories"]
    sources = config["sources"]

    opml = ET.Element("opml", {"version": "2.0"})
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "AI Info Feeds"
    ET.SubElement(head, "dateCreated").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S UTC"
    )

    body = ET.SubElement(opml, "body")

    # Group sources by category
    grouped: dict[str, list[dict]] = {}
    for src in sources:
        cat = src["category"]
        grouped.setdefault(cat, []).append(src)

    for cat_key, cat_label in categories.items():
        if cat_key not in grouped:
            continue
        cat_outline = ET.SubElement(
            body,
            "outline",
            {"text": cat_label, "title": cat_label},
        )
        for src in grouped[cat_key]:
            feed_attrs = {
                "text": src["name"],
                "title": src["name"],
                "type": "rss",
            }
            if src["rss"]:
                feed_attrs["xmlUrl"] = src["rss"]
                feed_attrs["description"] = src["url"]
            else:
                feed_attrs["xmlUrl"] = src["url"]
                feed_attrs["description"] = f"[NO RSS] {src['url']}"

            ET.SubElement(cat_outline, "outline", feed_attrs)

    return ET.ElementTree(opml)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config" / "sources.yaml"
    output_path = project_root / "config" / "ai-feeds.opml"

    config = load_config(str(config_path))
    tree = build_opml(config)

    # Pretty-print with XML declaration
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
    )
    print(output_path)

    # Stats
    total = len(config["sources"])
    with_rss = sum(1 for s in config["sources"] if s["rss"])
    without_rss = total - with_rss
    print(f"Total sources: {total}")
    print(f"With RSS: {with_rss}")
    print(f"Without RSS: {without_rss}")


if __name__ == "__main__":
    main()
