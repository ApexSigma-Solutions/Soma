<%*
/*
  AI-Powered Task Note Template
  Uses AI for Templater plugin + Templater JS for automation
  
  Requirements:
  - Templater plugin installed
  - AI for Templater plugin installed and configured
  - OpenAI API key (or compatible endpoint)
*/

const tp_r = tp;

// 1. Get the raw title (before user edits)
const rawTitle = tp_r.file.title;

// 2. AI Semantic Analysis - Suggest Area Code
const areaPrompt = `Analyze this task title and suggest a 2-3 letter area code prefix.
Options: OPS (Operations), DEV (Development), INF (Infrastructure), SEC (Security), 
DAT (Data), API (API/Integration), DOC (Documentation), TEST (Testing), UI (User Interface)

Task: "${rawTitle}"
Respond with ONLY the area code, e.g., "DEV" or "OPS"`;

let suggestedArea = "GEN"; // fallback
try {
    suggestedArea = await tp_r.ai.chat(areaPrompt, { model: "gpt-3.5-turbo" });
    suggestedArea = suggestedArea.trim().toUpperCase().slice(0, 3);
} catch (e) {
    tp_r.notify.error("AI area code generation failed, using GEN");
}

// 3. User confirms/edits area code
const areaCode = await tp_r.system.prompt(
    "Area code for UID prefix", 
    suggestedArea, 
    { throwOnCancel: true }
);

// 4. Calculate next sequence number for this area
const folder = tp_r.file.folder(true);
const vault = tp_r.app.vault;
const allFiles = vault.getFiles();
const areaFiles = allFiles.filter(f => 
    f.name.includes(`TN-${areaCode}-`) && 
    f.name.endsWith('.md')
);

// Extract sequence numbers and find max
let maxSeq = 0;
for (const f of areaFiles) {
    const match = f.name.match(new RegExp(`TN-${areaCode}-(\\d+)`));
    if (match) {
        const seq = parseInt(match[1], 10);
        if (seq > maxSeq) maxSeq = seq;
    }
}
const nextSeq = String(maxSeq + 1).padStart(3, '0');

// 5. AI Semantic Slug Generation
const slugPrompt = `Convert this task title into a short URL-safe slug (2-4 words max).
Task: "${rawTitle}"
Rules:
- Use hyphens between words
- Remove articles (a, an, the)
- Remove special characters
- Keep it concise
Respond with ONLY the slug, e.g., "auth-system" or "login-endpoint"`;

let suggestedSlug = rawTitle.toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .slice(0, 40);

try {
    suggestedSlug = await tp_r.ai.chat(slugPrompt, { model: "gpt-3.5-turbo" });
    suggestedSlug = suggestedSlug.trim().toLowerCase().replace(/[^a-z0-9-]/g, '');
} catch (e) {
    // Fallback to basic slugification
}

const uid = `TN-${areaCode}-${nextSeq}`;

// 6. AI Description Generation (optional)
const descPrompt = `Write a 1-sentence description for this task:
Task: "${rawTitle}"`;

const aiDesc = await tp_r.ai.chat(descPrompt, { model: "gpt-3.5-turbo" });

// 7. AI "Done Means Done" Criteria Generation
const criteriaPrompt = `Based on this task, suggest 3-5 concrete "Done Means Done" criteria.
Task: "${rawTitle}"
Format each as "- [ ] description" checklist items. Be specific and actionable.`;

const criteria = await tp_r.ai.chat(criteriaPrompt, { model: "gpt-3.5-turbo" });

-%>
---
uid: <% uid %>
title: <% rawTitle %>
status: draft
created: <% tp_r.date.now("YYYY-MM-DDTHH:mm:ssZ") %>
area: <% areaCode %>
sequence: <% nextSeq %>
pinned: false
warned: false
---

# <% rawTitle %>

<% aiDesc %>

## "Done Means Done" Criteria

<% criteria %>

## Description

## Implementation Notes

## Dependencies

- [[TNP-XXX-000]] - Parent plan (update)

## References

- [[Related-Document]]

## Time Log

| Date | Time Spent | Notes |
|------|------------|-------|
| | | |

---
**🤖 AI-Generated UID:** `<% uid %>`
**Slug:** `<% suggestedSlug %>`
**Generated:** <% tp_r.date.now("YYYY-MM-DD HH:mm") %>

---
**🤖 Lifecycle Transition:** draft → **active**
*Reason:* Manual activation
*Date:* 
