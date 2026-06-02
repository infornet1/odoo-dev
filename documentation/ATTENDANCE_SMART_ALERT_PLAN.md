# Smart Attendance Alert — Multi-Signal Confidence Engine

**Status:** Phase 1 complete — live as of 2026-06-02 07:30 VET  
**Created:** 2026-06-01  
**Origin:** Yudelys Brito false-positive case + teacher schedule analysis  
**Pending:** Employee guide update (inform staff of smart behavior) — 2026-06-02

---

## Problem Statement

The current `attendance_daily_alert.py` uses a single binary judge: did the employee check in on the Odoo kiosk, and did they work ≥ 5h? This produces systematic false positives for two populations:

1. **Teachers on the 07:00–12:45 schedule** — they leave at the end of the morning block per their contract, clock under 5h, and receive an alert even when they submitted student attendance for every class that day.
2. **Partial-contract specialist teachers** — teachers like Audrey García (7/14 school days) or Mairelsy Motta (6/14) only come in on their assigned days. The script has no awareness of which days they're expected.

Root cause: **the Odoo kiosk is treated as the judge, when it should be one witness among several.**

**Confirmed from data (May 2026):**
- Yudelys Brito: 14/14 school days with `asistencia_estudiante` submissions, consistently flagged for short hours.
- 25 teachers across 86 section assignments in `control_asistencias` — rich work-delivery signal already available, unused by the alert system.
- 14 school days in May produced alerts averaging 20–26 employees/day — majority were teachers with legitimate short-morning schedules.

---

## Core Design Principle

Replace the binary kiosk check with a **multi-signal confidence score** per employee per day.

The kiosk becomes a tiebreaker, not the judge. The question shifts from:
> "Did they tap the kiosk?"

To:
> "Is there enough evidence from all available signals that this person was doing their job today?"

---

## Architecture Decision

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Signal collection | Pure Python | Deterministic I/O — MySQL, SSH, Google API calls |
| Confidence scoring | Pure Python (weighted sum) | Auditable, tuneable, no LLM latency/cost |
| Action decision | Pure Python (thresholds) | Binary logic — no reasoning needed |
| Weekly pattern narrative | Claude Haiku (optional) | Synthesis of trends across employees — LLM adds value here |
| RRHH digest integration | Feeds `hr_leave_attendance_digest.py` | Reuses existing 08:00 VET digest pipeline |

**Not AI-driven. AI-enhanced at the reporting layer only.**

---

## Signal Inventory

| Signal | What it proves | Employee scope | Access | Status |
|--------|---------------|----------------|--------|--------|
| `asistencia_estudiante` submission | Teacher gave class, physically present | 25 teachers | MySQL `control_asistencias` | ✅ Live — Layer 1 |
| Mikrotik WiFi login (school hours) | Person on-campus network | 8 employees currently → expandable | SSH 172.28.10.10 | ✅ Live — needs mapping expansion |
| Google Classroom activity | Teacher posted/graded during school hours | All G Suite teachers | Classroom API + domain-wide delegation | 🔧 Needs OAuth setup |
| Work email sent (school hours window) | Active during 07:00–14:00 VET | All `@ueipab.edu.ve` | Google Admin Reports API | 🔧 Needs Admin Reports scope |
| Odoo kiosk check-in | Physical badge tap | All 44 | `hr.attendance` XML-RPC | ✅ Live |
| Odoo worked hours | Duration at desk | All 44 | `hr.attendance` XML-RPC | ✅ Live |

### Signal weights (v1 — tunable)

```python
SIGNAL_WEIGHTS = {
    'asistencia_submitted':      40,   # teachers only — definitive work delivery
    'google_classroom_activity': 30,   # active teaching signal
    'wifi_connected_school':     25,   # location signal
    'work_email_school_hours':   15,   # activity signal (weaker — could be remote)
    'odoo_checkin':              20,   # administrative confirmation
    'odoo_hours_adequate':       20,   # quality of Odoo record
}
```

### Action thresholds

| Score | Action | Rationale |
|-------|--------|-----------|
| ≥ 60 | **Silence** | Clearly working — kiosk miss is administrative, not a concern |
| 30–59 | **RRHH internal log only** | Something slightly off — HR awareness without alarming employee |
| < 30 | **Full alert** (employee + RRHH) | Genuine anomaly — multiple signals absent |

---

## Employee Profile Types

The scoring engine applies different logic per role type:

