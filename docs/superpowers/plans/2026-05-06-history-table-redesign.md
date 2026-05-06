# History Table Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the history table from 12 columns to 7, make the filter bar and table header sticky on scroll, add a "Show all" filter reset, surface the fit score as its own column, and remove the 1280px container ceiling for this page.

**Architecture:** Pure front-end change — two files modified (`static/style.css`, `templates/history.html`) and one lightly modified (`templates/base.html` gains a `container_class` block so child templates can opt out of the max-width constraint). No backend, no DB, no new endpoints.

**Tech Stack:** Jinja2 templates, vanilla JS, CSS custom properties. No build tools.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `static/style.css` | Modify | New classes: `.container-full`, `.table-wrap`, `.td-layers`, `.td-warning`, `.col-*`; update `.filter-bar` to be sticky; add `thead th` sticky rule |
| `templates/base.html` | Modify | Add `{% block container_class %}container{% endblock %}` so history can override |
| `templates/history.html` | Modify | Full table rebuild: colgroup, new thead, new tbody cells, filter bar "Show all" button, updated JS |

---

### Task 1: CSS additions

**Files:**
- Modify: `static/style.css`

Context: The existing `.filter-bar` rule is at line 330. The `th` rule is at line 193. The `/* ── layout ── */` section is at line 124 with `.container`. Add new rules in the appropriate sections.

- [ ] **Step 1: Add `.container-full` and `.table-wrap` after the existing `.container` rule**

Find:
```css
.container { max-width: 1280px; margin: 0 auto; padding: 40px 24px 80px; }
```

Add immediately after it:
```css
.container-full { max-width: none; margin: 0; padding: 40px 24px 80px; }
.table-wrap { overflow-x: auto; }
```

- [ ] **Step 2: Add `colgroup` column-width classes**

Add after `.table-wrap`:
```css
.col-date    { width: 90px; }
.col-badge   { width: 200px; }
.col-l0      { width: 44px; }
.col-layers  { width: 100px; }
.col-fit     { width: 75px; }
```

- [ ] **Step 3: Update `.filter-bar` to be sticky**

Find:
```css
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
```

Replace with:
```css
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; position: sticky; top: 0; z-index: 20; background: var(--bg); padding: 12px 0; margin-bottom: 4px; }
```

- [ ] **Step 4: Add sticky `thead th` rule**

Add immediately after the existing `th` rule (line 193):
```css
thead th { position: sticky; top: var(--filter-bar-h, 48px); z-index: 10; background: var(--surface); }
```

- [ ] **Step 5: Add `.td-layers` and `.td-warning`**

Find the `/* ── table ── */` section. After the last `td`-related rule (around line 197), add:
```css
.td-layers { display: flex; gap: 4px; align-items: center; padding-top: 13px; }
.td-warning { color: #f0c040; }
```

- [ ] **Step 6: Add light-mode override for `.td-warning`**

Find the block of `[data-theme="light"]` overrides for filter buttons (around line 393). Add alongside them:
```css
[data-theme="light"] .td-warning { color: #7a5800; }
```

- [ ] **Step 7: Verify no regressions by running the app and checking the dashboard and settings pages**

```bash
uv run --env-file config.env python app.py
```

Open `http://localhost:5000/dashboard` and `http://localhost:5000/settings`. Both should look unchanged — the new classes are not used there yet.

- [ ] **Step 8: Commit**

```bash
git add static/style.css
git commit -m "style: add container-full, table-wrap, sticky filter-bar, sticky thead, td-layers, td-warning"
```

---

### Task 2: `base.html` — container class block

**Files:**
- Modify: `templates/base.html`

Context: Line 34 of `base.html` is:
```html
<div class="container">
```
This needs a Jinja2 block so child templates can override the class name.

- [ ] **Step 1: Add `container_class` block to `base.html`**

Find:
```html
<div class="container">
```

Replace with:
```html
<div class="{% block container_class %}container{% endblock %}">
```

- [ ] **Step 2: Verify existing pages unaffected**

Open `http://localhost:5000/history`, `http://localhost:5000/dashboard`, `http://localhost:5000/settings`. All should still render inside the normal centred container (the block default is `container`).

- [ ] **Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: add container_class block to base.html for per-page width override"
```

---

### Task 3: `history.html` — full table rebuild

**Files:**
- Modify: `templates/history.html`

This task replaces the entire `{% block content %}` body of `history.html`. Read the file in full before editing. The changes are: container override, table structure, filter bar, tbody cells, JS updates.

- [ ] **Step 1: Override container class at top of `history.html`**

After `{% block title %}History — Job Screener{% endblock %}` and before `{% block content %}`, add:

```html
{% block container_class %}container-full{% endblock %}
```

- [ ] **Step 2: Add "Show all" button to the filter bar**

Find the filter bar block:
```html
<div class="filter-bar">
  <span class="filter-label">Show:</span>
  <button class="filter-btn active fb-worth_considering" onclick="toggleFilter('worth_considering', this)">Worth considering</button>
