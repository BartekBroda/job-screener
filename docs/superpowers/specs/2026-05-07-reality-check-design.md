# Reality Check — Design Spec

**Date:** 2026-05-07
**Status:** Approved

## Problem

Job listings frequently obscure what a role actually is behind management-speak and inflated language. The existing six-layer analysis evaluates *whether* a listing is worth applying to, but does not surface *what the language itself signals* about the role in plain terms. A reader has to do that translation themselves.

## Goal

Add a "Reality check" section to each job analysis: a short plain-English summary of what the role actually is, plus up to six specific corpo-speak phrases decoded into plain statements. Purely informational — no verdict impact.

---

## Architecture

Pure front-end change plus prompt additions. No new DB columns, no new endpoints, no `save_job()` changes.

`app.py` already parses `raw_json` into a `raw` dict and passes it to both detail templates. The new field lives in `raw` — no separate storage needed.

| File | Action |
|---|---|
| `analyzer.py` | Add `reality_check` to `SYSTEM_TEMPLATE` prompt and JSON schema |
| `static/style.css` | Add `.reality-check-*` classes |
| `templates/job_partial.html` | Add Reality check card before layer accordions |
| `templates/job_detail.html` | Same addition |

---

## Data

### New JSON field in model response

```json
"reality_check": {
  "summary": "2-3 sentences synthesising what the language signals about the actual role",
  "callouts": [
    {"phrase": "scalable and repeatable", "plain": "writing processes nobody currently follows"},
    {"phrase": "principal-level IC", "plain": "senior title, no budget, no team"}
  ]
}
```

- `summary`: always present; 2–3 sentences; synthesises what the callouts and framing collectively reveal
- `callouts`: up to 6 items; only phrases that genuinely obscure meaning; empty list `[]` if the listing uses clear language — no forced cynicism
- `phrase`: exact quote or close paraphrase from the listing
- `plain`: what it actually means; direct and slightly wry

### Storage

No new column. The full model response is already stored in `raw_json`. `app.py` parses it into `raw` and passes it to both `job_partial.html` and `job_detail.html`. Templates access it as `raw.get('reality_check')`.

Old records: `raw_json` won't contain `reality_check`, so `raw.get('reality_check')` returns `None` — section not rendered.

---

## Prompt — `analyzer.py`

Add a new section to `SYSTEM_TEMPLATE` before the FORMAT block:

```
══════════════════════════════════════════════════
REALITY CHECK
══════════════════════════════════════════════════
Translate the listing's language into plain statements.

summary: 2-3 sentences synthesising what the language and framing signal
         about what this role actually is day-to-day.

callouts: up to 6 specific phrases from the listing decoded into plain English.
  - "phrase": exact quote or close paraphrase from the listing
  - "plain": what it actually means — direct, slightly wry, accurate
  - Only include phrases that genuinely obscure meaning
  - If the listing uses clear language, return an empty list []
  - Do not invent signals that are not in the text
```

Add to the JSON schema in the FORMAT block (after `gut_feeling`):

```json
"reality_check": {
  "summary": "2-3 sentences on what the language signals about the actual role",
  "callouts": [
    {"phrase": "exact quote or close paraphrase", "plain": "what it actually means"}
  ]
}
```

---

## UI — Both Detail Templates

### Placement

Before the layer accordions, after the card header (verdict badge, role, company, verdict summary, listing URL).

### HTML structure

```html
{% set rc = raw.get('reality_check') %}
{% if rc %}
<div class="card reality-check-card">
  <div class="card-body">
    <div class="reality-check-label">Reality check</div>
    <div class="reality-check-summary">{{ rc.summary }}</div>
    {% if rc.callouts %}
    <div class="reality-check-divider"></div>
    {% for item in rc.callouts %}
    <div class="reality-check-callout">
      <span class="reality-check-phrase">"{{ item.phrase }}"</span>
      <span class="reality-check-arrow">→</span>
      <span class="reality-check-plain">{{ item.plain }}</span>
    </div>
    {% endfor %}
    {% endif %}
  </div>
</div>
{% endif %}
```

### CSS

```css
.reality-check-card {
  margin-bottom: 12px;
  border-left: 3px solid var(--green);
}
.reality-check-label {
  font-family: var(--fm);
  font-size: var(--fs-2xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--green);
  margin-bottom: 8px;
}
.reality-check-summary {
  font-size: var(--fs-sm);
  color: var(--muted);
  line-height: 1.65;
}
.reality-check-divider {
  border-top: 1px solid var(--border);
  margin: 10px 0;
}
.reality-check-callout {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 5px;
  font-size: var(--fs-sm);
}
.reality-check-phrase {
  font-style: italic;
  color: var(--dim);
  flex-shrink: 0;
}
.reality-check-arrow {
  color: var(--green);
  flex-shrink: 0;
}
.reality-check-plain {
  color: var(--muted);
}
```

`var(--green)` is `#2e8b57` — already defined in the design token set, already overridden in the light palette.

---

## Light Mode

All new classes use existing CSS variables — no extra light-mode overrides needed.

---

## Out of Scope

- Decoding old records (no backfill; `raw_json` for old analyses won't contain the field)
- Surfacing callouts in the history table or analytics
- Filtering or searching by decoded phrases
- Any verdict or scoring impact from the decoded content
- Separate "decode" endpoint or on-demand trigger
