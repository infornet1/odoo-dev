# Recruitment Pipeline — Architecture Plan

**Status:** Design / Planning  
**Last Updated:** 2026-06-10  
**Module:** `ueipab_recruitment` (v17.0.3.7.0 — testing only)

---

## 1. Current State (Prototype)

```
Candidate email → Freescout mailbox
                        ↓
              fs_cv_loader.py (cron)
                        ↓
          hr.applicant created + CV scored
          job_id: guessed from CV text heuristic
                        ↓
       OdooBot in-person eval (MCQ + conversational)
       question bank: hardcoded for 'contabilidad' only
                        ↓
          Dual-AI scoring → Manager summary tab
```

### Known Limitations

| # | Problem | Impact |
|---|---------|--------|
| 1 | Job position resolved by string heuristic (`if 'contab' in name`) | Breaks with any second position type |
| 2 | No structured intake — candidate email subject is ignored | HR has no visibility into what role a CV targets |
| 3 | No public-facing application UX | Requires candidates to know the email address; no official apply flow |
| 4 | MCQ question bank hardcoded as Python dict, one role only | Cannot add new positions without a code deploy |
| 5 | LinkedIn / structured resume import not supported | HR must forward CVs manually |

### Single-Position Hardcoding — Three Layers (audit 2026-06-10)

The prototype is single-position at **three** levels, not just the MCQ bank:

| Layer | Where | Covered by plan? |
|-------|-------|------------------|
| MCQ question bank | `_QUIZ_BANKS['contabilidad']` | ✅ Phase 3 |
| Phase-2 conversational questions | `_CONV_QUESTIONS` — all 7 turns are accounting-specific (IGTF, asientos, conciliación) | ✅ Phase 3 (scope expanded 2026-06-10) |
| AI scoring prompt | `_SCORING_PROMPT` — hardcodes the job title and accounting scoring criteria | ✅ Phase 3 (scope expanded 2026-06-10) |

Adding a second position requires all three to become per-`hr.job` data, otherwise
every candidate gets accounting questions and is scored against accounting criteria.
`_resolve_job_key()` currently returns `'contabilidad'` unconditionally.

### Eval Bot Audit — 2026-06-10 (Fable 5)

Read-only audit of `mail_bot_recruit_eval.py` + live-run data (applicant id=30, Jun 9 session).

**Latency (measured):** identity/MCQ/gate turns are instant (same-transaction reply;
no AI involved). Final scoring turn measured **~9.4s** (Claude Haiku ~6.4s + GPT-4o-mini
~3.0s, sequential, blocking an HTTP worker). Worst case with retries/timeouts: minutes —
mitigation deferred to Phase 4 (move scoring off the HTTP worker).

**Cost:** < $0.01 per candidate (AI only at final scoring; state machine elsewhere).

**Findings & status:**

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Claude JSON fence parse failure → score 0 → false "gaming" alarm (live run Jun 9) | High | ✅ Fixed v3.6.0 (parser); needs live re-validation |
| 2 | Scorer failure conflated with low consensus ("posible gaming") | High | ✅ Fixed v3.7.0 — new `failed` consensus state; GPT fallback feeds `ueipab_skill_score` when Claude fails |
| 3 | No session TTL — stale armed session hijacks the HR user's OdooBot DM indefinitely | Medium | ✅ Fixed v3.7.0 — 2h TTL + `cancelar` escape command |
| 4 | `evaluar` keyword setup flow was dead code (handler unreachable); `awaiting_choice` had no handler | Medium | ✅ Removed v3.7.0 — form button is the only entry point |
| 5 | Salary questions mid-eval recorded as technical answers (pollutes scored transcript) | Medium | ✅ Fixed v3.7.0 — deflection in MCQ + conversational turns; final turn keeps close-time ack |
| 6 | Sequential AI calls block 1 of 3 HTTP workers up to minutes on provider trouble | Medium | ⏳ Partial v3.7.0 (GPT timeout 60→30s); full fix (queued scoring) → Phase 4 |
| 7 | Quiz Q9 content questionable (IVA retention calendar applies to *sujetos pasivos especiales*, not ordinary taxpayers) | Low | ⏳ Pre-production: review bank with accountant |
| 8 | Quiz score not passed to scoring AIs (free context) | Low | ⏳ Backlog |
| 9 | Identity check trivially weak (`len > 5` passes) | Info | By design — in-person mode, supervisor verifies physical ID |

---

## 2. Target Architecture — Two Converging Paths

```
Path A (Email intake — evolve existing):          Path B (Native Odoo — new):
  Candidate emails CV to soporte@                   Candidate visits /recruitment/job/<id>
  Subject: free text                                 Fills apply form + attaches CV
  HR tags job in Freescout: appends #<job_id>        OR HR imports LinkedIn PDF via form
  fs_cv_loader detects #<job_id> in subject          Controller creates hr.applicant directly
  Updates job_id on existing applicant               Triggers CV scoring immediately
           ↓                                                      ↓
           └──────────────────────────────────────────────────────┘
                                    ↓
                        hr.applicant with correct job_id
                        CV scored (Tier A/B/C + salary risk)
                        Manager summary auto-generated
                                    ↓
                       Kanban pipeline → OdooBot eval
                       (question bank per job position)
                                    ↓
                       Dual-AI scoring → Manager review
```

