# Phases 1 & 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ghost job detection, compensation signals, role archetype, fit score, English UI, and DB columns for the two new structured fields.

**Architecture:** Phase 1 = prompt-only changes to `analyzer.py` (new fields appear in `raw_json`, zero DB changes) + full English UI translation across all templates and `app.py`. Phase 2 = two new DB columns (`role_archetype`, `fit_score`) + extraction in `save_job()` + display in job cards.

**Tech Stack:** Python 3.9, Flask 3.1.3, SQLite, Anthropic API (claude-sonnet-4-6), Jinja2, vanilla JS

---

## File Map

| File | Changes |
|---|---|
| `analyzer.py` | Extend `SYSTEM_TEMPLATE`: triage gets ghost legitimacy check + `role_archetype`; business gets compensation signal; fit gets numeric `score` (1.0–5.0); JSON format updated |
| `database.py` | `init_db()` migration: add `role_archetype TEXT`, `fit_score REAL`; `save_job()`: extract both fields |
| `app.py` | Translate all `flash()` strings Polish → English |
| `templates/base.html` | Translate nav labels, `lang` attr, theme toggle |
| `templates/dashboard.html` | Translate all UI strings and JS label maps; show archetype badge in inline result card |
| `templates/history.html` | Translate all UI strings and JS label maps; add archetype column |
| `templates/job_partial.html` | Translate all strings; show `role_archetype` badge + `fit_score` chip |
| `templates/job_detail.html` | Translate all strings; show `role_archetype` badge + `fit_score` chip |
| `templates/settings.html` | Translate all strings |
| `templates/login.html` | Translate all strings |
| `templates/register.html` | Translate all strings |
| `tests/test_database.py` | New: migration idempotency + save_job field extraction |
| `tests/test_analyzer_prompt.py` | New: build_system output sanity checks |

---

## Task 1: Extend SYSTEM_TEMPLATE — ghost job detection in Triage

**Files:**
- Modify: `analyzer.py:47` (triage layer description)
- Modify: `analyzer.py:86-90` (JSON format — triage object)

- [ ] **Step 1: Read current triage instruction (line 47) and triage JSON block (lines 86–90) to confirm exact text before editing**

- [ ] **Step 2: Replace triage layer description**

In `analyzer.py`, replace line 47:
```
1. TRIAGE - dopasowanie roli do profilu i trajektorii (nie tylko do CV), sygnały AI/eco/wellbeing-washing, ukryty pracodawca
```
With:
```
1. TRIAGE - dopasowanie roli do profilu i trajektorii (nie tylko do CV), sygnały AI/eco/wellbeing-washing, ukryty pracodawca.
   Dodatkowo oceń LEGITYMIZACJĘ ogłoszenia (ghost job risk). Sygnały do sprawdzenia:
   - Wiek ogłoszenia i wzorzec repostowania (wielokrotne odświeżanie = podejrzane)
   - Brak konkretnej nazwy zespołu, managera lub procesu rekrutacji
   - Treść JD ogólna bez technicznych detali specyficznych dla tej roli
   - "Apply now" ale brak aktywnego procesu / ogłoszenie bez daty / dziesiątki podobnych ogłoszeń tej firmy jednocześnie
   - Sygnały zamrożenia zatrudnienia: ostatnie zwolnienia, brak nowych wdrożeń, ogłoszenie "na wszelki wypadek"
   Ocena: ghost_job_risk "low" = konkretne ogłoszenie z detalami; "medium" = kilka sygnałów; "high" = multiple czerwone flagi
```

- [ ] **Step 3: Update triage JSON format block**

In `analyzer.py`, replace the `"triage"` block in `SYSTEM_TEMPLATE` (lines 86–90):
```python
  "triage": {{
    "status": "ok|warning|flag",
    "findings": "Obserwacje - dopasowanie roli do profilu i trajektorii, pierwsze sygnały",
    "evidence": "Cytat lub fakt z ogłoszenia - wymagany gdy status=flag, null w pozostałych przypadkach",
    "ghost_job_risk": "low|medium|high",
    "ghost_job_signals": "Konkretne sygnały uzasadniające ghost_job_risk lub null jeśli low"
  }},
```

- [ ] **Step 4: Verify file parses without errors**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from analyzer import build_system; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add analyzer.py
git commit -m "feat: add ghost job legitimacy detection to Triage layer"
```

---

## Task 2: Add compensation signal to Business layer

**Files:**
- Modify: `analyzer.py:49` (business layer description)
- Modify: `analyzer.py:97-101` (JSON format — business object)

- [ ] **Step 1: Replace business layer description**

In `analyzer.py`, replace line 49:
```
3. BIZNESOWA - model przychodowy vs deklarowana misja, struktura finansowania, presja VC/PE, PE roll-up playbook
```
With:
```
3. BIZNESOWA - model przychodowy vs deklarowana misja, struktura finansowania, presja VC/PE, PE roll-up playbook.
   Dodatkowo oceń SYGNAŁY KOMPENSACYJNE z treści ogłoszenia:
   - Czy podany zakres wynagrodzenia? Jeśli tak — oceń vs rynkowe stawki dla tej roli i lokalizacji
   - "Competitive salary" bez konkretu = sygnał niskiego widełkowego transparentności
   - Rażąca dysproporcja: wymagania seniorskie + wynagrodzenie juniora
   compensation_signal: "disclosed_above_market"|"disclosed_market"|"disclosed_below_market"|"undisclosed"|"unknown"
```

- [ ] **Step 2: Update business JSON format block**

In `analyzer.py`, replace the `"business"` block inside `"layers"`:
```python
    "business": {{
      "status": "ok|warning|flag",
      "findings": "Model biznesowy, finansowanie, inwestorzy",
      "evidence": "Cytat lub fakt z ogłoszenia - wymagany gdy status=flag, null w pozostałych przypadkach",
      "compensation_signal": "disclosed_above_market|disclosed_market|disclosed_below_market|undisclosed|unknown",
      "compensation_note": "Konkretna notatka np. '15-20k PLN gross, rynkowo 18-24k dla tego poziomu' lub null"
    }},
