# Background Analysis + Persistent Banner

**Date:** 2026-05-06
**Status:** Approved

## Problem

Analysis takes 60–120s. Currently the browser holds an open fetch() — navigating away aborts it and the result is lost. Users have no way to check other parts of the tool while waiting.

## Goal

Analysis runs server-side in a background thread. A persistent banner below the nav shows progress on every page. User can freely navigate during analysis and click the banner to view the result when done.

---

## Architecture

`POST /analyze` becomes non-blocking:
1. Validates input, deduplicates, scrapes (synchronous — fast path, same as now)
2. Creates an `analyses` record (`status='pending'`, `source_label`)
3. Spawns `threading.Thread` → returns `{"analysis_id": uuid}` immediately

The thread runs the full Claude API analysis, writes to `jobs`, updates `analyses`. Any gunicorn worker can serve status polls by reading the shared SQLite DB.

`/reanalyze/<id>` gets the same thread treatment.

---

## Data Model

New table added to `SCHEMA` in `database.py` (`CREATE TABLE IF NOT EXISTS`):

```sql
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,           -- uuid4
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL,          -- pending | running | done | error
    source_label TEXT,             -- URL or first 60 chars of pasted text
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    result_job_id INTEGER,         -- FK to jobs.id on success
    error TEXT,                    -- error message on failure
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

**Stuck-job cleanup** in `init_db()`: on startup, any row with `status IN ('pending','running')` and `started_at < now - 5 minutes` is set to `status='error'`, `error='Server restarted'`. Handles killed workers without leaving orphaned spinners.

---

## Backend — New / Changed Endpoints

### `POST /analyze` (modified)

Flow:
1. Normalize URL, validate input — same as before
2. Scrape if URL-only — same as before (synchronous, fast)
3. Deduplicate — same as before
4. `create_analysis(user_id, source_label)` → `analysis_id`
5. `threading.Thread(target=_run_analysis_bg, args=(...)).start()`
6. Return `{"analysis_id": analysis_id}`

### `_run_analysis_bg(analysis_id, user, input_text, url, scraped)` (new, private)

```
set status='running'
result = analyze(user, input_text, "text", API_KEY)
job = save_job(user_id, result, source_url=url, source_text=input_text)
set status='done', result_job_id=job.id, finished_at=now
on Exception: set status='error', error=str(e)
```

### `GET /analysis_status/<id>` (new)

- `@login_required`
- Joins `analyses` + `jobs` on `result_job_id`
- Returns:
  ```json
  {
    "status": "running",
    "source_label": "Senior PM · Figma Inc.",
    "result_job_id": 42,
    "company": "Figma Inc.",
    "role": "Senior Product Manager",
    "verdict": "worth_considering"
  }
  ```
- 404 if not found or belongs to different user

### `POST /reanalyze/<id>` (modified)

Same thread pattern as `/analyze` — returns `{"analysis_id": ...}` immediately.

---

## Frontend

### `base.html` — Banner element + polling JS

**HTML** (inserted between `<nav>` and `<div class="container">`):
```html
<div id="analysis-banner" style="display:none">
  <!-- content injected by JS based on state -->
</div>
```

**JS IIFE** on every page load:
1. Read `localStorage.getItem('activeAnalysis')` → `{id, source_label}`
2. If present: show banner in `running` state, start 3s poll loop
3. Poll `/analysis_status/<id>`:
   - `running/pending` → keep spinner + pulsing dots
   - `done` → switch to done state (green, company + verdict badge, "View result →" link to `/job/<result_job_id>`), stop polling; clicking the banner clears localStorage
   - `error` → switch to error state (red, error text, dismiss button clears localStorage)
   - 404 → clear localStorage, hide banner (stale entry)
   - Network error → silent retry next tick

The `reanalyze()` function in modal JS (history/dashboard) also receives `{analysis_id}` and writes localStorage the same way as `runAnalysis()`.

### `dashboard.html` — `runAnalysis()` changes

- POSTs to `/analyze`, receives `{analysis_id}`
- Writes `localStorage.setItem('activeAnalysis', JSON.stringify({id, source_label}))`
- Dispatches a custom `analysisStarted` event so the banner IIFE activates immediately without a page reload
- Result box shows: "Analysis started — you can navigate away. The banner above will update when done."
- Removes the inline loading spinner from the result area (banner owns progress now)

### Banner visual states

**Running** — blue-grey background strip:
```
⟳  Analyzing — Senior PM · Figma Inc.          ▬ ▬ ▬  (pulsing dots)
```

**Done** — green background strip (clickable row):
```
✓  Analysis done — Figma Inc. · Senior PM  [worth considering]   View result →
```

**Error** — red background strip:
```
✕  Analysis failed — API timeout                                    Dismiss ×
```

### `style.css`

New classes: `.analysis-banner`, `.analysis-banner.is-running`, `.analysis-banner.is-done`, `.analysis-banner.is-error`

All styled as a full-width fixed strip below the `<nav>`, height ~36px, `font-family: var(--fm)`, `font-size: var(--fs-xs)`. No inline styles in HTML.

---

## Error handling

| Scenario | Behaviour |
|---|---|
| API timeout (>120s) | Thread catches exception → `status='error'` → banner shows error + dismiss |
| Worker killed mid-analysis | `init_db()` on next startup marks stuck rows → banner shows error on next poll |
| Network error in browser poll | Silent retry next tick |
| User opens two tabs, starts analysis in both | Each gets its own `analysis_id`; localStorage stores the most recent one |
| 404 on status poll (stale localStorage) | Clear localStorage, hide banner silently |

---

## Files Changed

| File | Change |
|---|---|
| `database.py` | Add `analyses` table to SCHEMA; add `create_analysis()`, `update_analysis_status()`, `get_analysis()` functions; cleanup in `init_db()` |
| `app.py` | Modify `run_analyze()`, `run_reanalyze()`; add `_run_analysis_bg()` thread fn; add `GET /analysis_status/<id>` |
| `templates/base.html` | Add `#analysis-banner` element + polling IIFE |
| `templates/dashboard.html` | Update `runAnalysis()` to handle `{analysis_id}` response + localStorage write + custom event |
| `static/style.css` | Add `.analysis-banner` and state variant classes |

---

## Out of scope

- Real per-layer progress (would require SSE or analyzer callbacks — future)
- Push notifications / browser notifications API
- Multiple simultaneous analyses visible in banner (banner tracks one at a time — last started wins)