```

Replace the entire filter bar with:
```html
<div class="filter-bar">
  <span class="filter-label">Show:</span>
  <button class="filter-btn fb-all" onclick="showAll()">Show all</button>
  <button class="filter-btn active fb-worth_considering" data-cat="worth_considering" onclick="toggleFilter('worth_considering', this)">Worth considering</button>
  <button class="filter-btn active fb-warning" data-cat="warning" onclick="toggleFilter('warning', this)">Needs review</button>
  <button class="filter-btn active fb-rejected_soft" data-cat="rejected_soft" onclick="toggleFilter('rejected_soft', this)">Rejected (AI)</button>
  <button class="filter-btn active fb-rejected" data-cat="rejected" onclick="toggleFilter('rejected', this)">Rejected</button>
  <button class="filter-btn active fb-applied" data-cat="applied" onclick="toggleFilter('applied', this)">Applied</button>
  <button class="filter-btn active fb-company_rejected" data-cat="company_rejected" onclick="toggleFilter('company_rejected', this)">Rejected by company</button>
</div>
```

- [ ] **Step 3: Replace the `<table>` with the new 7-column structure**

Find the entire `<table>` block (from `<table>` to `</table>`) and replace with:

```html
<div class="table-wrap">
<table style="table-layout:fixed">
  <colgroup>
    <col class="col-date">
    <col>
    <col>
    <col class="col-badge">
    <col class="col-l0">
    <col class="col-layers">
    <col class="col-fit">
  </colgroup>
  <thead>
    <tr>
      <th>Date</th>
      <th>Role</th>
      <th>Company</th>
      <th>Verdict</th>
      <th>L0</th>
      <th>Layers</th>
      <th>Fit</th>
    </tr>
  </thead>
  <tbody>
    {% for j in jobs %}
    {% if j.verdict == 'rejected' and j.verdict_confirmed %}{% set row_cls = 'row-rejected' %}{% set cat = 'rejected' %}
    {% elif j.company_rejected %}{% set row_cls = 'row-company-rejected' %}{% set cat = 'company_rejected' %}
    {% elif j.applied %}{% set row_cls = 'row-applied' %}{% set cat = 'applied' %}
    {% elif j.verdict == 'rejected' and not j.verdict_confirmed %}{% set row_cls = 'row-rejected-soft' %}{% set cat = 'rejected_soft' %}
    {% elif j.verdict == 'worth_considering' %}{% set row_cls = 'row-worth-considering' %}{% set cat = 'worth_considering' %}
    {% elif j.verdict == 'warning' %}{% set row_cls = 'row-warning' %}{% set cat = 'warning' %}
    {% else %}{% set row_cls = '' %}{% set cat = j.verdict or 'unknown' %}{% endif %}
    <tr class="clickable{% if row_cls %} {{ row_cls }}{% endif %}" data-job-id="{{ j.id }}" data-category="{{ cat }}" onclick="openModal({{ j.id }})">
      <td class="td-date">{{ j.analyzed_at }}</td>
      <td class="td-role">{{ j.role or '—' }}</td>
      <td class="fw-500">{{ j.company or 'Unknown' }}</td>
      <td style="white-space:nowrap">
        {%- if j.company_rejected -%}<span class="badge badge-company_rejected" data-verdict="{{ j.verdict }}">Rejected by company</span>
        {%- elif j.applied -%}<span class="badge badge-applied" data-verdict="{{ j.verdict }}">Applied</span>
        {%- else -%}<span class="badge badge-{{ j.verdict }}" data-verdict="{{ j.verdict }}">{{ {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'}.get(j.verdict, j.verdict) }}</span>
        {%- endif %}
      </td>
      <td class="td-mono {% if j.zero_list_hit %}td-red{% else %}td-dim{% endif %}">{{ 'YES' if j.zero_list_hit else '—' }}</td>
      <td class="td-layers">
        <span class="dot dot-{{ j.triage_status or 'unknown' }}"     title="Triage: {{ j.triage_status or 'unknown' }}"></span>
        <span class="dot dot-{{ j.product_status or 'unknown' }}"    title="Product: {{ j.product_status or 'unknown' }}"></span>
        <span class="dot dot-{{ j.business_status or 'unknown' }}"   title="Business: {{ j.business_status or 'unknown' }}"></span>
        <span class="dot dot-{{ j.reputation_status or 'unknown' }}" title="Reputation: {{ j.reputation_status or 'unknown' }}"></span>
        <span class="dot dot-{{ j.values_status or 'unknown' }}"     title="Values: {{ j.values_status or 'unknown' }}"></span>
      </td>
      <td class="td-mono {% if j.fit_score is not none %}{% if j.fit_status == 'ok' %}td-green{% elif j.fit_status == 'warning' %}td-warning{% elif j.fit_status == 'flag' %}td-red{% else %}td-dim{% endif %}{% else %}td-dim{% endif %}">{{ "%.1f"|format(j.fit_score) ~ '/5' if j.fit_score is not none else '—' }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>
```

Note: `style="white-space:nowrap"` on the badge cell and `style="table-layout:fixed"` on the table are the two permitted inline style exceptions — both are structural invariants, not theme values.

- [ ] **Step 4: Update `updateTableRow()` JS — remove stale Status cell update**

Find in the `{% block scripts %}` section:
```js
  const statusCell = row.querySelector('td:last-child');
  if (statusCell) {
    if (status === 'company_rejected') { statusCell.textContent = '✕'; statusCell.className = 'td-mono td-orange'; }
    else if (status === 'applied')     { statusCell.textContent = '✓'; statusCell.className = 'td-mono td-green'; }
    else                               { statusCell.textContent = '—'; statusCell.className = 'td-mono td-dim'; }
  }
```

Delete those 5 lines entirely. The Status column no longer exists. The badge update immediately above those lines stays untouched.

- [ ] **Step 5: Add `showAll()` function to the JS block**

Find the `// ── Category filter ──` section. After the `toggleFilter` function, add:

```js
function showAll() {
  hiddenCategories.clear();
  localStorage.setItem(FILTER_STORAGE_KEY, '[]');
  document.querySelectorAll('.filter-btn[data-cat]').forEach(b => b.classList.add('active'));
  applyFilter();
}
```

- [ ] **Step 6: Update the restore-on-load IIFE to use `data-cat` and measure filter bar height**

Find the restore IIFE:
```js
(function() {
  hiddenCategories.forEach(cat => {
    const btn = document.querySelector(`.filter-btn.fb-${cat}`);
    if (btn) btn.classList.remove('active');
  });
  applyFilter();
})();
```

Replace with:
```js
(function() {
  hiddenCategories.forEach(cat => {
    const btn = document.querySelector(`.filter-btn[data-cat="${cat}"]`);
    if (btn) btn.classList.remove('active');
  });
  applyFilter();
  var fb = document.querySelector('.filter-bar');
  if (fb) document.documentElement.style.setProperty('--filter-bar-h', fb.offsetHeight + 'px');
})();
```

- [ ] **Step 7: Manual smoke test**

Start the server:
```bash
uv run --env-file config.env python app.py
```

Open `http://localhost:5000/history`. Verify:
1. Table has 7 columns: Date, Role, Company, Verdict, L0, Layers, Fit
2. Badge renders on a single line for all rows including "Rejected by company"
3. Layers column shows 5 coloured dots; hover each dot shows tooltip (e.g. "Triage: ok")
4. Fit column shows `X.X/5` in green/yellow/red, or `—` for older records without a score
5. Scroll down a long list — filter bar stays pinned at top; table header stays pinned just below filter bar
6. Click "Show all" — all 6 category filter buttons become active, all rows visible
7. Deactivate one filter, refresh page — filter state restored from localStorage
8. Click a row — modal opens correctly, modal navigation works
9. Change verdict in modal — table row updates colour and badge correctly (Status cell no longer updated, no JS error)
10. Check `http://localhost:5000/dashboard` — container still centred at 1280px

- [ ] **Step 8: Commit**

```bash
git add templates/history.html
git commit -m "feat: rebuild history table — 7 columns, sticky header/filters, fit score, show-all filter"
```

---

### Task 4: CHANGELOG update

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add v0.12 entry before the existing v0.11 entry**

```markdown
## v0.12 — History table redesign

- Rebuilt from 12 columns to 7: Date, Role, Company, Verdict, L0, Layers, Fit
- Classification badge always single-line; "Rejected by company" fits without wrapping
- Six analysis-layer dots collapsed into one compact dot strip with hover tooltips (Triage · Product · Business · Reputation · Values)
- Fit score surfaced as its own column (`X.X/5`, colour-coded by fit status)
- Status column removed (badge already encodes applied/company-rejected state)
- Filter bar and table header sticky on scroll — both remain visible on long lists
- "Show all" filter button resets all category filters at once
- History page no longer constrained to 1280px container — table uses full viewport width

---
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: v0.12 history table redesign"
```