```

- [ ] **Step 3: Verify**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from analyzer import SYSTEM_TEMPLATE; assert 'compensation_signal' in SYSTEM_TEMPLATE; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add analyzer.py
git commit -m "feat: add compensation signal inference to Business layer"
```

---

## Task 3: Add role archetype to Triage layer

**Files:**
- Modify: `analyzer.py:47` region (triage description — already extended in Task 1)
- Modify: `analyzer.py` — triage JSON block (add `role_archetype` field)

- [ ] **Step 1: Add archetype definition to triage layer description**

In `analyzer.py`, append to the triage layer description (after the ghost job paragraph added in Task 1):
```
   Określ ARCHETYPE roli: engineering|pm|design|data|devrel|leadership|operations|sales|other
   Bazuj na tytule stanowiska i wymaganiach JD, nie na deklarowanej "misji".
```

- [ ] **Step 2: Add role_archetype to triage JSON block**

In `analyzer.py`, update the `"triage"` block to include:
```python
  "triage": {{
    "status": "ok|warning|flag",
    "findings": "Obserwacje - dopasowanie roli do profilu i trajektorii, pierwsze sygnały",
    "evidence": "Cytat lub fakt z ogłoszenia - wymagany gdy status=flag, null w pozostałych przypadkach",
    "ghost_job_risk": "low|medium|high",
    "ghost_job_signals": "Konkretne sygnały uzasadniające ghost_job_risk lub null jeśli low",
    "role_archetype": "engineering|pm|design|data|devrel|leadership|operations|sales|other"
  }},
```

- [ ] **Step 3: Verify**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from analyzer import SYSTEM_TEMPLATE; assert 'role_archetype' in SYSTEM_TEMPLATE; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add analyzer.py
git commit -m "feat: add role archetype classification to Triage layer"
```

---

## Task 4: Add numeric fit score to Fit layer

**Files:**
- Modify: `analyzer.py:56-57` (fit layer description)
- Modify: `analyzer.py:113-119` (fit JSON block)

- [ ] **Step 1: Extend fit layer description**

In `analyzer.py`, replace line 57 (fit layer):
```
6. DOPASOWANIE - mocne strony kandydata vs wymagania, luki, co wzmocnić w aplikacji
```
With:
```
6. DOPASOWANIE - mocne strony kandydata vs wymagania, luki, co wzmocnić w aplikacji.
   Dodatkowo przyznaj score: liczba 1.0–5.0 (jeden decimal).
   5.0 = idealne dopasowanie CV do JD bez luk. 1.0 = brak dopasowania.
   4.5+ = aplikuj od razu. 4.0–4.4 = dobre dopasowanie. 3.5–3.9 = warunkowe. Poniżej 3.5 = odradzam.
   Score musi być spójny z gaps i verdict — nie przyznawaj 4.5 przy liście istotnych luk.
```

- [ ] **Step 2: Update fit JSON block**

In `analyzer.py`, replace the `"fit"` block:
```python
  "fit": {{
    "status": "ok|warning|flag",
    "score": 3.5,
    "strengths": "Co z profilu kandydata pasuje do tej roli",
    "gaps": "Czego brakuje lub co jest niedopasowane",
    "improve": "Co podkreślić/uzupełnić w aplikacji jeśli warto aplikować"
  }},
```

- [ ] **Step 3: Verify**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from analyzer import SYSTEM_TEMPLATE; assert '\"score\": 3.5' in SYSTEM_TEMPLATE; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add analyzer.py
git commit -m "feat: add numeric fit score (1.0-5.0) to Fit layer"
```

---

## Task 5: Translate app.py flash messages

**Files:**
- Modify: `app.py` (all `flash()` calls)

- [ ] **Step 1: Replace all Polish flash strings**

In `app.py`, apply these replacements:

```python
# Line 89 — login failure
flash("Invalid username or password.")

# Line 108 — registration disabled
flash("Registration is disabled. Contact the administrator.")

# Line 116 — missing fields
flash("Please fill in all fields.")

# Line 119 — password mismatch
flash("Passwords do not match.")

# Line 121 — password too short
flash("Password must be at least 6 characters.")

# Line 123 — username taken
flash("That username is already taken.")

# Line 127 — account created
flash("Account created. Complete your profile in Settings.")

# Line 408 — job not found
flash("Analysis not found.")

# Line 444 — settings saved
flash("Profile saved.")
```

- [ ] **Step 2: Verify app loads**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "style: translate flash messages to English"
```

---

## Task 6: Translate base.html

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 1: Apply all translations**

Replace the entire `<nav>` block and surrounding strings in `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
```

Nav links (replace the nav-links div):
```html
  <div class="nav-links">
    <a href="{{ url_for('dashboard') }}" {% if request.endpoint == 'dashboard' %}class="active"{% endif %}>Analyze</a>
    <a href="{{ url_for('history') }}" {% if request.endpoint in ('history','job_detail') %}class="active"{% endif %}>History</a>
    <a href="{{ url_for('settings') }}" {% if request.endpoint == 'settings' %}class="active"{% endif %}>Settings</a>
    <a href="{{ url_for('export') }}">Export CSV</a>
    <a href="{{ url_for('logout') }}">Logout</a>
    <button class="btn-theme-toggle" id="theme-toggle" title="Toggle theme"></button>
  </div>
```

Theme toggle JS strings (in the inline script):
```js
btn.title = t === 'light' ? 'Dark mode' : 'Light mode';
```

Footer:
```html
  <a href="/changelog">Changelog</a>
```
(already English — no change needed)

- [ ] **Step 2: Verify template renders (start dev server and check nav)**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from app import app; client = app.test_client(); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add templates/base.html
git commit -m "style: translate base.html nav to English"
```

---

## Task 7: Translate login.html and register.html

**Files:**
- Modify: `templates/login.html`
- Modify: `templates/register.html`

- [ ] **Step 1: Replace login.html content**

