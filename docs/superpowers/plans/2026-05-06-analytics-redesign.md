# Analytics Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the analytics page for readability: plain-English TL;DR, visual application funnel, stacked verdict bar, flag-only layer bars sorted by severity, and secondary sections collapsed by default.

**Architecture:** Pure front-end change plus two small additions to `get_analytics()` — no new endpoints, no schema changes. Three files modified: `database.py` (new dict keys), `static/style.css` (new classes, remove stat-card classes), `templates/analytics.html` (full block rebuild).

**Tech Stack:** Python/SQLite, Jinja2, vanilla JS, CSS custom properties. No build tools.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `database.py` | Modify `get_analytics()` at line 731 | Add `funnel.qualifying`, `most_flagged_layer`, `layer_flag_counts` |
| `static/style.css` | Modify analytics section (lines 423–523) | Remove stat-card classes; add funnel, TL;DR, stacked bar, collapsible classes |
| `templates/analytics.html` | Full `{% block content %}` rebuild | New page structure: TL;DR → funnel → breakdown grid → collapsed sections |

---

### Task 1: `database.py` — add qualifying, most_flagged_layer, layer_flag_counts

**Files:**
- Modify: `database.py` (function `get_analytics`, lines 731–821)
- Test: `tests/test_analytics.py`

Context: `get_analytics()` builds `verdict_distribution` first, then `layer_flags`, then returns a dict. New keys are computed from those existing structures — no new DB queries needed.

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_analytics.py` (before `if __name__ == '__main__'`):

```python
def test_funnel_qualifying(tmp_path):
    uid = _seed_db(tmp_path)
    data = database.get_analytics(uid)
    # seed: 3 worth_considering + 1 warning = 4 qualifying
    assert data['funnel']['qualifying'] == 4

def test_most_flagged_layer(tmp_path):
    uid = _seed_db(tmp_path)
    data = database.get_analytics(uid)
    mfl = data['most_flagged_layer']
    assert mfl is not None
    assert isinstance(mfl, tuple) and len(mfl) == 2
    assert isinstance(mfl[0], str)   # layer label e.g. 'Triage'
    assert isinstance(mfl[1], int) and mfl[1] >= 1

def test_layer_flag_counts(tmp_path):
    uid = _seed_db(tmp_path)
    data = database.get_analytics(uid)
    counts = data['layer_flag_counts']
    assert len(counts) == 6  # one entry per layer
    for i in range(len(counts) - 1):
        assert counts[i][1] >= counts[i + 1][1], "list must be sorted descending"
    for label, count in counts:
        assert isinstance(label, str)
        assert isinstance(count, int) and count >= 0
