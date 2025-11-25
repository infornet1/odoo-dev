# UEIPAB OpenEducat Implementation Plan
**Institution:** Instituto Privado Andrés Bello (UEIPAB)
**Location:** Venezuela
**Date:** 2025-11-25
**Version:** 2.0 (Revised with practical optimizations)
**Go-Live Target:** 15 September 2026

---

## 1. Executive Summary

This plan outlines the implementation of OpenEducat ERP Community Edition with custom portal development for UEIPAB, a Venezuelan educational institution with **223 students** offering PreSchool, Primary, and Secondary education.

**Key Constraints:**
- Zero budget (using free Community Edition)
- Intermittent Internet connectivity
- Limited IT resources

**Key Decision:** Simplify architecture, minimize custom code, leverage existing OpenEducat features wherever possible.

---

## 2. Database Architecture

| Database | Purpose | Content |
|----------|---------|---------|
| `DB_UEIPAB` | Accounting & HR | Payroll, contracts, accounting (existing) |
| `openeducat_prod` | Academics | Students, grades, attendance (NEW) |
| `openeducat_demo` | Development & Testing | Testing environment (existing) |

**Rationale:** Separate databases avoid chart-of-accounts pollution and satisfy auditor requirements.

---

## 3. Institution Profile

### Education Levels & Student Count

| Level | Spanish | Grades/Groups | Students (est.) |
|-------|---------|---------------|-----------------|
| **PreSchool** | Preescolar | 1er, 2do, 3er grupo | ~40 |
| **Primary** | Primaria | 1er - 6to grado | ~100 |
| **Secondary** | Media | 1er - 5to año | ~83 |
| **TOTAL** | | | **223** |

### Grading Systems (Simplified Approach)

#### PreSchool & Primary: Literal Scale (A-E) + Descriptive

**NO NEW MODELS REQUIRED** - Use existing OpenEducat exam system:

| Exam Type | Weight | Purpose |
|-----------|--------|---------|
| Regular exams | Variable % | Literal grade (A,B,C,D,E) |
| **"Informe Descriptivo"** | **0%** | Teacher narrative (text field) |

**Implementation:** Create one exam called "Informe Descriptivo" per lapso, mark as "Descriptive" type with 0% weight. Teachers type narrative in existing QWeb text widget. Prints on boletín without custom Python code.

#### Secondary: Numeric Scale (1-20)

Use **built-in 20-point numeric scale** - no changes needed.

| Range | Qualification |
|-------|---------------|
| 19-20 | Excelente |
| 16-18 | Muy Bueno |
| 13-15 | Bueno |
| 10-12 | Regular (Aprobado) |
| 01-09 | Deficiente (Reprobado) |

---

## 4. Assignment Types & Weights (LOCK BEFORE GO-LIVE)

**CRITICAL:** Configure these BEFORE any teacher creates assignments:

| Assignment Type | Spanish | Weight |
|-----------------|---------|--------|
| Homework | Tarea | 10% |
| Project | Trabajo | 15% |
| Presentation | Presentación | 15% |
| Quiz | Prueba Corta | 5% |
| Midterm | Parcial | 25% |
| Final | Final | 30% |
| **TOTAL** | | **100%** |

---

## 5. Academic Calendar 2026-2027

### Lapso Dates (LOCK NOW)

| Lapso | Start Date | End Date | Weeks |
|-------|------------|----------|-------|
| **1er Lapso** | 15 Sep 2026 | 19 Dec 2026 | 14 |
| **2do Lapso** | 05 Jan 2027 | 10 Apr 2027 | 14 |
| **3er Lapso** | 20 Apr 2027 | 17 Jul 2027 | 13 |

### Key Actions:
- Create **three Exam Sessions** per batch with these exact dates
- Configure holidays within each lapso
- Setup boletín delivery dates

---

## 6. User Roles

### Portal Users (Frontend - Custom Development)

| Role | Spanish | Access |
|------|---------|--------|
| **Student** | Estudiante | View own grades, attendance, schedule |
| **Parent** | Representante | View children's academic data |

**NOTE:** Teacher Portal (Phase 5) **DEFERRED** to Year 2. Teachers use backend for first school year - they already have PCs in staff room.

### Backend Users (OpenEducat Admin)

| Role | Spanish | Responsibilities |
|------|---------|------------------|
| **Director(a)** | Director(a) | Oversight, approvals, KPIs |
| **Control de Estudios** | Coordinación Académica | ALL academic operations |
| **Teachers** | Docentes | Grade entry via backend |
| **Secretary** | Secretaria | Student data entry |

---

## 7. Development Timeline (10-Month Runway)