---

## 3. Path A Enhancement — Job ID Tagging via Freescout Subject

### Mechanism

Candidates continue emailing CVs naturally. HR reviews in Freescout and edits
the conversation subject to include `[Applying for <job_id>]`.

**Subject line format:** `[Applying for <id>]` — anywhere in the subject, case-insensitive.

```
Before: "Hola envio mi curriculum"
After:  "Hola envio mi curriculum [Applying for 8]"

Before: (sin asunto)
After:  [Applying for 8]

Before: "solicitud empleo contabilidad"
After:  "solicitud empleo contabilidad [Applying for 8]"
```

**Why numeric ID over short codes:**
- Uses `hr.job.id` — already exists, no new field or setup required
- Guaranteed unique by DB primary key — no constraint to enforce
- Parser does a direct `hr.job.browse(n)` — zero ambiguity
- IDs are stable: `hr.job` records are archived, never deleted

**Job ID reference** (current positions):

| ID | Position |
|----|----------|
| 1  | Auxiliar de Soporte |
| 2  | Asociada de Administración y RRHH |
| 3  | Director |
| 4  | Profesora |
| 5  | Asesor Especialista Académico |
| 6  | Docente |
| 7  | Docente de Educación Deportiva |
| 8  | Auxiliar de Contabilidad y Administración |

This reference should be posted in a pinned Freescout note and on each
public job description page (`/recruitment/job/<id>` displays the ID in the URL).

### How `fs_cv_loader.py` handles it

1. **New conversation, no tag:** create `hr.applicant`, score CV, leave `job_id` blank,
   set `ueipab_eval_state='pending'`. HR tags in Freescout later.

2. **New conversation, tag present:** create applicant, set `job_id` immediately,
   score CV in context of that job position.

3. **Existing applicant (dedup by `ueipab_freescout_conv_id`), tag now in subject:**
   do NOT re-create. Only update `job_id` if currently blank (or different).
   Log the update. No re-scoring needed unless HR explicitly requests it.

4. **Invalid ID (no matching `hr.job`):** log warning, leave `job_id` blank, do not error.

### Regex

```python
m = re.search(r'\[Applying for\s+(\d+)\]', subject or '', re.IGNORECASE)
job_id = int(m.group(1)) if m else None
```

Can appear anywhere in the subject — no end-of-string anchoring needed.
Case-insensitive so `[applying for 8]` and `[APPLYING FOR 8]` both work.

### Retroactive fix for already-scored applicants

Since `ueipab_freescout_conv_id` is stored on every `hr.applicant`, HR can fix any
previously-processed CV simply by updating the Freescout subject. The next cron run
picks it up and writes `job_id` to the existing record.

**Example:** Juan Ortuño (applicant id=30, Freescout conv id=46987).  
HR edits subject to `[Applying for 8]` → next loader run sets `job_id=8` on his existing record.

### Future Odoo button (optional — Phase 2+)

A "Asignar Cargo" button on the `hr.applicant` form that calls the Freescout API
(`PUT /api/conversations/{id}`) to write `[Applying for <selected_job_id>]` into the subject
directly from Odoo, without HR needing to open Freescout manually.

---

## 4. Path B — Native Odoo Application Form

### Option B1: Extend existing `/recruitment/job/<id>` page (recommended)

The public job description page already exists (`ueipab_recruitment/controllers/main.py`).
Extend it with an apply form: name, email, phone, CV file upload.

On submit:
- Create `hr.applicant` with `job_id` already known (from the URL)
- Save CV attachment
- Trigger CV scoring directly (call the same scoring function as `fs_cv_loader`)
- Send acknowledgment email to candidate

**Pros:** zero new module dependencies, CV already linked to position on creation.  
**Cons:** custom-built form, not Odoo's standard recruitment UX.

### Option B2: Odoo native `website_hr_recruitment`

Install the `website_hr_recruitment` module to get Odoo's built-in public jobs page.

**Pros:** standard, maintained.  
**Cons:** requires `website` module; adds significant dependency weight; may conflict
with existing lightweight controller approach.

### LinkedIn import

CE does not have native LinkedIn API integration (Enterprise only).  
Realistic Path B approach for CE:

1. HR downloads candidate's LinkedIn profile as PDF
2. Opens "Nuevo Candidato" form in Odoo
3. Attaches the PDF — same Vision scoring pipeline as Freescout PDFs
4. Optionally pastes LinkedIn URL in a `ueipab_linkedin_url` field (display only)

---

## 5. Multi-Position Evaluation Banks

Currently `_QUIZ_BANKS` is a Python dict with one key (`contabilidad`).  
The code already has a roadmap comment: *"Future upgrade: swap `_load_quiz_questions()` to read from `ueipab.recruitment.quiz` ORM model"*.

### Phase 3 target model