```html
{% extends "base.html" %}
{% block title %}Login — Job Screener{% endblock %}
{% block content %}
<div class="auth-wrap">
  <div style="margin-bottom:32px;">
    <div class="auth-brand">Job Screener</div>
    <div class="auth-sub">Ethical job offer analysis</div>
  </div>
  <div class="card">
    <form method="POST" style="padding:24px;">
      <div class="field">
        <label>Username</label>
        <input type="text" name="username" autocomplete="username" autofocus required>
      </div>
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" autocomplete="current-password" required>
      </div>
      <button type="submit" class="btn btn-primary" style="width:100%">Log in →</button>
    </form>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Read register.html and apply same pattern**

Read `templates/register.html` first, then translate all labels:
- `Rejestracja` → `Register`
- `Nazwa użytkownika` → `Username`
- `Hasło` → `Password`
- `Powtórz hasło` → `Repeat password`
- `Zarejestruj się →` → `Create account →`
- Any `auth-sub` subtitle → `"Ethical job offer analysis"`

- [ ] **Step 3: Commit**

```bash
git add templates/login.html templates/register.html
git commit -m "style: translate login and register templates to English"
```

---

## Task 8: Translate settings.html

**Files:**
- Modify: `templates/settings.html`

- [ ] **Step 1: Apply all translations**

Replace content in `templates/settings.html`:

Page header:
```html
<div class="page-title">Profile settings</div>
<p class="page-sub">Your CV and criteria are used in every analysis. The more detail, the better the results.</p>
```

CV field:
```html
  <div class="field">
    <label>CV — experience and skills</label>
    <div class="field-hint">Write as continuous text or bullet points. More context = better job matching.</div>
    <textarea name="cv" rows="14" placeholder="E.g.:&#10;Specialization: product discovery, facilitation, advisory&#10;&#10;Experience:&#10;- Senior Product Manager @ CompanyX (2022–2025): discovery workshops, AI product strategy...&#10;- Product Designer @ CompanyY (2019–2022): e-commerce, supply chain...&#10;&#10;Skills: user research, journey mapping, stakeholder alignment...&#10;Languages: Polish (native), English (fluent)">{{ user.cv or '' }}</textarea>
  </div>
```

Zero list field:
```html
  <div class="field">
    <label>Zero Rule — auto-reject without analysis</label>
    <div class="field-hint">Industries, company categories, or criteria that disqualify a listing immediately.</div>
    <textarea name="zero_list" rows="8" placeholder="E.g.:&#10;- Alcohol, tobacco, gambling&#10;- Arms and defense&#10;- Finance (banks, fintechs, trading)">{{ user.zero_list or '' }}</textarea>
  </div>
```

Yellow list field:
```html
  <div class="field">
    <label>Yellow list — needs attention, but not auto-rejected</label>
    <div class="field-hint">Industries that automatically set verdict to "needs review" — analysis continues.</div>
    <textarea name="yellow_list" rows="5" placeholder="E.g.:&#10;- Insurance (when not core business)&#10;- Fintech (verify revenue model)&#10;- Public / government sector">{{ user.yellow_list or '' }}</textarea>
  </div>
```

Criteria field:
```html
  <div class="field">
    <label>Additional criteria and priorities</label>
    <div class="field-hint">Preferred sectors, role types, cultural red flags, etc.</div>
    <textarea name="criteria" rows="6" placeholder="E.g.:&#10;Prefer: healthcare, social impact, AI ethics&#10;Avoid: execution PM without discovery, growth PM (A/B tests as core)&#10;Red flag: Glassdoor below 3.5 with a clear downward trend">{{ user.criteria or '' }}</textarea>
  </div>
```

Buttons:
```html
    <button type="submit" class="btn btn-primary">Save profile →</button>
    <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">Cancel</a>
```

Export section:
```html
<div class="export-section">
  <div class="section-label">Data export</div>
  <p class="page-sub" style="margin-bottom:16px;">Download all your analyses as a CSV file (opens in Excel and Google Sheets).</p>
  <a href="{{ url_for('export') }}" class="btn btn-secondary">Download CSV →</a>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add templates/settings.html
git commit -m "style: translate settings.html to English"
```

---

## Task 9: Translate dashboard.html

**Files:**
- Modify: `templates/dashboard.html`

- [ ] **Step 1: Translate page header and notices**

Replace:
```html
{% block title %}Analyze — Job Screener{% endblock %}
```

```html
<div class="page-title">Analyze a listing</div>
<p class="page-sub">Provide a URL and/or job description text. Both are saved to the database.</p>
```

Notices:
```html
<div class="notice warn">⚠ No API key. Contact the application administrator.</div>
```
```html
<div class="notice">No CV in your profile yet. <a href="{{ url_for('settings') }}" class="link-accent">Add it in Settings →</a></div>
```

- [ ] **Step 2: Translate form labels and button**

```html
    <div class="field">
      <label>Job listing URL</label>
      <input type="url" id="input-url" placeholder="https://www.linkedin.com/jobs/view/...">
    </div>
    <div class="field">
      <label>Job description text</label>
      <textarea id="input-text" rows="8" placeholder="Paste the job description — required when the link is inaccessible (LinkedIn, Indeed, etc.)"></textarea>
    </div>
    <button class="btn btn-primary" id="analyze-btn" onclick="runAnalysis()" {% if not has_api_key %}disabled{% endif %}>
      Analyze listing →
    </button>
```

Loading notice:
```html
<div id="loading" class="notice" style="display:none;">
  <span class="spinner"></span> Analyzing — may take 20–40 seconds…
</div>
```

- [ ] **Step 3: Translate recent jobs table**

```html
  <div class="section-label">Recent analyses</div>
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Role</th>
        <th>Company</th>
        <th>Verdict</th>
      </tr>
    </thead>