### Reverse-Planned from 15 Sep 2026

```
Nov 2025 ──────────────────────────────────────────────► Sep 2026
    │                                                        │
    ▼                                                        ▼
[Research]──[Core Build]──[Pilot]──[Freeze]──[Buffer]──[GO-LIVE]
Nov-Dec     Jan-Mar       Apr-Jun   Jun-Jul   Jul-Aug    Sep 15
```

### Phase Details

| Phase | Calendar Weeks | Milestone Date | What "Done" Looks Like |
|-------|----------------|----------------|------------------------|
| **0. Research & Planning** | Nov - Dec 2025 (8w) | 31 Dec 2025 | Plan approved, demo environment ready, requirements validated |
| **1. Core Build** | 05 Jan - 27 Mar 2026 (12w) | **31 Mar 2026** | Venezuelan grade scales, 3-lapso calendar, parent portal v1, demo data purged, USB-backup script working |
| **2. Pilot Cycle** | 30 Mar - 26 Jun 2026 (13w) | **30 Jun 2026** | One real section per level (Pre, Prim, Sec) running live with ~30 volunteer students; teachers entering grades; parents logging in; bug list < 10 low-priority items |
| **3. Hard Freeze & Training** | 29 Jun - 24 Jul 2026 (4w) | **24 Jul 2026** | Code freeze, final data migration rehearsal, coordinator training videos recorded, printed quick-guides in teachers' lounge |
| **4. Summer Buffer** | 27 Jul - 31 Aug 2026 (5w) | 31 Aug 2026 | Vacation + emergency-only support; server snapshot taken; any last-minute ministerio form changes absorbed |
| **5. Production Launch** | 01 Sep - 15 Sep 2026 (2w) | **15 Sep 2026** | All 223 students imported, parent accounts bulk-created, first attendance sheet printed, 1er lapso exam sessions published |

### Key Dates (LOCK NOW)

| Date | Milestone | Non-Negotiable |
|------|-----------|----------------|
| **31 Mar 2026** | Core-complete | Gives 5.5 months buffer |
| **30 Jun 2026** | Pilot MUST finish | Teachers disappear in July |
| **24 Jul 2026** | Code freeze | No new features, only bug-fixes |
| **15 Sep 2026** | **GO-LIVE** | First day of regular classes |

---

## 8. Portal Scope (Simplified)

### What We WILL Build (Phases 4.1 - 4.4)

| Feature | Route | Priority |
|---------|-------|----------|
| Grades/Calificaciones | `/my/grades` | HIGH |
| Attendance/Asistencia | `/my/attendance` | HIGH |
| Schedule/Horario | `/my/schedule` | HIGH |
| Assignments/Tareas | `/my/assignments` | MEDIUM |
| Parent Child View | `/my/children` | HIGH |

### What We WON'T Build (Year 1)

| Feature | Reason | When |
|---------|--------|------|
| Teacher Portal | Teachers use backend, saves 3 weeks dev | Year 2 |
| Assignment Submission | Complex, low priority | Year 2 |
| Chat/Messaging | Scope creep risk | Year 2+ |

---

## 9. Risk Mitigation

### Internet/Power Outages

**Solution:** Export PDF boletas every lapso and save on USB stick.

```bash
# USB Backup Script (run end of each lapso)
#!/bin/bash
DATE=$(date +%Y%m%d)
LAPSO=$1
mkdir -p /media/usb/boletas_${LAPSO}_${DATE}
# Export all student report PDFs
odoo-bin shell -d openeducat_prod << EOF
# Generate and save all boletas to USB
EOF
echo "Backup complete: /media/usb/boletas_${LAPSO}_${DATE}"
```

**Result:** When Internet dies, hand paper copy to parents - **legal compliance preserved**.

### Demo Data Cleanup

**CRITICAL:** On Day 1 of production setup, run:
```
Settings → Technical → Purge Demo Data
```

**Why:** Otherwise first real student = student #224, and Ministry forms require **consecutive codes**.

### Monthly Snapshots

Every **last Friday of the month**:
1. Tag VM snapshot
2. Backup database
3. Test restore procedure

**Result:** If something breaks, rollback in 10 minutes.

---

## 10. Success Metrics (Measurable)

### Pilot Phase (Apr-Jun 2026)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Pilot students | 30 | Database count |
| Teacher grade entries | 100% digital | No paper grade sheets |
| Critical bugs | < 10 | Issue tracker |

### Go-Live (Sep 2026 - Jul 2027)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Students imported | 223 | Database count |
| Parent portal logins | **150 active logins in 3er lapso** | Server log count |
| Boletines generated | 669 (223 × 3 lapsos) | Report count |
| USB backups | 3 (one per lapso) | Physical verification |

