export const dynamic = "force-dynamic";

export async function GET() {
  return new Response(skill, {
    headers: { "Content-Type": "text/markdown; charset=utf-8" },
  });
}

const skill = `---
name: aihot-local
description: Query the local AI HOT intelligence radar for selected items, all items, industry digests, and keyword searches.
---

# AI HOT Local Skill

Use this skill when the user asks about recent intelligence, selected items, all updates, industry digests, or keyword-specific intelligence from this local radar.

## Endpoints

- Selected feed: \`GET http://localhost:8000/api/public/items?mode=selected\`
- All feed: \`GET http://localhost:8000/api/public/items?mode=all\`
- Industry index: \`GET http://localhost:8000/api/public/industries\`
- Industry digest: \`GET http://localhost:8000/api/public/industries/{industry}\`

## Routing

- Default broad questions should call selected feed.
- Questions containing "全部", "完整", "所有", or "全量" should call all feed.
- Questions containing "日报" should call industry index first, then the matching industry digest.
- Keyword questions should pass \`q=<keyword>\`.
- Category questions can pass \`category=ai-models|ai-products|industry|paper|tip\`.
- Industry questions can pass \`industry=ai|semiconductor|embodied_ai|energy|technology|products\`.

## Output

Always include title, source, score, short summary, reason, and source URL when available.
`;
