<%*
/*
  AI-Powered Task-Note-Plan Template
  Uses AI for Templater plugin + Templater JS for automation
  
  Requirements:
  - Templater plugin installed
  - AI for Templater plugin installed and configured
  - OpenAI API key (or compatible endpoint)
*/

const tp_r = tp;

// 1. Get the raw title
const rawTitle = tp_r.file.title;

// 2. AI Semantic Analysis - Suggest Area Code
const areaPrompt = `Analyze this project/plan title and suggest a 2-3 letter area code prefix.
Options: OPS (Operations), DEV (Development), INF (Infrastructure), SEC (Security), 
DAT (Data), API (API/Integration), DOC (Documentation), TEST (Testing), UI (User Interface)

Project: "${rawTitle}"
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

// 4. Calculate next sequence number for this area (TNPs)
const folder = tp_r.file.folder(true);
const vault = tp_r.app.vault;
const allFiles = vault.getFiles();
const areaFiles = allFiles.filter(f => 
    f.name.includes(`TNP-${areaCode}-`) && 
    f.name.endsWith('.tnp.md')
);

// Extract sequence numbers and find max
let maxSeq = 0;
for (const f of areaFiles) {
    const match = f.name.match(new RegExp(`TNP-${areaCode}-(\\d+)`));
    if (match) {
        const seq = parseInt(match[1], 10);
        if (seq > maxSeq) maxSeq = seq;
    }
}
const nextSeq = String(maxSeq + 1).padStart(3, '0');

// 5. AI Semantic Slug Generation
const slugPrompt = `Convert this project title into a short URL-safe slug (2-4 words max).
Project: "${rawTitle}"
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
    // Fallback
}

const uid = `TNP-${areaCode}-${nextSeq}`;

// 6. AI High-Level Objective Generation
const objPrompt = `Write a clear high-level objective for this project:
Project: "${rawTitle}"
Respond with 1-2 sentences describing the goal.`;

const objective = await tp_r.ai.chat(objPrompt, { model: "gpt-3.5-turbo" });

// 7. AI "Done Means Done" Criteria Generation
const criteriaPrompt = `Generate 4-6 concrete "Done Means Done" exit criteria for this project.
Project: "${rawTitle}"
Format as bullet points. Be specific and measurable.`;

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

<% objective %>

## 1. High-Level Objective

<% objective %>

## 2. "Done Means Done" Criteria

<% criteria %>

## 3. Task Breakdown

This is the granular, tactical list of work. **Every task here MUST use the `- [ ]` or `- [x]` syntax.**

- [ ] [<% `TN-${areaCode}-${String(parseInt(nextSeq)*100+1).padStart(3,'0')}` %>] First major task
- [ ] [<% `TN-${areaCode}-${String(parseInt(nextSeq)*100+2).padStart(3,'0')}` %>] Second major task
- [ ] [<% `TN-${areaCode}-${String(parseInt(nextSeq)*100+3).padStart(3,'0')}` %>] Third major task

## 4. Notes & Context

**Related Resources:**
- [[Reference-Document]]

**Implementation Notes:**
<!-- AI-generated notes placeholder -->
<!-- Replace with your implementation details -->

---
**🤖 AI-Generated UID:** `<% uid %>`
**Slug:** `<% suggestedSlug %>`
**Generated:** <% tp_r.date.now("YYYY-MM-DD HH:mm") %>