```
ueipab.recruitment.quiz
  job_id (Many2one hr.job)        — links bank to position
  question_ids (One2many)         — ordered question list

ueipab.recruitment.quiz.question
  quiz_id (Many2one)
  sequence (Integer)
  question_text (Text)
  option_a/b/c/d (Char)
  correct_answer (Selection A/B/C/D)
  explanation (Text)              — shown in scoring notes
```

HR edits question banks from Odoo UI per position.  
`_load_quiz_questions(job_key)` replaced by an ORM query on `ueipab.recruitment.quiz`.

---

## 6. Phased Implementation Plan

### Phase 0 — Eval bot hardening (audit 2026-06-10) — ✅ DONE v17.0.3.7.0

- [x] Robust Claude JSON parser (fence-stripping + balanced-brace extraction) — v3.6.0
- [x] `failed` consensus state — scorer failure no longer reads as "posible gaming"
- [x] GPT score fallback into `ueipab_skill_score` when Claude fails (protects composite confidence)
- [x] Session TTL (2h) + `cancelar` escape command + applicant state reset on abort
- [x] Removed dead `evaluar` keyword flow (form button is the single entry point)
- [x] Mid-eval salary question deflection (MCQ + conversational; final-turn ack preserved)
- [x] GPT scoring timeout 60s → 30s
- [ ] **Live end-to-end validation run** — parser fix + welcome + salary ack + TTL have
      not yet been exercised in a real OdooBot session (pending HR/test candidate)

### Phase 1 — Fix Path A (subject-line job tagging)

- [ ] `fs_cv_loader.py`: parse `#<id>` from subject → set `job_id`
- [ ] Dedup path: update `job_id` on existing applicant if subject now has tag
- [ ] `_resolve_job_key()` in eval bot: replace string heuristic with `hr.job.id` lookup
- [ ] End result: prototype works correctly for any number of positions via email

### Phase 2 — Path B apply form

- [ ] Extend `/recruitment/job/<id>` with an apply form (name, email, phone, CV upload)
- [ ] Direct `hr.applicant` creation with `job_id` pre-filled
- [ ] Inline CV scoring trigger (no Freescout middleman)
- [ ] Candidate acknowledgment email

### Phase 3 — DB-driven evaluation profiles (scope expanded 2026-06-10)

All **three** hardcoded layers must become per-`hr.job` data, not just the MCQ bank:

- [ ] `ueipab.recruitment.quiz` + `ueipab.recruitment.quiz.question` models
- [ ] Migrate `_QUIZ_BANKS['contabilidad']` into DB records
- [ ] **Conversational question set per position** — `_CONV_QUESTIONS` → DB (ordered turns, optional dynamic follow-up flag)
- [ ] **Scoring criteria per position** — `_SCORING_PROMPT` job title + technical criteria → template fed from `hr.job` fields
- [ ] HR UI to add/edit questions per position
- [ ] `_load_quiz_questions()` reads from ORM

### Phase 4 — Production deploy

- [ ] All question banks validated (min 2 positions)
- [ ] **Quiz content review with accountant** (Q9 IVA retention calendar — see audit finding #7)
- [ ] End-to-end tested on at least 3 real candidates
- [ ] **Move dual-AI scoring off the HTTP worker** (queued job or cron) — only 3 workers in prod-like envs; worst-case provider trouble blocks one for minutes
- [ ] Add `recruitment` to production nginx allowlist
- [ ] Deploy module to `DB_UEIPAB`

---

## 7. Open Decisions

| Decision | Options | Notes |
|----------|---------|-------|
| Path B form: custom vs website module | Custom controller (recommended) vs `website_hr_recruitment` | Custom already started; avoids `website` dependency |
| Who tags Freescout subject: HR manual vs Odoo button | Manual for Phase 1; Odoo button optional for Phase 2+ | Manual is zero code; button is better UX |
| Subject tag format | `[Applying for <id>]` | **Decided** — English tag (intentional for staff EN exposure), numeric ID (no new field, PK guarantees uniqueness, stable for lifetime of position) |
| LinkedIn | PDF attach (Phase 2) vs URL field only (Phase 1) | URL field is 1 field, zero code |
| Conversational question banks per position | Hardcoded dict (Phase 1-2) vs DB model (Phase 3) | Hardcoded is fine until 3+ positions exist |

---

## 8. Files Reference

| File | Purpose |
|------|---------|
| `scripts/fs_cv_loader.py` | Freescout → hr.applicant CV intake (Path A) |
| `addons/ueipab_recruitment/models/hr_applicant.py` | Model fields + action_start_eval |
| `addons/ueipab_recruitment/models/mail_bot_recruit_eval.py` | OdooBot eval handler + dual-AI scoring |
| `addons/ueipab_recruitment/controllers/main.py` | Public routes: job page, confirm endpoint |
| `addons/ueipab_recruitment/wizard/hr_applicant_eval_invite_wizard.py` | In-person invite email + WA |
| `addons/ueipab_recruitment/views/hr_applicant_views.xml` | Evaluación IA tab UI |