```

Also update the `if __name__ == '__main__'` block at the bottom of the file to include the new tests:

```python
if __name__ == '__main__':
    import tempfile
    tests = [
        test_verdict_distribution, test_funnel, test_layer_flags,
        test_fit_score_avg, test_archetype_distribution,
        test_funnel_qualifying, test_most_flagged_layer, test_layer_flag_counts,
    ]
    for t in tests:
        with tempfile.TemporaryDirectory() as tmp:
            t(tmp)
            print(f"  PASS: {t.__name__}")
    print("All analytics tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run pytest tests/test_analytics.py -v
```

Expected: 3 new tests fail with `KeyError: 'qualifying'` or similar. The 5 existing tests still pass.

- [ ] **Step 3: Add the three new keys to `get_analytics()`**

The function is at `database.py:731`. Make these two changes:

**Change 1** — after the `for row in rows:` loop (around line 798), add `qualifying` to the funnel dict. Find this block:

```python
    fit_score_avg = round(sum(fit_scores) / len(fit_scores), 2) if fit_scores else None
```

Insert immediately before it:

```python
    funnel['qualifying'] = verdict_distribution['worth_considering'] + verdict_distribution['warning']

    layer_labels = {
        'triage': 'Triage', 'product': 'Product', 'business': 'Business',
        'reputation': 'Reputation', 'values': 'Values', 'fit': 'Skills fit',
    }
    most_flagged_layer = None
    max_flags = 0
    for _layer in layers:
        fc = layer_flags[_layer]['flag']
        if fc > max_flags:
            max_flags = fc
            most_flagged_layer = (layer_labels[_layer], fc)

    layer_flag_counts = sorted(
        [(layer_labels[l], layer_flags[l]['flag']) for l in layers],
        key=lambda x: -x[1],
    )

```

**Change 2** — add the three new keys to the `return` dict (around line 813). Find:

```python
    return {
        'verdict_distribution': verdict_distribution,
        'funnel': funnel,
        'layer_flags': layer_flags,
        'fit_score_avg': fit_score_avg,
        'fit_score_distribution': buckets,
        'archetype_distribution': dict(sorted(archetype_distribution.items(), key=lambda x: -x[1])),
        'zero_list_hits': zero_list_hits,
    }
```

Replace with:

```python
    return {
        'verdict_distribution': verdict_distribution,
        'funnel': funnel,
        'layer_flags': layer_flags,
        'most_flagged_layer': most_flagged_layer,
        'layer_flag_counts': layer_flag_counts,
        'fit_score_avg': fit_score_avg,
        'fit_score_distribution': buckets,
        'archetype_distribution': dict(sorted(archetype_distribution.items(), key=lambda x: -x[1])),
        'zero_list_hits': zero_list_hits,
    }
```

- [ ] **Step 4: Run all analytics tests**

```bash
uv run pytest tests/test_analytics.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all 20+ tests pass, no failures.

- [ ] **Step 6: Commit**

```bash
git add database.py tests/test_analytics.py
git commit -m "feat: add qualifying, most_flagged_layer, layer_flag_counts to get_analytics()"
```

---

### Task 2: `static/style.css` — add new analytics classes, remove stat-card classes

**Files:**
- Modify: `static/style.css` (analytics section, lines 423–523)

Context: The analytics section starts at line 423 with `/* ── analytics ── */`. Lines 424–459 contain `.analytics-grid`, `.stat-card`, `.stat-card-label`, `.stat-card-value`, `.stat-card-sub` — all used only on `analytics.html` and all being removed. Lines 461–523 contain bar-chart classes and `.analytics-section-title` which are kept.

- [ ] **Step 1: Remove the stat-card classes**

Find and delete the following block (lines 424–459):

```css
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px 24px;
}

.stat-card-label {
  font-family: var(--fm);
  font-size: var(--fs-xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.stat-card-value {
  font-family: var(--fd);
  font-size: var(--fs-3xl);
  font-weight: 200;
  color: var(--text);
  line-height: 1.1;
}

.stat-card-sub {
  font-size: var(--fs-sm);
  color: var(--muted);
  margin-top: 4px;
}
```

- [ ] **Step 2: Add new analytics classes after the analytics section's last rule**

Find the last rule in the analytics section:

```css
[data-theme="light"] .bar-track { background: var(--border-light); }
```

Add immediately after it:

```css
.analytics-tldr {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  margin-bottom: 28px;
}
.analytics-tldr-label {
  font-family: var(--fm);
  font-size: var(--fs-2xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  margin-bottom: 6px;
}
.analytics-tldr-text { font-size: var(--fs-sm); color: var(--muted); line-height: 1.65; }
.analytics-tldr-text strong { color: var(--text); }

.analytics-funnel { display: flex; align-items: stretch; gap: 0; margin-bottom: 10px; }
.funnel-step { flex: 1; text-align: center; }
.funnel-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px 8px 12px;
  margin: 0 4px;
}
.funnel-num { font-family: var(--fd); font-size: var(--fs-3xl); font-weight: 200; line-height: 1; }
.funnel-lbl {
  font-family: var(--fm);
  font-size: var(--fs-2xs);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 6px;
}
.funnel-pct { font-size: var(--fs-xs); margin-top: 6px; min-height: 1.4em; }
.funnel-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-bottom: 28px;
  color: var(--border-light);
  font-size: var(--fs-xl);
  flex-shrink: 0;
  width: 18px;
}
.funnel-step-qualifying .funnel-num,
.funnel-step-qualifying .funnel-pct { color: #4a9eff; }
.funnel-step-applied .funnel-num,
.funnel-step-applied .funnel-pct    { color: #3dba73; }
.funnel-step-corej .funnel-num,
.funnel-step-corej .funnel-pct      { color: #e07b39; }

.zero-rule-note { font-size: var(--fs-xs); color: var(--dim); margin-bottom: 28px; padding-left: 4px; }
.zero-rule-note strong { color: var(--muted); }

.analytics-card-title {
  font-family: var(--fm);
  font-size: var(--fs-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 12px;
}

.stacked-bar { height: 16px; border-radius: 4px; overflow: hidden; display: flex; margin-bottom: 12px; }
.stacked-bar-seg { height: 100%; }
.stacked-bar-seg.seg-worth    { background: #4a9eff; }
.stacked-bar-seg.seg-warning  { background: #c9a96e; }
.stacked-bar-seg.seg-rejected { background: #e74c3c; }
.stacked-bar-seg.seg-soft     { background: var(--muted); }

.stacked-legend { display: flex; flex-wrap: wrap; gap: 8px 14px; }
.stacked-legend-item { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs); color: var(--muted); }
.stacked-legend-dot { width: 9px; height: 9px; border-radius: 2px; flex-shrink: 0; }
.stacked-legend-dot.dot-worth    { background: #4a9eff; }
.stacked-legend-dot.dot-warning  { background: #c9a96e; }
.stacked-legend-dot.dot-rejected { background: #e74c3c; }
.stacked-legend-dot.dot-soft     { background: var(--muted); }

.analytics-breakdown-card .bar-label { width: 90px; }
.bar-count-flag { color: #e74c3c; }

.collapsible { border: 1px solid var(--border); border-radius: var(--radius-sm); margin-bottom: 8px; overflow: hidden; }
.collapsible-header {
  background: var(--surface);
  padding: 11px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.collapsible-header:hover { background: color-mix(in srgb, var(--surface) 90%, white 10%); }
.collapsible-label { font-size: var(--fs-sm); color: var(--muted); }
.collapsible-right { display: flex; align-items: center; gap: 10px; }
.collapsible-meta { font-size: var(--fs-xs); color: var(--dim); }
.collapsible-arrow { font-family: var(--fm); font-size: var(--fs-2xs); color: var(--dim); }
.collapsible-body { padding: 14px 16px; }
```

- [ ] **Step 3: Start the app and verify no regressions on other pages**

```bash
uv run --env-file config.env python app.py
```

Open `http://localhost:5000/dashboard` and `http://localhost:5000/settings`. Both should look unchanged — no stat-card classes appear on those pages.

- [ ] **Step 4: Commit**

```bash
git add static/style.css
git commit -m "style: add analytics funnel, TL;DR, stacked bar, collapsible classes; remove stat-card"
```

---

### Task 3: `templates/analytics.html` — full page rebuild

**Files:**
- Modify: `templates/analytics.html`

Context: The entire `{% block content %}` and `{% block scripts %}` are replaced. The existing template has inline styles throughout (the old approach). The new template uses CSS classes for all colours; `style="width:X%"` on bar fills is the only remaining inline style (dynamic data-driven widths — existing pattern in this file). `style="display:none"` on collapsible bodies is JS-managed state (the one permitted exception). Read the full file before editing.

Key data keys available from `get_analytics()` after Task 1:
- `data.funnel` → `{total, qualifying, applied, company_rejected}`
- `data.most_flagged_layer` → `(label, count)` or `None`
- `data.layer_flag_counts` → `[(label, count), ...]` sorted desc
- `data.verdict_distribution` → `{worth_considering, warning, rejected_confirmed, rejected_soft}`
- `data.fit_score_avg` → float or `None`
- `data.fit_score_distribution` → `[(label, count), ...]`
- `data.archetype_distribution` → `{arch: count, ...}`
- `data.zero_list_hits` → int

- [ ] **Step 1: Replace the entire file content**

Replace `templates/analytics.html` with:

```html
{% extends "base.html" %}
{% block title %}Analytics — Job Screener{% endblock %}

{% block content %}
<div class="page-title">Analytics</div>
<p class="page-sub">Aggregated statistics from all your analyses.</p>

{% if data.funnel.total == 0 %}
<div class="notice">No analyses yet. <a href="{{ url_for('dashboard') }}" class="link-accent">Analyze your first listing →</a></div>
{% else %}

{# ── TL;DR ──────────────────────────────────────────────────────── #}
<div class="analytics-tldr">
  <div class="analytics-tldr-label">Summary</div>
  <div class="analytics-tldr-text">
    You've analyzed <strong>{{ data.funnel.total }}</strong> job{{ 's' if data.funnel.total != 1 else '' }}{% if data.funnel.applied > 0 %} and applied to <strong>{{ data.funnel.applied }}</strong>{% if data.funnel.qualifying > 0 %} — a <strong>{{ (data.funnel.applied / data.funnel.qualifying * 100)|round|int }}%</strong> follow-through rate on qualifying listings{% endif %}{% endif %}.{% if data.most_flagged_layer %} <strong>{{ data.most_flagged_layer[0] }}</strong> is your most common blocker ({{ data.most_flagged_layer[1] }} flag{{ 's' if data.most_flagged_layer[1] != 1 else '' }}).{% endif %}{% if data.fit_score_avg is not none %} Average fit score across scored analyses is <strong>{{ "%.1f"|format(data.fit_score_avg) }}/5</strong>.{% endif %}
  </div>
</div>

{# ── Application pipeline ───────────────────────────────────────── #}
<div class="analytics-section-title">Application pipeline</div>
<div class="analytics-funnel">
  <div class="funnel-step">
    <div class="funnel-block">
      <div class="funnel-num">{{ data.funnel.total }}</div>
      <div class="funnel-lbl">Analyzed</div>
    </div>
    <div class="funnel-pct"></div>
  </div>
  <div class="funnel-arrow">›</div>
  <div class="funnel-step funnel-step-qualifying">
    <div class="funnel-block">
      <div class="funnel-num">{{ data.funnel.qualifying }}</div>
      <div class="funnel-lbl">Qualifying</div>
    </div>
    <div class="funnel-pct">
      {%- if data.funnel.total > 0 %}{{ (data.funnel.qualifying / data.funnel.total * 100)|round|int }}% of analyzed{% endif -%}
    </div>
  </div>
  <div class="funnel-arrow">›</div>
  <div class="funnel-step funnel-step-applied">
    <div class="funnel-block">
      <div class="funnel-num">{{ data.funnel.applied }}</div>
      <div class="funnel-lbl">Applied</div>
    </div>
    <div class="funnel-pct">
      {%- if data.funnel.qualifying > 0 %}{{ (data.funnel.applied / data.funnel.qualifying * 100)|round|int }}% of qualifying{% endif -%}
    </div>
  </div>
  <div class="funnel-arrow">›</div>
  <div class="funnel-step funnel-step-corej">
    <div class="funnel-block">
      <div class="funnel-num">{{ data.funnel.company_rejected }}</div>
      <div class="funnel-lbl">Co. rejected</div>
    </div>
    <div class="funnel-pct">
      {%- if data.funnel.applied > 0 %}{{ (data.funnel.company_rejected / data.funnel.applied * 100)|round|int }}% of applied{% endif -%}
    </div>
  </div>
</div>
{% if data.zero_list_hits > 0 %}
<p class="zero-rule-note"><strong>{{ data.zero_list_hits }}</strong> auto-rejected by Zero Rule — not included above.</p>
{% endif %}

{# ── Breakdown grid ─────────────────────────────────────────────── #}
<div class="analytics-section-title">Breakdown</div>
<div class="grid2">

  <div class="card analytics-breakdown-card">
    <div class="card-body">
      <div class="analytics-card-title">Verdict distribution</div>
      {% set vd = data.verdict_distribution %}
      {% set vd_total = vd.worth_considering + vd.warning + vd.rejected_confirmed + vd.rejected_soft %}
      {% if vd_total > 0 %}
      <div class="stacked-bar">
        {% if vd.worth_considering > 0 %}<div class="stacked-bar-seg seg-worth" style="width:{{ (vd.worth_considering / vd_total * 100)|round }}%"></div>{% endif %}
        {% if vd.warning > 0 %}<div class="stacked-bar-seg seg-warning" style="width:{{ (vd.warning / vd_total * 100)|round }}%"></div>{% endif %}
        {% if vd.rejected_confirmed > 0 %}<div class="stacked-bar-seg seg-rejected" style="width:{{ (vd.rejected_confirmed / vd_total * 100)|round }}%"></div>{% endif %}
        {% if vd.rejected_soft > 0 %}<div class="stacked-bar-seg seg-soft" style="width:{{ (vd.rejected_soft / vd_total * 100)|round }}%"></div>{% endif %}
      </div>
      <div class="stacked-legend">
        <div class="stacked-legend-item"><span class="stacked-legend-dot dot-worth"></span>Worth considering — {{ vd.worth_considering }}</div>
        <div class="stacked-legend-item"><span class="stacked-legend-dot dot-warning"></span>Needs review — {{ vd.warning }}</div>
        <div class="stacked-legend-item"><span class="stacked-legend-dot dot-rejected"></span>Rejected — {{ vd.rejected_confirmed }}</div>
        <div class="stacked-legend-item"><span class="stacked-legend-dot dot-soft"></span>Rejected (AI) — {{ vd.rejected_soft }}</div>
      </div>
      {% else %}
      <div class="td-dim">No verdict data.</div>
      {% endif %}
    </div>
  </div>

  <div class="card analytics-breakdown-card">
    <div class="card-body">
      <div class="analytics-card-title">Layer flags</div>
      {% set max_flag = data.layer_flag_counts[0][1] if data.layer_flag_counts and data.layer_flag_counts[0][1] > 0 else 1 %}
      {% if data.layer_flag_counts and data.layer_flag_counts[0][1] > 0 %}
      <div class="bar-chart">
        {% for label, count in data.layer_flag_counts %}
        {% if count > 0 %}
        <div class="bar-row">
          <div class="bar-label">{{ label }}</div>
          <div class="bar-track">
            <div class="bar-fill bar-flag" style="width:{{ (count / max_flag * 100)|round }}%"></div>
          </div>
          <div class="bar-count bar-count-flag">{{ count }}</div>
        </div>
        {% endif %}
        {% endfor %}
      </div>
      {% else %}
      <div class="td-dim">No flags recorded.</div>
      {% endif %}
    </div>
  </div>

</div>

{# ── Collapsible sections ───────────────────────────────────────── #}
{% if data.fit_score_avg is not none %}
<div class="collapsible">
  <div class="collapsible-header" onclick="toggleCollapsible(this)">
    <span class="collapsible-label">Fit score distribution</span>
    <div class="collapsible-right">
      <span class="collapsible-meta">{{ data.fit_score_distribution | sum(attribute=1) }} scored</span>
      <span class="collapsible-arrow">▶</span>
    </div>
  </div>
  <div class="collapsible-body" style="display:none">
    {% set fs_total = data.fit_score_distribution | sum(attribute=1) %}
    {% if fs_total > 0 %}
    <div class="bar-chart">
      {% for label, count in data.fit_score_distribution %}
      <div class="bar-row">
        <div class="bar-label">{{ label }}</div>
        <div class="bar-track">
          <div class="bar-fill bar-worth" style="width:{{ (count / fs_total * 100)|round }}%"></div>
        </div>
        <div class="bar-count">{{ count }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>
</div>
{% endif %}

{% if data.archetype_distribution %}
<div class="collapsible">
  <div class="collapsible-header" onclick="toggleCollapsible(this)">
    <span class="collapsible-label">Role archetypes</span>
    <div class="collapsible-right">
      <span class="collapsible-meta">{{ data.archetype_distribution | length }} type{{ 's' if data.archetype_distribution | length != 1 else '' }}</span>
      <span class="collapsible-arrow">▶</span>
    </div>
  </div>
  <div class="collapsible-body" style="display:none">
    {% set arch_total = data.archetype_distribution.values() | sum %}
    <div class="bar-chart">
      {% for arch, count in data.archetype_distribution.items() %}
      <div class="bar-row">
        <div class="bar-label">{{ arch }}</div>
        <div class="bar-track">
          <div class="bar-fill bar-neutral" style="width:{{ (count / arch_total * 100)|round }}%"></div>
        </div>
        <div class="bar-count">{{ count }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>
{% endif %}

{% endif %}
{% endblock %}

{% block scripts %}
<script>
function toggleCollapsible(header) {
  var body = header.nextElementSibling;
  var arrow = header.querySelector('.collapsible-arrow');
  var open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  arrow.textContent = open ? '▶' : '▼';
}
</script>
{% endblock %}
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 3: Manual smoke test**

```bash
uv run --env-file config.env python app.py
```

Open `http://localhost:5000/analytics`. Verify:

1. **TL;DR card** — gold left border; sentence mentions total jobs, applied count and follow-through %, most flagged layer, avg fit score (if any scored records exist)
2. **Pipeline funnel** — four blocks: Analyzed / Qualifying / Applied / Co. rejected; qualifying and applied blocks have blue/green numbers; percentages appear below each block except "Analyzed"
3. **Zero Rule note** — appears below funnel only if `zero_list_hits > 0` (check settings if none exist)
4. **Verdict stacked bar** — proportional single bar; legend below with four coloured dots and counts
5. **Layer flags card** — bars for flag-only layers, sorted descending; layers with 0 flags not shown; bar counts are red; "No flags recorded." if all zero
6. **Fit score distribution** — collapsed by default; click header → expands bar chart, arrow changes to ▼; click again → collapses, arrow returns to ▶
7. **Role archetypes** — collapsed by default; same toggle behaviour
8. **Dashboard/Settings** — unaffected; no layout breakage

- [ ] **Step 4: Commit**

```bash
git add templates/analytics.html
git commit -m "feat: rebuild analytics page — TL;DR, funnel, stacked verdict bar, collapsed sections"
```

---

### Task 4: CHANGELOG update

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add v0.13 entry before the existing v0.12 entry**

Find:

```markdown
## v0.12 — History table redesign
```

Add immediately before it:

```markdown
## v0.13 — Analytics redesign

- Plain-English TL;DR card at top: interprets total analyzed, follow-through rate, most common blocker, avg fit score
- Application pipeline funnel replaces stat cards: Analyzed → Qualifying → Applied → Co. rejected with drop-off percentages
- Verdict distribution rebuilt as single proportional stacked bar — proportions visible at a glance
- Layer flags simplified to flag-count-only bars sorted by severity — ok/warning noise removed
- Fit score distribution and Role archetypes collapsed by default — click to expand
- All colours moved to CSS classes; no new inline styles

---

```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: v0.13 analytics redesign"
```