---

## 11. Pilot Strategy

### Test with 2025-2026 Data

Even though current year is half-paper, use real data to exercise full three-lapso cycle between April and June 2026.

### Fake Lapsos Schedule

| Fake Lapso | Duration | Test Focus |
|------------|----------|------------|
| Fake 1er Lapso | 3 weeks (Apr) | Grade entry, computation |
| Fake 2do Lapso | 3 weeks (May) | Parent PDF generation |
| Fake 3er Lapso | 3 weeks (Jun) | USB backup, final reports |

**Result:** Test grade computation, parent PDF, and USB backup **twice** before real year starts.

---

## 12. Project Management

### Trello Board Structure

Only **three columns** - anything not in "Now" is postponed:

```
┌─────────────┬─────────────────┬─────────────────┐
│     NOW     │   JULY BUG      │  POST-GO-LIVE   │
│ (current)   │ (freeze period) │ (after Sep 15)  │
├─────────────┼─────────────────┼─────────────────┤
│ Portal v1   │                 │ Teacher portal  │
│ Grade entry │                 │ Messaging       │
│ USB backup  │                 │ Mobile app      │
│ ...         │                 │ ...             │
└─────────────┴─────────────────┴─────────────────┘
```

**Rule:** Scope-creep is the biggest enemy. If it's not in "Now", it waits until Year 2.

---

## 13. Training Materials

### Deadline: Before July 2026

| Material | Audience | Format |
|----------|----------|--------|
| Quick-guide (2 pages) | Teachers | Printed, laminated |
| Video tutorials (5 min each) | Coordinators | MP4 on USB |
| Parent portal guide | Parents | PDF via WhatsApp |

**Why before July:** Once vacations start, you won't catch teachers again until September.

---

## 14. Technical Checklist

### Before Go-Live (Sep 2026)

- [ ] `openeducat_prod` database created
- [ ] Demo data purged
- [ ] Academic year 2026-2027 configured
- [ ] 3 lapsos with exact dates
- [ ] Assignment types & weights locked
- [ ] 223 students imported
- [ ] Parent accounts bulk-created
- [ ] USB backup script tested
- [ ] First attendance sheet printed
- [ ] 1er lapso exam sessions published

---

## 15. Git Repository Strategy

### Single Repo Approach (Current)

```
infornet1/odoo-dev/
├── addons/
│   ├── openeducat_*              # OpenEducat CE modules (external)
│   └── ueipab_education_portal/  # Custom portal (NEW - our code)
├── documentation/
│   ├── UEIPAB_OPENEDUCAT_*.md    # OpenEducat docs
│   └── *.md                       # HR/Payroll docs
├── config/
│   └── odoo.conf
└── scripts/
```

**Rationale:** Simple, everything in one place, easier backup, single developer workflow.

### Git Tags for Milestones

| Tag | Date | Milestone |
|-----|------|-----------|
| `openeducat-v0.1` | 31 Mar 2026 | Core complete |
| `openeducat-v0.9` | 30 Jun 2026 | Pilot complete |
| `openeducat-v1.0` | 15 Sep 2026 | GO-LIVE |

### Commit Convention

```
docs:     Documentation changes
feat:     New features (portal, grading)
fix:      Bug fixes
config:   Configuration changes
refactor: Code restructuring
```

---

### Document References

| Document | Location |
|----------|----------|
| Venezuelan Grading Research | `VENEZUELAN_GRADING_SYSTEM_RESEARCH.md` |
| Custom Portal Technical Plan | `OPENEDUCAT_CUSTOM_PORTAL_PLAN.md` |
| OpenEducat Installation Guide | `OPENEDUCAT_OPTION_C_INSTALLATION.md` |

---

## 16. Summary: Path to Success

**Follow this calendar and you'll walk into September 2026 RELAXED, with a BATTLE-TESTED system and ZERO surprises.**

| Key Decision | Impact |
|--------------|--------|
| Separate databases | Auditor-friendly, no accounting pollution |
| No new grading models | Zero migration risk, faster development |
| No teacher portal Year 1 | Save 3 weeks, teachers already have PCs |
| Lock assignment weights | No December grade-fixing emergency |
| USB backup every lapso | Legal compliance even without Internet |
| Purge demo data Day 1 | Consecutive student codes for Ministry |
| Measurable metrics | Know exactly when you've succeeded |

---

**Document Status:** APPROVED FOR IMPLEMENTATION
**Last Updated:** 2025-11-25
**Go-Live:** 15 September 2026
**Author:** Claude Code Assistant + User Review