```

Table badge labels (Jinja dict):
```html
{{ {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'}.get(j.verdict, j.verdict) }}
```

Applied / company_rejected badges:
```html
{%- if j.company_rejected %}<span class="badge badge-company_rejected" data-verdict="{{ j.verdict }}">Rejected by company</span>
{%- elif j.applied %}<span class="badge badge-applied" data-verdict="{{ j.verdict }}">Applied</span>
{%- else %}<span class="badge badge-{{ j.verdict }}" data-verdict="{{ j.verdict }}">{{ {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'}.get(j.verdict, j.verdict) }}</span>{% endif %}
```

Company fallback:
```html
<td class="fw-500">{{ j.company or 'Unknown' }}</td>
```

"See all" link:
```html
    <a href="{{ url_for('history') }}" class="td-mono td-dim">See all ({{ jobs|length }}) →</a>
```

- [ ] **Step 4: Translate JS label maps and inline strings**

In the `<script>` block, replace:
```js
const vLabel = v => ({rejected:'Rejected', warning:'Needs review', worth_considering:'Worth considering'}[v]||v);
const sLabel = s => ({ok:'No issues', warning:'Needs review', flag:'Red flag'}[s]||'—');
```

`renderResult` fitFindings labels:
```js
  const fitFindings = [
    fit.strengths ? '<strong>Strengths:</strong> '+fit.strengths : '',
    fit.gaps      ? '<strong>Gaps:</strong> '+fit.gaps : '',
    fit.improve   ? '<strong>To strengthen:</strong> '+fit.improve : ''
  ].filter(Boolean).join('<br><br>');
```

Layer names in `renderResult`:
```js
  ${mkLayer('triage','Triage', r.triage?.status, r.triage?.findings)}
  ${mkLayer('prod','Product layer', l.product?.status, l.product?.findings)}
  ${mkLayer('biz','Business layer', l.business?.status, l.business?.findings)}
  ${mkLayer('rep','Reputation layer', l.reputation?.status, l.reputation?.findings)}
  ${mkLayer('val','Values layer', l.values?.status, l.values?.findings)}
  ${mkLayer('fit','Skills fit', fit.status, fitFindings)}
  ${mkLayer('gut','Gut feeling', 'unknown', r.gut_feeling)}
```

Source layer in `renderResult`:
```js
      <div class="layer-name">Job source</div>
      <div class="layer-status-label">${sourceUrl ? 'URL' : ''}${sourceUrl && sourceText ? ' + ' : ''}${sourceText ? 'Text' : ''}</div>
```

```js
        ${sourceUrl ? `<div class="source-url-label">URL</div><a href="${sourceUrl}" target="_blank" class="source-url-link">${sourceUrl}</a>` : ''}
        ${sourceText ? `<div class="source-url-label" class="${sourceUrl?'source-preview-label-gap':''}">Text</div><div class="source-text" class="source-preview-text">${sourceText.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</div>` : ''}
```

Status select optgroups:
```js
  const verdictOpts = `
    <optgroup label="Analysis">
      <option value="worth_considering" ${r.verdict==='worth_considering'?'selected':''}>Worth considering</option>
      <option value="warning" ${r.verdict==='warning'?'selected':''}>Needs review</option>
      <option value="rejected_soft" ${isSoftRejected?'selected':''}>Rejected (AI)</option>
      <option value="rejected" ${r.verdict==='rejected'&&!isSoftRejected?'selected':''}>Rejected</option>
    </optgroup>
    <optgroup label="Application">
      <option value="applied">Applied</option>
    </optgroup>`;
```

`setVerdictInline` labels:
```js
  const labels = {rejected:'Rejected', rejected_soft:'Rejected', warning:'Needs review', worth_considering:'Worth considering', applied:'Applied'};
```

`SCRAPE_ERRORS` map:
```js
const SCRAPE_ERRORS = {
  timeout:  { title: 'Server did not respond', fallback: true },
  notfound: { title: 'Listing not found (404)', fallback: false },
  blocked:  { title: 'Content inaccessible', fallback: true },
  network:  { title: 'Network error', fallback: true },
};
```

Inline error/status strings in `runAnalysis`:
```js
      statusEl.textContent = `⚠ This listing was already analyzed (${chkData.analyzed_at}). Analysis will run again.`;
      statusEl.textContent = '✓ New listing — not yet in the database.';
      // scrape error fallback text:
      (info.fallback ? '<br><br>Paste the job description in the text field above and try again.' : '');
      // duplicate notice:
      <div class="td-mono" duplicate-label">⚠ This listing was already analyzed</div>
      <a href="/job/${p.id}" class="btn btn-secondary btn-sm">View previous analysis →</a>
      <button class="btn btn-secondary btn-sm" onclick="runAnalysis(true)">Analyze again</button>
      // error prefix:
      document.getElementById('error-box').textContent = 'Error: ' + data.error;
      document.getElementById('error-box').textContent = 'Connection error: ' + e.message;
```

Modal loading strings:
```js
  body.innerHTML = '<div class="modal-loading">Loading…</div>';
  body.innerHTML = '<div class="modal-loading">Loading error.</div>';
  body.innerHTML = '<div class="modal-loading">Connection error.</div>';
```

Badge update in `updateTableRow`:
```js
      badge.textContent = 'Applied';
      badge.textContent = 'Rejected by company';
      badge.textContent = {rejected:'Rejected', warning:'Needs review', worth_considering:'Worth considering'}[verdict] || verdict;
```

`confirmDelete` confirm dialog:
```js
  if (!confirm('Delete this analysis? This action cannot be undone.')) return;
  alert('Error: ' + (data.error || 'unknown'));
  alert('Connection error: ' + e.message);
```

`reanalyze` status strings:
```js
  if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }
  if (statusEl) { statusEl.style.display='block'; statusEl.textContent='Analysis complete. Redirecting…'; }
  statusEl.textContent='Error: '+(data.error||'unknown');
  if (btn) { btn.disabled=false; btn.textContent='Re-analyze'; }
  statusEl.textContent='Connection error: '+e.message;
```

`saveUrl` strings:
```js
    if (statusEl) { statusEl.style.color='#e74c3c'; statusEl.style.display='block'; statusEl.textContent='Please enter a valid URL.'; }
    if (statusEl) { statusEl.style.color='#3dba73'; statusEl.style.display='block'; statusEl.textContent='URL saved.'; }
    if (statusEl) { statusEl.style.color='#e74c3c'; statusEl.style.display='block'; statusEl.textContent=data.error||'Save error.'; }
    if (statusEl) { statusEl.style.color='#e74c3c'; statusEl.style.display='block'; statusEl.textContent='Connection error.'; }
```

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard.html
git commit -m "style: translate dashboard.html to English"
```

---

## Task 10: Translate history.html

**Files:**
- Modify: `templates/history.html`

- [ ] **Step 1: Translate page header**

```html
{% block title %}History — Job Screener{% endblock %}
```

```html
<div class="page-title">Analysis history</div>
<p class="page-sub">All analyzed listings. <a href="{{ url_for('export') }}" style="color:var(--accent);">Download CSV →</a></p>
```

Empty state:
```html
<div class="notice">No analyses yet. <a href="{{ url_for('dashboard') }}" style="color:var(--accent);">Analyze your first listing →</a></div>
```

- [ ] **Step 2: Translate filter bar buttons**

```html
<div class="filter-bar">
  <span class="filter-label">Show:</span>
  <button class="filter-btn active fb-worth_considering" onclick="toggleFilter('worth_considering', this)">Worth considering</button>
  <button class="filter-btn active fb-warning" onclick="toggleFilter('warning', this)">Needs review</button>
  <button class="filter-btn active fb-rejected_soft" onclick="toggleFilter('rejected_soft', this)">Rejected (AI)</button>
  <button class="filter-btn active fb-rejected" onclick="toggleFilter('rejected', this)">Rejected</button>
  <button class="filter-btn active fb-applied" onclick="toggleFilter('applied', this)">Applied</button>
  <button class="filter-btn active fb-company_rejected" onclick="toggleFilter('company_rejected', this)">Rejected by company</button>
</div>
```

- [ ] **Step 3: Translate table headers**

```html
    <tr>
      <th>Date</th>
      <th>Role</th>
      <th>Company</th>
      <th>Verdict</th>
      <th>L0</th>
      <th>Triage</th>
      <th>Product</th>
      <th>Business</th>
      <th>Reput.</th>
      <th>Values</th>
      <th>Fit</th>
      <th>Status</th>
    </tr>
```

- [ ] **Step 4: Translate table cell labels**

Badge labels (Jinja dict):
```html
{{ {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'}.get(j.verdict, j.verdict) }}
```

Applied/rejected badges:
```html
{%- if j.company_rejected %}<span class="badge badge-company_rejected" data-verdict="{{ j.verdict }}">Rejected by company</span>
{%- elif j.applied %}<span class="badge badge-applied" data-verdict="{{ j.verdict }}">Applied</span>
{%- else %}...{% endif %}
```

Company fallback:
```html
<td class="fw-500">{{ j.company or 'Unknown' }}</td>
```

Zero list cell:
```html
<td class="td-mono {% if j.zero_list_hit %}td-red{% else %}td-dim{% endif %}">{{ 'YES' if j.zero_list_hit else '—' }}</td>
```

- [ ] **Step 5: Translate JS strings**

Modal loading:
```js
  body.innerHTML = '<div class="modal-loading">Loading…</div>';
  body.innerHTML = '<div class="modal-loading">Loading error.</div>';
  body.innerHTML = '<div class="modal-loading">Connection error.</div>';
```

`updateTableRow` badge labels:
```js
      badge.textContent = 'Applied';
      badge.textContent = 'Rejected by company';
      badge.textContent = {rejected:'Rejected', warning:'Needs review', worth_considering:'Worth considering'}[verdict] || verdict;
```

`setStatus` error:
```js
      if (el) { el.className='notice warn'; el.style.display='block'; el.textContent='Error: '+(data.error||'unknown'); }
```

`confirmDelete`:
```js
  if (!confirm('Delete this analysis? This action cannot be undone.')) return;
  alert('Error: ' + (data.error || 'unknown'));
  alert('Connection error: ' + e.message);
```

`reanalyze` strings:
```js
  if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }
  if (statusEl) { statusEl.style.display='block'; statusEl.textContent='Analysis complete. Redirecting…'; }
  statusEl.textContent='Error: '+(data.error||'unknown');
  if (btn) { btn.disabled=false; btn.textContent='Re-analyze'; }
  statusEl.textContent='Connection error: '+e.message;
```

`saveUrl` strings (same as dashboard):
```js
    statusEl.textContent='Please enter a valid URL.';
    statusEl.textContent='URL saved.';
    statusEl.textContent=data.error||'Save error.';
    statusEl.textContent='Connection error.';
```

- [ ] **Step 6: Commit**

```bash
git add templates/history.html
git commit -m "style: translate history.html to English"
```

---

## Task 11: Translate job_partial.html

**Files:**
- Modify: `templates/job_partial.html`

- [ ] **Step 1: Translate verdict/status label dicts at top of file**

Replace lines 1–3:
```html
{% set vl = {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'} %}
{% set sl = {'ok':'No issues','warning':'Needs review','flag':'Red flag'} %}
{% set sc = {'ok':'ok','warning':'warning','flag':'flag'} %}
```

- [ ] **Step 2: Translate action bar and buttons**

```html
    <label class="verdict-select-label">Status:</label>
    <select id="status-select" class="verdict-select" onchange="setStatus(this.value)">
      <optgroup label="Analysis">
        <option value="worth_considering" {% if cur_status == 'worth_considering' %}selected{% endif %}>Worth considering</option>
        <option value="warning"           {% if cur_status == 'warning' %}selected{% endif %}>Needs review</option>
        <option value="rejected_soft"     {% if cur_status == 'rejected_soft' %}selected{% endif %}>Rejected (AI)</option>
        <option value="rejected"          {% if cur_status == 'rejected' %}selected{% endif %}>Rejected</option>
      </optgroup>
      <optgroup label="Application">
        <option value="applied"           {% if cur_status == 'applied' %}selected{% endif %}>Applied</option>
        <option value="company_rejected"  {% if cur_status == 'company_rejected' %}selected{% endif %}>Rejected by company</option>
      </optgroup>
    </select>
```

```html
  <button id="reanalyze-btn" class="btn btn-secondary btn-sm" onclick="reanalyze()">Re-analyze</button>
  <button class="btn btn-secondary btn-sm btn-danger" onclick="confirmDelete()">Delete</button>
```

- [ ] **Step 3: Translate card header labels**

Badge labels using `vl` dict (already updated in Step 1).

Applied/rejected badges:
```html
{%- if job.company_rejected %}<span class="badge badge-company_rejected" data-verdict="{{ job.verdict }}">Rejected by company</span>
{%- elif job.applied %}<span class="badge badge-applied" data-verdict="{{ job.verdict }}">Applied</span>
{%- else %}<span class="badge badge-{{ job.verdict }}" data-verdict="{{ job.verdict }}">{{ vl.get(job.verdict, job.verdict) }}</span>{% endif %}
```

Company fallback:
```html
    <div class="card-company">{{ job.company or 'Unknown' }}</div>
```

Zero list / yellow list meta:
```html
    <div class="card-meta text-red">⛔ Zero rule: {{ job.zero_list_reason }}</div>
    <div class="evidence"><span class="evidence-label">Evidence from listing</span>{{ raw.get('zero_list_evidence') }}</div>
    <div class="card-meta text-yellow">⚠ Yellow list: {{ raw.get('yellow_list_reason') }}</div>
```

Date meta:
```html
      Analyzed: {{ job.analyzed_at }}
      &nbsp;·&nbsp; <span class="text-accent">✕ Rejected by company: {{ job.company_rejected_at }}</span>
      &nbsp;·&nbsp; <span class="text-green">✓ Applied: {{ job.applied_at }}</span>
```

- [ ] **Step 4: Translate layer names**

```html
  {{ layer('triage','Triage', job.triage_status, job.triage_findings,
    raw.get('triage',{}).get('evidence')) }}
  {{ layer('prod','Product layer', job.product_status, job.product_findings,
    raw.get('layers',{}).get('product',{}).get('evidence')) }}
  {{ layer('biz','Business layer', job.business_status, job.business_findings,
    raw.get('layers',{}).get('business',{}).get('evidence')) }}
  {{ layer('rep','Reputation layer', job.reputation_status, job.reputation_findings,
    raw.get('layers',{}).get('reputation',{}).get('evidence')) }}
  {{ layer('val','Values layer', job.values_status, job.values_findings,
    raw.get('layers',{}).get('values',{}).get('evidence')) }}
```

Fit layer:
```html
          <div class="layer-name">Skills fit</div>
```

Fit body labels:
```html
      {% if job.fit_strengths %}<strong>Strengths:</strong> {{ job.fit_strengths }}<br><br>{% endif %}
      {% if job.fit_gaps %}<strong>Gaps:</strong> {{ job.fit_gaps }}<br><br>{% endif %}
      {% if job.fit_improve %}<strong>To strengthen:</strong> {{ job.fit_improve }}{% endif %}
```

Evidence label in macro:
```html
      <div class="evidence"><span class="evidence-label">Evidence from listing</span>{{ evidence }}</div>
```

Source layer:
```html
          <div class="layer-name">Job source</div>
          <div class="layer-status-label">
            {%- if job.source_full and job.source_full.startswith('http') -%}URL
            {%- elif job.source_full -%}Job description text
            {%- else -%}No data{%- endif -%}
          </div>
```

Source layer body:
```html
          <div class="source-url-hint">URL may be inactive if the listing was removed.</div>
          <div class="source-url-label">Listing URL</div>
          <button onclick="showUrlEdit()" class="btn-inline">change</button>
          <div class="source-url-label">Add listing URL</div>
          <button onclick="saveUrl()" class="btn btn-secondary btn-sm">Save URL</button>
          <div class="source-old-hint">Full text unavailable — listing was analyzed before this feature was introduced.</div>
          <div class="source-none">No source saved.</div>
```

- [ ] **Step 5: Commit**

```bash
git add templates/job_partial.html
git commit -m "style: translate job_partial.html to English"
```

---

## Task 12: Translate job_detail.html

**Files:**
- Modify: `templates/job_detail.html`

- [ ] **Step 1: Translate navigation and action bar**

```html
  <a href="{{ url_for('history') }}" class="detail-nav-back">← History</a>
```

Status select (same translations as job_partial.html Task 11 Step 2):
```html
      <optgroup label="Analysis">
        <option value="worth_considering" ...>Worth considering</option>
        <option value="warning" ...>Needs review</option>
        <option value="rejected_soft" ...>Rejected (AI)</option>
        <option value="rejected" ...>Rejected</option>
      </optgroup>
      <optgroup label="Application">
        <option value="applied" ...>Applied</option>
        <option value="company_rejected" ...>Rejected by company</option>
      </optgroup>
```

Buttons:
```html
    <button id="reanalyze-btn" class="btn btn-secondary btn-sm" onclick="reanalyze()">Re-analyze</button>
    <button class="btn btn-secondary btn-sm btn-danger" onclick="confirmDelete()">Delete</button>
```

- [ ] **Step 2: Translate verdict/status label dicts**

```html
{% set vl = {'rejected':'Rejected','warning':'Needs review','worth_considering':'Worth considering'} %}
{% set sl = {'ok':'No issues','warning':'Needs review','flag':'Red flag'} %}
```

- [ ] **Step 3: Translate card header, layer names, fit labels, source section**

Apply the same translations as job_partial.html Task 11 Steps 3–4, since job_detail.html mirrors job_partial.html for the card body.

- [ ] **Step 4: Translate JS strings**

`setStatus` verdictLabels map:
```js
  const verdictLabels = {
    worth_considering: 'Worth considering',
    warning: 'Needs review',
    rejected_soft: 'Rejected (AI)',
    rejected: 'Rejected',
    applied: 'Applied',
    company_rejected: 'Rejected by company',
  };
```

`setStatus` success/error:
```js
      statusEl.textContent = `Status changed to: ${verdictLabels[status] || status}`;
      statusEl.textContent = 'Error: ' + (data.error || 'unknown');
      statusEl.textContent = 'Connection error: ' + e.message;
```

`confirmDelete`:
```js
  if (!confirm('Delete this analysis? This action cannot be undone.')) return;
  alert('Error: ' + (data.error || 'unknown'));
  alert('Connection error: ' + e.message);
```

`saveUrl` strings:
```js
    statusEl.textContent = 'Please enter a valid URL.';
    statusEl.textContent = 'URL saved.';
    statusEl.textContent = data.error || 'Save error.';
    statusEl.textContent = 'Connection error.';
```

`reanalyze` strings:
```js
  btn.textContent = 'Analyzing…';
  statusEl.textContent = 'Analysis complete. New entry saved.';
  statusEl.textContent = 'Error: ' + (data.error || 'unknown error');
  btn.textContent = 'Re-analyze';
  statusEl.textContent = 'Connection error: ' + e.message;
```

- [ ] **Step 5: Commit**

```bash
git add templates/job_detail.html
git commit -m "style: translate job_detail.html to English"
```

---

## Task 13: DB migration — add role_archetype and fit_score columns

**Files:**
- Modify: `database.py:106-122` (the column-addition loop in `init_db()`)
- Modify: `database.py:368-408` (`save_job()` INSERT)

- [ ] **Step 1: Write a test first**

Create `tests/test_database.py`:

```python
import sqlite3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from pathlib import Path
import database

def _tmp_db(tmp_path):
    database.DB_PATH = Path(tmp_path) / "test.db"
    database.init_db()
    return database.get_conn()

def test_new_columns_exist(tmp_path):
    conn = _tmp_db(tmp_path)
    cur = conn.execute("PRAGMA table_info(jobs)")
    cols = {row['name'] for row in cur.fetchall()}
    assert 'role_archetype' in cols, "role_archetype column missing"
    assert 'fit_score' in cols, "fit_score column missing"
    conn.close()

def test_save_job_extracts_fields(tmp_path):
    conn = _tmp_db(tmp_path)
    conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("testuser", "salt:hash")
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE username='testuser'").fetchone()['id']

    result = {
        "company_name": "Acme",
        "role_title": "Senior PM",
        "verdict": "worth_considering",
        "verdict_summary": "Good fit.",
        "zero_list_hit": False,
        "zero_list_reason": None,
        "zero_list_evidence": None,
        "yellow_list_hit": False,
        "yellow_list_reason": None,
        "triage": {
            "status": "ok", "findings": "Good role.", "evidence": None,
            "ghost_job_risk": "low", "ghost_job_signals": None,
            "role_archetype": "pm"
        },
        "layers": {
            "product": {"status": "ok", "findings": "Fine.", "evidence": None,
                        "compensation_signal": "undisclosed", "compensation_note": None},
            "business": {"status": "ok", "findings": "Fine.", "evidence": None,
                         "compensation_signal": "undisclosed", "compensation_note": None},
            "reputation": {"status": "ok", "findings": "Fine.", "evidence": None},
            "values": {"status": "ok", "findings": "Fine.", "evidence": None},
        },
        "fit": {
            "status": "ok", "score": 4.2,
            "strengths": "Strong PM background.",
            "gaps": "No SaaS experience.",
            "improve": "Emphasize discovery work."
        },
        "gut_feeling": "Looks solid."
    }

    database.save_job(user_id, result, source_url="https://example.com/job/1")
    conn2 = database.get_conn()
    row = conn2.execute("SELECT * FROM jobs WHERE user_id=?", (user_id,)).fetchone()
    assert row['role_archetype'] == 'pm', f"Expected 'pm', got {row['role_archetype']}"
    assert abs(row['fit_score'] - 4.2) < 0.01, f"Expected 4.2, got {row['fit_score']}"
    conn2.close()

if __name__ == '__main__':
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_new_columns_exist(tmp)
        test_save_job_extracts_fields(tmp)
    print("All tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python tests/test_database.py
```
Expected: `AssertionError: role_archetype column missing`

- [ ] **Step 3: Add columns to init_db migration loop**

In `database.py`, in the `for col, tbl` loop (around line 106), add two entries:

```python
        for col, tbl in [
            ("source_full TEXT", "jobs"),
            ("source_hash TEXT", "jobs"),
            ("reasoning TEXT", "jobs"),
            ("job_url TEXT", "jobs"),
            ("applied INTEGER DEFAULT 0", "jobs"),
            ("applied_at DATE", "jobs"),
            ("verdict_confirmed INTEGER DEFAULT 0", "jobs"),
            ("company_rejected INTEGER DEFAULT 0", "jobs"),
            ("company_rejected_at DATE", "jobs"),
            ("role_archetype TEXT", "jobs"),        # ← new
            ("fit_score REAL", "jobs"),              # ← new
            # kept for migration chain: old DBs may not have this yet before rename
            ("lista_zolta TEXT DEFAULT ''", "users"),
        ]:
```

- [ ] **Step 4: Update save_job to extract the new fields**

In `database.py`, update the `INSERT INTO jobs` statement in `save_job()`.

Add `role_archetype, fit_score` to the column list and extract them from result:

Column list (add at end before `raw_json`):
```python
                    gut_feeling, source, source_full, source_hash, reasoning, job_url,
                    role_archetype, fit_score, raw_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
```

Values (add after `source_url.strip() or ""`):
```python
                (result.get("triage") or {}).get("role_archetype", None),
                fit.get("score", None),
                _json.dumps(result, ensure_ascii=False),
```

The full updated INSERT column list:
```python
            conn.execute("""
                INSERT INTO jobs (
                    user_id, company, role, verdict, verdict_confirmed, zero_list_hit, zero_list_reason,
                    triage_status, product_status, business_status,
                    reputation_status, values_status, fit_status,
                    verdict_summary, triage_findings, product_findings,
                    business_findings, reputation_findings, values_findings,
                    fit_strengths, fit_gaps, fit_improve,
                    gut_feeling, source, source_full, source_hash, reasoning, job_url,
                    role_archetype, fit_score, raw_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                user_id,
                d("company_name", ""),
                d("role_title", ""),
                d("verdict", ""),
                verdict_confirmed,
                zero_list_hit,
                d("zero_list_reason", ""),
                (result.get("triage") or {}).get("status", ""),
                l.get("product", {}).get("status", ""),
                l.get("business", {}).get("status", ""),
                l.get("reputation", {}).get("status", ""),
                l.get("values", {}).get("status", ""),
                fit.get("status", ""),
                d("verdict_summary", ""),
                (result.get("triage") or {}).get("findings", ""),
                l.get("product", {}).get("findings", ""),
                l.get("business", {}).get("findings", ""),
                l.get("reputation", {}).get("findings", ""),
                l.get("values", {}).get("findings", ""),
                fit.get("strengths", ""),
                fit.get("gaps", ""),
                fit.get("improve", ""),
                d("gut_feeling", ""),
                source_display,
                full_text,
                compute_hash(dedup_source),
                d("_reasoning", ""),
                source_url.strip() or "",
                (result.get("triage") or {}).get("role_archetype", None),
                fit.get("score", None),
                _json.dumps(result, ensure_ascii=False),
            ))
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python tests/test_database.py
```
Expected: `All tests passed.`

- [ ] **Step 6: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add role_archetype and fit_score columns to jobs table"
```

---

## Task 14: Display fit_score in job cards (partial + detail)

**Files:**
- Modify: `templates/job_partial.html`
- Modify: `templates/job_detail.html`

- [ ] **Step 1: Add fit_score chip to Skills fit layer in job_partial.html**

In `templates/job_partial.html`, inside the fit layer body (after the `{% if job.fit_strengths %}` block), add a score chip when the score is available from `raw_json`:

Replace the fit layer block:
```html
  <div class="layer">
    <div class="layer-hdr" onclick="tog('fit')">
      <div class="layer-left">
        <div class="dot dot-{{ sc.get(job.fit_status,'unknown') }}"></div>
        <div>
          <div class="layer-name">Skills fit</div>
          <div class="layer-status-label">{{ sl.get(job.fit_status,'—') }}{% if job.fit_score %} · <strong>{{ "%.1f"|format(job.fit_score) }}/5</strong>{% endif %}</div>
        </div>
      </div>
      <span class="chev" id="lc-fit">▶</span>
    </div>
    <div class="layer-body" id="lb-fit">
      {% if job.fit_strengths %}<strong>Strengths:</strong> {{ job.fit_strengths }}<br><br>{% endif %}
      {% if job.fit_gaps %}<strong>Gaps:</strong> {{ job.fit_gaps }}<br><br>{% endif %}
      {% if job.fit_improve %}<strong>To strengthen:</strong> {{ job.fit_improve }}{% endif %}
    </div>
  </div>
```

The score appears inline in the status label row: `"No issues · 4.2/5"`.

- [ ] **Step 2: Apply same change to job_detail.html**

In `templates/job_detail.html`, find the fit layer block and apply the same pattern:
```html
          <div class="layer-status-label">{{ sl.get(job.fit_status,'—') }}{% if job.fit_score %} · <strong>{{ "%.1f"|format(job.fit_score) }}/5</strong>{% endif %}</div>
```

- [ ] **Step 3: Verify**

Start the app and check a job detail page — the Skills fit layer header should show `No issues · 4.2/5` for records with a fit_score, and just `No issues` for old records.

```bash
cd "/Users/bartekjagniatkowski/Library/Mobile Documents/com~apple~CloudDocs/Work/Development/job-screener"
uv run python -c "from app import app; c = app.test_client(); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add templates/job_partial.html templates/job_detail.html
git commit -m "feat: display fit score in Skills fit layer header"
```

---

## Task 15: Display role_archetype badge in job cards

**Files:**
- Modify: `templates/job_partial.html`
- Modify: `templates/job_detail.html`
- Modify: `templates/dashboard.html` (inline result renderResult)
- Modify: `templates/history.html` (table row — optional column or tooltip)

- [ ] **Step 1: Add archetype badge to card header in job_partial.html**

In `templates/job_partial.html`, add after the verdict badge in `card-header--vertical`:

```html
    {%- if job.company_rejected %}<span class="badge badge-company_rejected" data-verdict="{{ job.verdict }}">Rejected by company</span>
    {%- elif job.applied %}<span class="badge badge-applied" data-verdict="{{ job.verdict }}">Applied</span>
    {%- else %}<span class="badge badge-{{ job.verdict }}" data-verdict="{{ job.verdict }}">{{ vl.get(job.verdict, job.verdict) }}</span>{% endif %}
    {% if job.role_archetype %}<span class="badge badge-archetype">{{ job.role_archetype }}</span>{% endif %}
```

- [ ] **Step 2: Add CSS for badge-archetype in static/style.css**

Find the badge section in `static/style.css` and add:

```css
.badge-archetype {
  border-color: var(--border);
  color: var(--muted);
  text-transform: uppercase;
  font-size: var(--fs-2xs);
  letter-spacing: 0.06em;
}
```

- [ ] **Step 3: Apply same badge to job_detail.html**

Same change as Step 1, in the `card-header--vertical` block.

- [ ] **Step 4: Add archetype to dashboard.html renderResult JS**

In `templates/dashboard.html`, in the `renderResult` function, after the verdict badge in the card header HTML string, add:

```js
      <span class="badge badge-${r.verdict}" id="result-badge">${vLabel(r.verdict)}</span>
      ${r.triage?.role_archetype ? `<span class="badge badge-archetype">${r.triage.role_archetype}</span>` : ''}
```

- [ ] **Step 5: Commit**

```bash
git add templates/job_partial.html templates/job_detail.html templates/dashboard.html static/style.css
git commit -m "feat: display role archetype badge in job cards"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Ghost job detection → Task 1 (analyzer.py)
- ✅ Compensation signal → Task 2 (analyzer.py)
- ✅ Role archetype → Tasks 3, 13, 15 (analyzer, DB, display)
- ✅ Numeric fit score → Tasks 4, 13, 14 (analyzer, DB, display)
- ✅ English UI translation → Tasks 5–12 (all templates + app.py)
- ✅ role_archetype DB column → Task 13
- ✅ fit_score DB column → Task 13

**Placeholder scan:** No TBD or TODO patterns found.

**Type consistency:**
- `role_archetype` used consistently as: JSON path `result.get("triage").get("role_archetype")`, DB column `role_archetype TEXT`, template `job.role_archetype`
- `fit_score` used consistently as: JSON path `fit.get("score")`, DB column `fit_score REAL`, template `job.fit_score`, format `"%.1f"|format(job.fit_score)`
- Badge CSS class: `badge-archetype` used consistently in templates and style.css