| Profile | Key signals | Min hours threshold |
|---------|------------|---------------------|
| `teacher_full` | asistencia + WiFi + Classroom | 4.5h (morning block 07:00–12:45) |
| `teacher_partial` | asistencia (days present only) | 4.5h on expected days, skip others |
| `admin_staff` | email + WiFi + Odoo | 7.0h |
| `special_schedule` | skipped entirely | N/A (ids 571/606/610) |

**Profile assignment:** derived from `profesor_seccion` membership. If an employee's email appears in `control_asistencias.profesor_seccion` → `teacher_*`. All others → `admin_staff`.

---

## The Fractal / Self-Calibrating Layer

Over time, the per-employee pattern emerges from accumulated signal history. No manual rules needed.

**Expected schedule inference (30-day window):**
```
For each teacher:
  - Count which weekdays they have asistencia submissions in last 30 days
  - If they submit ≥ 70% of Mon/Tue/Wed/Thu/Fri → that day is "expected"
  - If they submit < 30% of a given weekday → that day is "not expected"
  - Silence all alerts on "not expected" days (contract days off)
```

**Example — Audrey García (7/14 in May):**
- Mon: 3/5 weeks submitted → expected
- Tue: 1/5 → not expected  
- Wed: 3/5 → expected
- Thu: 0/5 → not expected
- Fri: 0/5 → not expected

After 30 days of data, the system knows she comes Mon/Wed only. No alerts on Tue/Thu/Fri.

**Bootstrap period:** First 2 weeks use a conservative fallback (no inferred schedule — use raw signal scoring only). After 30 days → full pattern inference active.

---

## Implementation Phases

### Phase 1 — asistencia cross-check + day-of-week pattern ✅ COMPLETE (2026-06-02)
**Built in:** `scripts/attendance_daily_alert.py`

**New functions added:**
- `load_teacher_emails()` — identifies teachers via `profesor_seccion` membership (25 teachers)
- `get_asistencia_signals_batch(emails, date)` — one DB round-trip, returns set of emails that submitted
- `get_teacher_day_patterns(emails, reference_date, lookback_days=45)` — per-teacher weekday submission rates
- `compute_confidence_score(is_teacher, has_checkin, worked_hours, asistencia_submitted, wifi_connected)` — returns (score, summary)

**New constants:**
```python
MIN_WORKED_HOURS_TEACHER = 4.5   # teachers finish ~12:45 VET
SCORE_SILENCE   = 60             # suppress entirely
SCORE_RRHH_ONLY = 30             # log internally, no employee email
OFF_DAY_MAX_RATE = 0.25          # ≤25% → contract off day
OFF_DAY_MIN_DATA = 4             # minimum weekday occurrences before suppressing
SIGNAL_WEIGHTS = {
    'asistencia_submitted': 65,  # alone sufficient for silence
    'wifi_connected':       25,
    'odoo_checkin':         20,
    'odoo_hours_adequate':  20,
}
```

**Decision flow in `run_morning` for each teacher with issues:**
1. **Off-day check first:** if weekday submission rate ≤ 25% across ≥4 occurrences → SILENCE (contract off day)
2. **Confidence score:** asistencia + WiFi + kiosk + hours → score
3. **score ≥ 60 → SILENCE** | **score 30–59 → RRHH internal log** | **score < 30 → full alert**
4. **Non-teachers:** unchanged — full alert if any issue

**First live run dry-run result (June 1 data → June 2 blast):**
- Before Phase 1: ~32 employees would have been alerted
- After Phase 1: **14 emails sent, 18 suppressed** (8 off-day pattern, 10 silenced by asistencia)
- Example: Flormar Hernández — Mon 0/7 = 0% → OFF-DAY → silence ✅
- Example: Yudelys Brito — asistencia ✅ → score=65 → SILENCE ✅
- Example: Audrey García — came in but 3.7h + no asistencia → score=20 → FULL ALERT ✅ (legitimate)

### Phase 2 — rolling personal baseline (pending)
**Priority:** Arcides Arzola (Director, 4.8h) and Robert Quijada (4.9h) are the clearest candidates — borderline false positives that Phase 2 would eliminate automatically.


**Effort:** ~2 days | **Impact:** Self-calibrating hours threshold per employee

- Add `AttendanceBaseline` class: computes 30-day rolling `mean_hours` + `stddev_hours` per employee
- Alert threshold becomes `max(3.5, mean_hours - 1.5 * stddev_hours)` instead of global 5.0h
- Stored in state file alongside morning/evening keys
- Handles role changes automatically — baseline adjusts within 30 days

