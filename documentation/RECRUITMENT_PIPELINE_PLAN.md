# Recruitment Pipeline — Architecture Plan

**Status:** Design / Planning  
**Last Updated:** 2026-06-09  
**Module:** `ueipab_recruitment` (v17.0.3.6.0 — testing only)

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

Candidates continue emailing CVs naturally. HR reviews in Freescout and appends
`#<job_id>` to the conversation subject to assign the position.

**Subject line format:** append `#<id>` at the end.

```
Before: "Hola envio mi curriculum"
After:  "Hola envio mi curriculum #8"
```

The job IDs map to `hr.job` records in Odoo:

| ID | Position |
|----|----------|
| 2  | Asociada de Administración y RRHH |
| 5  | Asesor Especialista Académico |
| 6  | Docente |
| 8  | Auxiliar de Contabilidad y Administración |

(Full list via `hr.job` table — IDs are stable once created.)

### How `fs_cv_loader.py` handles it

1. **New conversation, no `#id` tag:** create `hr.applicant`, score CV, leave `job_id` blank,
   set `ueipab_eval_state='pending'`. HR tags in Freescout later.

2. **New conversation, `#id` tag present:** create applicant, set `job_id` immediately,
   score CV in context of that job position.

3. **Existing applicant (dedup by `ueipab_freescout_conv_id`), `#id` now in subject:**
   do NOT re-create. Only update `job_id` if currently blank (or different).
   Log the update. No re-scoring needed unless HR explicitly requests it.

4. **Invalid `#id` (no matching `hr.job`):** log warning, leave `job_id` blank, do not error.

### Regex

```python
m = re.search(r'#(\d+)\s*$', subject or '')
job_id = int(m.group(1)) if m else None
```

### Retroactive fix for already-scored applicants

Since `ueipab_freescout_conv_id` is stored on every `hr.applicant`, HR can fix any
previously-processed CV simply by updating the Freescout subject. The next cron run
picks it up and writes `job_id` to the existing record.

**Example:** Juan Ortuño (applicant id=30, Freescout conv id stored on record).  
HR appends `#8` to his Freescout conversation subject → next loader run sets `job_id=8`.

### Future Odoo button (optional — Phase 2+)

A "Asignar Cargo" button on the `hr.applicant` form that calls the Freescout API
(`PUT /api/conversations/{id}`) to append `#<selected_job_id>` to the subject
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

### Phase 3 — DB-driven question banks

- [ ] `ueipab.recruitment.quiz` + `ueipab.recruitment.quiz.question` models
- [ ] Migrate `_QUIZ_BANKS['contabilidad']` into DB records
- [ ] HR UI to add/edit questions per position
- [ ] `_load_quiz_questions()` reads from ORM

### Phase 4 — Production deploy

- [ ] All question banks validated (min 2 positions)
- [ ] End-to-end tested on at least 3 real candidates
- [ ] Add `recruitment` to production nginx allowlist
- [ ] Deploy module to `DB_UEIPAB`

---

## 7. Open Decisions

| Decision | Options | Notes |
|----------|---------|-------|
| Path B form: custom vs website module | Custom controller (recommended) vs `website_hr_recruitment` | Custom already started; avoids `website` dependency |
| Who tags Freescout subject: HR manual vs Odoo button | Manual for Phase 1; Odoo button optional for Phase 2+ | Manual is zero code; button is better UX |
| Subject tag format | `#<id>` (simple) vs `[JOB-<id>]` (explicit) | `#<id>` chosen — easy to type, easy to parse |
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
