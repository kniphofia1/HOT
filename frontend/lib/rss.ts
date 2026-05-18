import type { TimelinePage } from "./api";

export function renderTimelineRss(title: string, link: string, description: string, feed: TimelinePage): string {
  const items = feed.items
    .map(
      (item) => `<item>
  <title>${xml(item.displayTitle)}</title>
  <link>${xml(item.url || `${link}/events/${item.id}`)}</link>
  <guid>${xml(item.id)}</guid>
  <pubDate>${new Date(item.publishedAt || item.displayedAt || item.seenAt || Date.now()).toUTCString()}</pubDate>
  <description>${xml(item.displaySummary || item.reason)}</description>
</item>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>${xml(title)}</title>
  <link>${xml(link)}</link>
  <description>${xml(description)}</description>
${items}
</channel>
</rss>`;
}

function xml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