### Phase 3 — Google signals (when OAuth is configured)
**Effort:** OAuth setup (admin, ~30 min) + 1 day code | **Impact:** Strongest signal for remote/hybrid evidence

- `get_classroom_activity_signal(teacher_email, date)` — queries Classroom API for posts, grades, comments in school hours window
- `get_email_activity_signal(employee_email, date)` — queries Google Admin Reports API (`gmail` application, `messagesSent` event, filter 07:00–14:00 VET)
- Requires: service account with domain-wide delegation, scopes:
  - `https://www.googleapis.com/auth/admin.reports.audit.readonly`
  - `https://www.googleapis.com/auth/classroom.courses.readonly`

### Phase 4 — weekly pattern narrative (AI layer)
**Effort:** ~1 day | **Impact:** RRHH gets actionable insight, not just a list of names

- After the morning run, if any employee has had ≥ 3 low-confidence days in the past week → pass their signal history to Claude Haiku
- Generate 2-sentence narrative: what's the pattern, is it consistent with their baseline, what warrants attention
- Append to the `hr_leave_attendance_digest.py` daily digest as a new section: "⚠️ Tendencias de Asistencia"
- Uses existing `ai.agent.claude.service` infrastructure — no new API setup needed

---

## Data Sources — Connection Reference

```python
# control_asistencias (teacher work delivery)
CA_DB = {
    'host': 'localhost', 'port': 3306,
    'user': 'control_asist', 'password': 'y3deTsi92HrQgj0wgvVx',
    'database': 'control_asistencias'
}

# Query: did teacher submit asistencia for date?
SELECT COUNT(*) FROM asistencia_estudiante
WHERE id_usuario = %s AND fecha = %s

# Query: teacher's id_usuario from email
SELECT id_usuario FROM usuario WHERE email = %s

# Query: teacher→section mapping (for section-count-based weight adjustment)
SELECT COUNT(DISTINCT id_seccion) FROM profesor_seccion WHERE id_profesor = %s
```

```python
# WiFi signal — reuse existing Mikrotik SSH pattern
# Extend wifi_hotspot_users table with teacher phone/laptop usernames
# Same SSH query as evening mode — filter to school hours window (07:00–14:00 VET)
```

---

## Known Gaps / Open Questions

1. **WiFi expansion:** Currently only 8 employees mapped in `payroll_db.wifi_hotspot_users`. Add teacher phone/laptop hotspot usernames to increase WiFi signal coverage.

2. **Google OAuth:** `google_sheets_credentials.json` covers Sheets only. Classroom + Admin Reports need service account with domain-wide delegation. One-time setup in Google Workspace Admin console.

3. **Camila Rossato, Gladys Brito, Nidya Lira:** In Odoo Docentes dept with active contracts but NO sections in `control_asistencias` and zero asistencia submissions ever. Phase 1 treats them as admin staff (full alert). Clarify with RRHH: are they teaching or in a support role?  Nidya is not even in `control_asistencias` user table.

4. **Nidya Lira kiosk issues:** Two back-to-back 22h attendance records (May 18–19) — chronic missing-checkout problem. RRHH should correct those records and train her on kiosk checkout.

5. **Employee guide update pending (2026-06-02):** Update `ATTENDANCE_EMPLOYEE_GUIDE.md` and the blast email template to explain the smart alert behavior — employees should know that if they submitted their class, they will not receive an alarm even if they forgot the kiosk.

6. **Score weight calibration:** Review after 2 weeks of live data to confirm silence/alert distribution is correct.

---

## Integration Points

- **`attendance_daily_alert.py`** — primary home for Phase 1 + 2 changes
- **`hr_leave_attendance_digest.py`** — Phase 4 narrative section appended here
- **`payroll_db.wifi_hotspot_users`** — needs teacher username entries for Phase 1 WiFi expansion
- **`control_asistencias.asistencia_estudiante`** — primary result signal (live, current through today)
- **`ai.agent.claude.service`** — reused for Phase 4 narrative generation (no new API setup)

---

## Related Documentation

- [Attendance Daily Alert](ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md)
- [Control Asistencia Bridge](CONTROL_ASISTENCIA_BRIDGE.md)
- [Glenda Technical Patterns](GLENDA_TECHNICAL_PATTERNS.md) — Claude service usage pattern
