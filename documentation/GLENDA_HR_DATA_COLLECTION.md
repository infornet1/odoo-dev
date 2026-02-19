# Glenda HR Data Collection — AI-Assisted Employee Data Verification

**Status:** Testing (Gustavo + Alejandra + Alberto tests COMPLETED)
**Created:** 2026-02-18
**Module:** `ueipab_ai_agent` (new skill) + `ueipab_hr_employee` (new module for employee extensions)
**Skill Code:** `hr_data_collection`
**Target:** 44 employees (from latest payslip batches)
**Test Employees:** Gustavo Perdomo (#9/Conv#25), Alejandra Lopez (#12/Conv#28), Alberto Perdomo (#13/Conv#29) — ALL COMPLETED
**Language:** Venezuelan Spanish

---

## 1. Overview

Extend Glenda's AI Agent capabilities with a new **HR Data Collection** skill that proactively contacts employees via WhatsApp to verify and collect:

1. **Phone number** — confirm correct mobile, save in `+58 4XX XXXXXXX` format
2. **Cedula de Identidad** — confirm number (format `V15128008`), expiry date (format `MM/YYYY` → stored as last day of month), request photo/scan. Also collects personal data: nationality (auto-derived), gender, date of birth (from photo), place of birth.
3. **RIF (Registro de Informacion Fiscal)** — request number (format `V151280087`, no dashes) + photo/screenshot, validate expiration, upload to employee profile
4. **Private address** — extract/confirm from RIF document
5. **Emergency contact** — name + phone number

The process is conversational, multi-phase, and tolerant of delays (employees may take days to respond or gather documents).

### Dual-Channel Communication

| Channel | Use Case | Cost |
|---------|----------|------|
| **WhatsApp** (MassivaMovil) | Primary for Phase 1 rollout — builds awareness of Glenda's AI capabilities. Interactive, real-time. | API cost per message |
| **Email** (recursoshumanos@ueipab.edu.ve) | Alternative channel — employees regularly read institutional emails. RIF/Cedula photos can be sent as email attachments. Lower cost for follow-ups. | Free (Freescout) |

**Phase 1 rollout strategy:** Contact all 44 employees via WhatsApp first (90% awareness goal). After initial rollout, email becomes the preferred channel for reminders and document collection to reduce API costs.

**Note:** Some employees may mistakenly reply to `soporte@ueipab.edu.ve` instead of `recursoshumanos@ueipab.edu.ve`. HR Manager manually moves those to the correct mailbox — this is existing workflow, not handled by Glenda.

---

## 2. Business Goals

| Goal | Description |
|------|-------------|
| Phone verification | Ensure every employee has a verified, reachable WhatsApp number on file |
| Cedula compliance | Confirm cedula number + expiry date, collect document photo |
| RIF compliance | Collect valid (non-expired) RIF documents for all employees |
| Document expiry tracking | Proactive CRON alerts when RIF or Cedula approaches expiration |
| Address accuracy | Update private address from authoritative RIF data |
| Emergency preparedness | Every employee must have an emergency contact on record |
| Audit trail | Full conversation log + timestamps for each data point collected |

---

## 3. Critical Safety Rules

### PROTECTED FIELDS — NEVER MODIFIED BY GLENDA

| Field | Example | Rule |
|-------|---------|------|
| `name` (Employee Name) | `ARCIDES ARZOLA` | **NEVER TOUCH** — if name discrepancy found (e.g., RIF shows different name), escalate to HR Manager |
| `work_email` (Institutional Email) | `arcides.arzola@ueipab.edu.ve` | **NEVER TOUCH** — if update/revision needed, escalate to HR Manager |

**If Glenda detects a mismatch** between employee record and document (e.g., RIF name vs Odoo name, or employee reports wrong institutional email), the ONLY action is:

1. Inform the employee: "Noto una diferencia en [campo]. Esto requiere revision por parte de Recursos Humanos."
2. Send escalation email to `recursoshumanos@ueipab.edu.ve` with details
3. Continue with remaining phases

---

## 4. Architecture

### 4.1 New Odoo Model: `hr.data.collection.request`

Tracks the multi-phase data collection process per employee.

```
hr.data.collection.request
├── employee_id          (Many2one → hr.employee, required)
├── state                (Selection: draft/in_progress/partial/completed/cancelled)
├── ai_conversation_id   (Many2one → ai.agent.conversation)
├── batch_id             (Many2one → hr.payslip.run, optional — source batch)
│
├── Phase tracking (Boolean + Date pairs):
│   ├── phone_confirmed          / phone_confirmed_date
│   ├── phone_value              (Char — confirmed phone in +58 format)
│   ├── cedula_confirmed         / cedula_confirmed_date
│   ├── cedula_number            (Char — e.g. "V15128008")
│   ├── cedula_expiry_date       (Date — e.g. 2035-06-30 from "06/2035")
│   ├── cedula_photo_received    / cedula_photo_date
│   ├── nationality_country_code (Char — auto-derived: V→VE, E→foreign)
│   ├── gender_value             (Selection: male/female/other)
│   ├── birthday_value           (Date — extracted from cedula photo)
│   ├── place_of_birth_value     (Char — asked during cedula phase)
│   ├── rif_number_confirmed     / rif_confirmed_date
│   ├── rif_number_value         (Char — e.g. "V151280087")
│   ├── rif_expiry_date          (Date — extracted from document)
│   ├── rif_photo_received       / rif_photo_date
│   ├── address_confirmed        / address_confirmed_date
│   ├── address_value            (Text — full address as confirmed)
│   ├── emergency_confirmed      / emergency_confirmed_date
│   ├── emergency_name           (Char)
│   └── emergency_phone          (Char — in +58 format)
│
├── attempt_count        (Integer — total contact attempts)
├── last_attempt_date    (Datetime)
├── channel              (Selection: whatsapp/email — primary contact channel)
├── notes                (Text — operator notes)
├── create_date          (auto)
└── write_date           (auto)
```

**State flow:**
```
draft ──(conversation started)──> in_progress ──(some phases done)──> partial
                                                                         │
                                       (all 5 phases done) ─────────> completed
                                       (manual cancel) ──────────────> cancelled
```

### 4.2 New AI Skill: `hr_data_collection`

| Property | Value |
|----------|-------|
| Code | `hr_data_collection` |
| Source Model | `hr.data.collection.request` |
| Max Turns | 15 (multi-phase, longer than bounce resolution) |
| Timeout Hours | 72 (3 days — employees need time to gather documents) |
| Reminder Interval | 24 hours |
| Max Reminders | 3 |

### 4.3 Conversation Flow

The skill operates in **5 phases**, advancing through each as data is collected. Claude tracks the current phase and adjusts its prompts accordingly. **Phases with existing data use quick confirmation** (not blank-slate collection).

```
PHASE 1: Phone Confirmation
  Context: Check if employee.mobile_phone already has a value
  IF has phone:
    Glenda: "Hola [nombre], soy Glenda del departamento de RRHH de UEIPAB.
             Estamos actualizando los datos de nuestro personal.
             Tengo registrado tu numero como [current_phone], es correcto?"
    Employee: "Si" → quick confirm, move to Phase 2
    Employee: "No, mi numero es 0414-XXXXXXX" → save new number
  IF no phone:
    Glenda: "...Necesito confirmar tu numero de WhatsApp personal.
             Me lo podrias indicar?"
  → Save confirmed phone in +58 format to request + hr.employee.mobile_phone + hr.employee.private_phone

PHASE 2: Cedula de Identidad + Personal Data
  Context: Check identification_id and id_expiry_date
  IF has cedula:
    Glenda: "Tu cedula es [V15128008], confirmas?
             Cual es la fecha de vencimiento? (por ejemplo: 06/2035)"
  IF no cedula:
    Glenda: "Necesito tu numero de cedula de identidad y su fecha de vencimiento."
  THEN:
    Glenda: "Podrias enviarme una foto o captura de tu cedula?
             Puede ser por aqui o por correo a recursoshumanos@ueipab.edu.ve"
  → Save: identification_id (V15128008), id_expiry_date (06/2035 → 2035-06-30)
  → Upload photo to identification_attachment_ids (named "Cedula - V15128008.jpg")
  → Auto-derive: nationality (V-prefix → Venezuela), country_of_birth (V → VE)
  → From cedula photo: extract birthday via Claude Vision
  → Ask: gender confirmation, place of birth (if not already on file)
  → Save: gender, birthday, place_of_birth, nationality_country_code

PHASE 3: RIF (Registro de Informacion Fiscal)
  Glenda: "Ahora necesitamos tu RIF. Por favor, indicame:
           1. Tu numero de RIF completo
           2. Enviame una foto o captura de pantalla del RIF
           (puede ser por aqui o por correo a recursoshumanos@ueipab.edu.ve)"
  Employee: sends RIF number + photo
  → Claude validates RIF format (V/E/J/G/P + digits + check digit)
  → Claude uses VISION to read expiry date from photo
  → If expired: "Tu RIF vencio el [date]. Necesitas renovarlo.
     Mientras tanto, registramos el actual."
  → Save: ueipab_rif, ueipab_rif_expiry_date
  → Upload photo to identification_attachment_ids (named "RIF - V151280087.jpg")

PHASE 4: Address Confirmation
  Context: Extract address from RIF photo via Claude Vision
  Glenda: "Del RIF puedo ver tu direccion como [extracted_address].
           Es correcta esta direccion de residencia? O prefieres indicarme otra?"
  Employee: confirms or provides different address
  → Save to hr.employee: private_street, private_city, private_state_id,
    private_zip (default 6050), private_country_id (Venezuela)
  → Defaults: state=Anzoategui (ID 2171), city="El Tigre", zip="6050"
  → If different city mentioned, Claude adapts

PHASE 5: Emergency Contact
  Glenda: "Casi terminamos. Necesitamos un contacto de emergencia.
           Por favor, indicame:
           1. Nombre completo del contacto
           2. Numero de telefono
           3. Relacion (esposo/a, padre/madre, hermano/a, etc.)"
  Employee: provides info
  → Save to hr.employee: emergency_contact, emergency_phone

FAREWELL:
  Glenda: "Muchas gracias [nombre]! Hemos actualizado todos tus datos.
           Si necesitas modificar algo en el futuro, escribenos a
           recursoshumanos@ueipab.edu.ve. Que tengas un excelente dia!"
```

### 4.4 Smart Confirmation Logic

When starting a conversation, the skill checks **existing employee data** and adapts:

| Existing Data | Behavior |
|---------------|----------|
| Phone exists | Quick confirm: "Tu numero es [phone], correcto?" |
| Cedula exists | Quick confirm: "Tu cedula es [number], confirmas?" |
| Cedula expiry exists | Skip expiry question, still request photo if missing |
| RIF exists | Quick confirm: "Tu RIF es [number], correcto?" Still request photo |
| Address exists | Quick confirm: "Tu direccion es [address], sigue siendo correcta?" |
| Emergency exists | Quick confirm: "Tu contacto de emergencia es [name] al [phone], sigue vigente?" |
| All data complete + photos | Ultra-short: "Solo necesito verificar que tus datos estan actualizados..." |

**Result:** Employees with partial data get shorter conversations. Employees with complete data get a quick 2-3 message verification.

### 4.5 Control Markers (Claude → Odoo)

Extending the existing marker pattern used by other skills:

| Marker | Purpose | Example |
|--------|---------|---------|
| `ACTION:PHASE_COMPLETE:phone:+58 414 2337463` | Phase 1 done | Phone confirmed |
| `ACTION:PHASE_COMPLETE:cedula:V15128008` | Cedula number confirmed | |
| `ACTION:PHASE_COMPLETE:cedula_expiry:2035-06-30` | Cedula expiry confirmed | "06/2035" → last day of month |
| `ACTION:SAVE_DOCUMENT:cedula` | Current attachment is Cedula photo | Upload to identification_attachment_ids |
| `ACTION:PHASE_COMPLETE:rif_number:V151280087` | RIF number confirmed | |
| `ACTION:PHASE_COMPLETE:rif_expiry:2028-05-15` | RIF expiry from photo | Claude Vision extraction |
| `ACTION:SAVE_DOCUMENT:rif` | Current attachment is RIF photo | Upload to identification_attachment_ids |
| `ACTION:PHASE_COMPLETE:gender:male` | Gender confirmed | Values: male/female/other |
| `ACTION:PHASE_COMPLETE:birthday:1990-01-15` | Date of birth confirmed | YYYY-MM-DD format |
| `ACTION:PHASE_COMPLETE:place_of_birth:El Tigre` | Place of birth confirmed | City/town name |
| `ACTION:PHASE_COMPLETE:address:Calle X, El Tigre, Anzoategui` | Address confirmed | |
| `ACTION:PHASE_COMPLETE:emergency:Juan Perez;+58 412 1234567` | Emergency contact | Name;Phone format |
| `ACTION:ESCALATE:description` | Cannot resolve or protected field issue | Email to HR Manager |

### 4.6 Escalation Mechanism

**All escalations go via email** to `recursoshumanos@ueipab.edu.ve`:

1. Glenda composes an email describing the issue (in Spanish)
2. Sends via Odoo `mail.mail` to `recursoshumanos@ueipab.edu.ve`
3. Freescout auto-creates a conversation in the HR mailbox (mailbox_id=4)
4. Freescout conversation ID + folder can be linked back to the collection request
5. HR Manager (Gustavo, user_id=10) picks up for resolution

**Escalation triggers:**
- Name mismatch between document and Odoo record
- Employee reports wrong institutional email
- Employee refuses to provide data
- Employee reports they no longer work at UEIPAB
- Document appears fraudulent or tampered
- Any situation requiring human judgement

### 4.7 Phone Number Format

**Target format:** `+58 414 2337463` (stored in `mobile_phone` field)

**Normalization rules:**
- Input: `04142337463` → `+58 414 2337463`
- Input: `0414-233-7463` → `+58 414 2337463`
- Input: `584142337463` → `+58 414 2337463`
- Input: `+584142337463` → `+58 414 2337463`
- Pattern: `+58 XXX XXXXXXX` (country code + area code + number, with spaces)

### 4.8 Cedula Expiry Date Format

Venezuelan Cedula expiry is expressed as month/year: `06/2035`

**Conversion:** Always store as **last day of the month** → `2035-06-30`
- `06/2035` → `2035-06-30`
- `12/2028` → `2028-12-31`
- `01/2030` → `2030-01-31`

### 4.9 RIF Document Processing

**RIF format:** `[V|E|J|G|P|C]XXXXXXXXX` (type + digits, no dashes — official Venezuelan convention)

**Claude Vision extraction from RIF photo:**
1. RIF number (validate format)
2. Expiration date
3. Full name (cross-reference — if mismatch, **ESCALATE, do NOT update name**)
4. Address (fiscal domicile — "Domicilio Fiscal")

**Storage — both Cedula and RIF use `identification_attachment_ids`:**
- Cedula photo → `identification_attachment_ids` (name: `"Cedula - V15128008"`)
- RIF photo → `identification_attachment_ids` (name: `"RIF - V151280087"`)
- RIF number → `hr.employee.ueipab_rif` field (new, in `ueipab_hr_employee` module)
- RIF expiry → `hr.employee.ueipab_rif_expiry_date` field (new)
- Cedula number → `hr.employee.identification_id` (existing standard field)
- Cedula expiry → `hr.employee.id_expiry_date` (existing, from `hr_employee_updation`)

### 4.10 Accepted Document Formats

Employees can send Cedula/RIF documents in any of these formats:

| Format | Claude Vision | Handling |
|--------|--------------|----------|
| JPG/PNG/WEBP (photo) | Direct analysis | Best — Claude extracts all data directly |
| PDF | Cannot read directly | Convert first page to image, then analyze via Vision |
| Document (DOC/DOCX) | Not supported | Ask employee to send as photo or PDF instead |

**PDF processing pipeline:**
1. Download PDF from WhatsApp URL (or email attachment)
2. Convert first page to image using `pdf2image` or `PyMuPDF`
3. Send converted image to Claude Vision for RIF/Cedula data extraction
4. Store the **original PDF** in `identification_attachment_ids` (not the converted image)
5. Employee experience is identical regardless of format

### 4.11 Document Expiry CRON (Combined: RIF + Cedula)

Single weekly CRON that checks **both** RIF and Cedula expiry dates:

| Setting | Value |
|---------|-------|
| Frequency | Weekly (every Monday) |
| Alert: 60 days before | Create Odoo activity for HR Manager |
| Alert: 30 days before | Second alert + email to HR Manager |
| Alert: Expired | Urgent alert + optionally auto-trigger renewal request via Glenda |
| Scope | Both `ueipab_rif_expiry_date` AND `id_expiry_date` |

**Auto-renewal flow (optional):** When a document expires, CRON can create a new `hr.data.collection.request` targeting ONLY the expired document phase (not full 5-phase flow). Glenda contacts the employee: "Tu [RIF/Cedula] vencio. Necesitamos el documento actualizado."

---

## 5. Module Structure

### 5.1 New Module: `ueipab_hr_employee` (Employee Extensions)

Follows the same pattern as `ueipab_hr_contract` (which extends contracts). This module owns all UEIPAB-specific employee fields, independent of the AI agent.

**Rationale:** Avoid dependency on `tdv_hr_payroll` (which has a minimal `rif` field with no UI). The `ueipab_hr_employee` module provides a clean, UEIPAB-owned place for Venezuelan employee fields that can be used by multiple features (AI agent, reports, self-service portal, etc.).

```
addons/ueipab_hr_employee/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── hr_employee.py           # RIF fields, phone format helper
├── views/
│   └── hr_employee_views.xml    # RIF group in Identification section
├── data/
│   └── cron.xml                 # Combined RIF + Cedula expiry check CRON
└── security/
    └── ir.model.access.csv
```

**Fields added to `hr.employee`:**

| Field | Type | Purpose |
|-------|------|---------|
| `ueipab_rif` | Char | RIF number (`VXXXXXXXXX` (no dashes)) |
| `ueipab_rif_expiry_date` | Date | RIF expiration date |

**View extension:** Adds a third group `[RIF]` alongside existing `[Identification ID]` and `[Passport ID]` in the employee form's personal information page:

```xml
<!-- Existing (hr_employee_updation) -->     <!-- New (ueipab_hr_employee) -->
[Identification ID]  [Passport ID]           [RIF]
  identification_id    passport_id              ueipab_rif
  id_expiry_date       passport_expiry_date     ueipab_rif_expiry_date
  attachments*         attachments

* identification_attachment_ids holds BOTH Cedula + RIF photos
```

### 5.2 AI Agent Skill (within `ueipab_ai_agent`)

```
addons/ueipab_ai_agent/
├── skills/
│   ├── __init__.py              # Add import for hr_data_collection
│   └── hr_data_collection.py    # NEW — skill class
├── models/
│   ├── hr_data_collection_request.py  # NEW — tracking model
│   └── hr_employee.py           # NEW — One2many + computed state on employee
├── wizard/
│   └── start_hr_collection_wizard.py  # NEW — batch launch wizard
├── views/
│   ├── hr_data_collection_request_views.xml  # NEW
│   └── hr_employee_views.xml    # NEW — show collection status on employee form
├── data/
│   ├── skill_data.xml           # UPDATE — add hr_data_collection skill record
│   └── cron.xml                 # UPDATE — add staggered start CRON
└── security/
    └── ir.model.access.csv      # UPDATE — add access rules
```

### 5.3 Key Files to Create/Modify

**New module `ueipab_hr_employee`:**

| File | Action | Description |
|------|--------|-------------|
| `models/hr_employee.py` | CREATE | `ueipab_rif`, `ueipab_rif_expiry_date` fields |
| `views/hr_employee_views.xml` | CREATE | RIF group in Identification section |
| `data/cron.xml` | CREATE | Weekly combined RIF + Cedula expiry check |
| `security/ir.model.access.csv` | CREATE | Access rules |

**Within `ueipab_ai_agent`:**

| File | Action | Description |
|------|--------|-------------|
| `skills/hr_data_collection.py` | CREATE | Skill class with multi-phase logic |
| `models/hr_data_collection_request.py` | CREATE | Tracking model |
| `models/hr_employee.py` | CREATE | One2many to collection requests |
| `wizard/start_hr_collection_wizard.py` | CREATE | Batch launch from payslip batch |
| `views/hr_data_collection_request_views.xml` | CREATE | List/form views |
| `data/skill_data.xml` | MODIFY | Add skill record |
| `models/__init__.py` | MODIFY | Import new models |
| `__manifest__.py` | MODIFY | Add new files + dependency on `ueipab_hr_employee` |

---

## 6. Target Employee Extraction

### Source: Latest payslip batches (44 employees)

```python
# Extraction logic:
recent_batches = env['hr.payslip.run'].search([
    ('state', 'in', ['close', 'draft']),
], order='date_end desc', limit=5)

target_employees = recent_batches.mapped('slip_ids.employee_id')
# Deduplicate
target_employees = target_employees.sorted('name')
# Expected: ~44 unique employees
```

### Batch Launch Wizard

A wizard accessible from:
1. **Payslip Batch form** → "Iniciar Recoleccion de Datos" button
2. **HR Data Collection** menu → "Crear Solicitudes en Lote"

The wizard:
1. Selects a payslip batch (or multiple)
2. Extracts unique employees
3. Excludes employees with already-completed requests
4. Creates `hr.data.collection.request` records in `draft` state
5. Does NOT auto-start conversations — starts are handled by stagger CRON or manually

---

## 7. Rollout Strategy

### Progressive Groups over 30 Business Days

44 employees over 6 weeks (~5 per week), excluding weekends and holidays.

| Week | Employees | Group Size | Cumulative | Notes |
|------|-----------|------------|------------|-------|
| Week 1 | 1 (Gustavo) | 1 | 1 | Test employee — full validation |
| Week 2 | 2-6 | 5 | 6 | Small batch — monitor + adjust prompts |
| Week 3 | 7-14 | 8 | 14 | Ramp up — lessons from Weeks 1-2 applied |
| Week 4 | 15-24 | 10 | 24 | Steady state |
| Week 5 | 25-34 | 10 | 34 | Steady state |
| Week 6 | 35-44 | 10 | 44 | Final batch + follow-up on stragglers |

**Daily cadence within each week:**
- Monday/Wednesday/Friday: Start 2-3 new conversations each day
- Tuesday/Thursday: Focus on monitoring active conversations, processing photos
- This avoids overwhelming HR with simultaneous active conversations

**Stagger CRON:**
- Runs every 30 minutes during contact schedule hours
- Picks up to 2 `draft` requests per run and starts them
- Respects WA anti-spam throttle (120s between sends)
- Only starts new conversations if active count < configurable limit (default: 10)

### Capacity Management

| Metric | Limit | Rationale |
|--------|-------|-----------|
| Max concurrent active conversations | 10 | HR monitoring capacity (1 person) |
| Max new starts per day | 3 | Manageable flow of incoming documents |
| WA messages per hour | ~30 | 120s anti-spam throttle |
| Expected conversation duration | 2-5 days | Employees need time to gather documents |
| Expected completion rate/week | 70-80% | Some will timeout, need manual follow-up |

---

## 8. Freescout Integration

### HR Mailbox Reference

| Property | Value |
|----------|-------|
| Mailbox | `recursoshumanos@ueipab.edu.ve` |
| Mailbox ID | 4 |
| Inbox folder ID | 107 (type=1, Unassigned) |
| Assigned folder ID | 109 (type=40) |
| Closed folder ID | 110 (type=60) |
| HR Manager | Gustavo Perdomo (user_id=10) |

### Email Channel for Document Collection

Employees can send Cedula/RIF photos via email to `recursoshumanos@ueipab.edu.ve` as an alternative to WhatsApp. An **email attachment checker** script (similar to existing `ai_agent_email_checker.py` for bounce resolution) monitors the HR mailbox for:

1. Replies from employees with active `hr.data.collection.request`
2. Attachments (photos) in those replies
3. Processes attachments → uploads to `identification_attachment_ids`
4. Updates the collection request phase status
5. Optionally replies via Freescout with confirmation

### Escalation Email Flow

```
Glenda detects issue (name mismatch, employee refusal, etc.)
    │
    ├─ ACTION:ESCALATE:description (in Claude response)
    │
    ├─ Odoo sends mail.mail to recursoshumanos@ueipab.edu.ve
    │   Subject: "[GLENDA-HR] Requiere atencion: [Employee Name] - [Issue]"
    │   Body: Description of issue, link to collection request, conversation context
    │
    ├─ Freescout auto-creates conversation in HR mailbox (mailbox_id=4)
    │
    └─ HR Manager picks up conversation for resolution
```

---

## 9. Testing Plan

### Phase 0: Unit Test (No WhatsApp)

- [ ] Create `ueipab_hr_employee` module with RIF fields
- [ ] Create `hr.data.collection.request` model and verify CRUD
- [ ] Test phone normalization function (+58 format)
- [ ] Test RIF format validation
- [ ] Test cedula expiry format conversion (06/2035 → 2035-06-30)
- [ ] Test skill class `get_context()`, `get_system_prompt()`
- [ ] Test `process_ai_response()` marker parsing
- [ ] Verify protected field guardrails (name, work_email)

### Phase 1: Dry Run with Gustavo Perdomo

| Step | Test | Expected |
|------|------|----------|
| 1 | Create collection request for Gustavo | Request in `draft` state |
| 2 | Start conversation (dry_run=True) | Verify greeting message text, smart confirmation |
| 3 | Start conversation (LIVE) | Gustavo receives WhatsApp |
| 4 | Gustavo confirms phone | Phone saved in +58 format |
| 5 | Gustavo confirms cedula + sends photo | identification_id updated, id_expiry_date set, photo in attachments |
| 6 | Gustavo sends RIF number + photo | Claude Vision extracts expiry + address, ueipab_rif saved |
| 7 | Gustavo confirms address | Private address fields updated |
| 8 | Gustavo provides emergency contact | emergency_contact + emergency_phone saved |
| 9 | Conversation completes | Request state = `completed`, all 5 phases marked |
| 10 | Test escalation | Trigger name mismatch → email to recursoshumanos@ |
| 11 | Test email channel | Send RIF photo via email → processed correctly |

### Phase 2: Small Batch (5 employees, Week 2)

- [ ] Select 5 employees from recent batch
- [ ] Monitor conversation flows
- [ ] Verify document uploads to identification_attachment_ids
- [ ] Check retry/reminder behavior
- [ ] Verify email alternative works

### Phase 3: Full Rollout (44 employees, Weeks 3-6)

- [ ] Progressive group starts per schedule
- [ ] Monitor progress dashboard
- [ ] Handle edge cases (wrong numbers, no response, expired documents)
- [ ] Post-rollout: verify all employee records updated

---

## 10. Conversation Edge Cases

| Scenario | Handling |
|----------|----------|
| Employee says phone is wrong | Ask for correct number, retry on new number |
| Employee doesn't have RIF/Cedula handy | "No hay problema, te envio un recordatorio manana" → reminder |
| Photo is blurry/unreadable | "La imagen no es legible, podrias enviar otra foto mas clara?" |
| RIF/Cedula is expired | Accept it, note expiry, remind to renew. "Necesitas renovarlo." |
| Employee sends document via email | Email checker processes attachment, updates request |
| Employee refuses to provide data | Escalate to HR Manager via email |
| Phone number unreachable | After 3 reminders → timeout, flag for manual follow-up |
| Employee provides partial data over multiple days | Resume from last completed phase |
| Name on RIF differs from Odoo record | **DO NOT UPDATE NAME** — escalate to HR Manager |
| Employee reports wrong institutional email | **DO NOT UPDATE EMAIL** — escalate to HR Manager |
| Employee says they no longer work at UEIPAB | Escalate to HR Manager immediately |
| Employee writes to soporte@ instead of recursoshumanos@ | Existing HR workflow — HR moves email manually |
| Multiple employees share a phone (family) | Track per-request, not per-phone |

---

## 11. Data Fields Summary

### Fields to Populate on `hr.employee`

| Field | Source | Format | Example | Protected? |
|-------|--------|--------|---------|------------|
| `name` | — | — | `ARCIDES ARZOLA` | **YES — NEVER TOUCH** |
| `work_email` | — | — | `arcides.arzola@ueipab.edu.ve` | **YES — NEVER TOUCH** |
| `mobile_phone` | Phase 1 | `+58 XXX XXXXXXX` | `+58 414 2337463` | No |
| `private_phone` | Phase 1 | `+58 XXX XXXXXXX` | `+58 414 2337463` | No (mirrors mobile_phone) |
| `identification_id` | Phase 2 | `VXXXXXXXX` | `V15128008` | No |
| `id_expiry_date` | Phase 2 | Date (last day of month) | `2035-06-30` | No |
| `identification_attachment_ids` | Phase 2+3 | Many2many ir.attachment | Cedula + RIF photos | No |
| `country_id` | Phase 2 | Many2one | Venezuela (auto-derived from V-prefix cedula) | No |
| `gender` | Phase 2 | Selection | `male` / `female` / `other` | No |
| `birthday` | Phase 2 | Date | `1990-01-15` (from cedula photo) | No |
| `place_of_birth` | Phase 2 | Char | `El Tigre` | No |
| `country_of_birth` | Phase 2 | Many2one | Venezuela (auto-derived from V-prefix cedula) | No |
| `ueipab_rif` | Phase 3 | `VXXXXXXXXX` (no dashes) | `V151280087` | No |
| `ueipab_rif_expiry_date` | Phase 3 | Date | `2028-05-15` | No |
| `private_street` | Phase 4 | Free text | `Calle Bolivar, Sector Centro` | No |
| `private_city` | Phase 4 | City name | `El Tigre` (parsed from address) | No |
| `private_state_id` | Phase 4 | Many2one | Anzoategui (code V02, ID 2171) | No |
| `private_zip` | Phase 4 | Postal code | `6050` (parsed or default) | No |
| `private_country_id` | Phase 4 | Many2one | Venezuela (always set) | No |
| `emergency_contact` | Phase 5 | Full name | `Maria Gonzalez` | No |
| `emergency_phone` | Phase 5 | `+58 XXX XXXXXXX` | `+58 412 1234567` | No |

### New Fields (via `ueipab_hr_employee` module)

| Model | Field | Type | Purpose |
|-------|-------|------|---------|
| `hr.employee` | `ueipab_rif` | Char | RIF number |
| `hr.employee` | `ueipab_rif_expiry_date` | Date | RIF expiration date |

### New Fields (via `ueipab_ai_agent` module)

| Model | Field | Type | Purpose |
|-------|-------|------|---------|
| `hr.employee` | `data_collection_request_ids` | One2many | Link to collection requests |
| `hr.employee` | `data_collection_state` | Computed | Latest request state for quick view |

### Existing Fields Leveraged (no changes needed)

| Field | Module | Notes |
|-------|--------|-------|
| `identification_id` | Core Odoo | Cedula number (V15128008) |
| `id_expiry_date` | `hr_employee_updation` | Cedula expiry date |
| `identification_attachment_ids` | `hr_employee_updation` | Shared for Cedula + RIF photos |
| `emergency_contact` | Core Odoo | Emergency contact name |
| `emergency_phone` | Core Odoo | Emergency contact phone |
| `private_street`, `private_city`, etc. | Core Odoo | Private address fields |
| `private_phone` | Core Odoo | Private phone (mirrors mobile_phone) |
| `mobile_phone` | Core Odoo | Work mobile (used for WA number) |
| `country_id` | Core Odoo | Nationality (auto-derived from cedula prefix) |
| `gender` | Core Odoo | Gender (male/female/other) |
| `birthday` | Core Odoo | Date of birth (from cedula photo) |
| `place_of_birth` | Core Odoo | Place of birth (asked during Phase 2) |
| `country_of_birth` | Core Odoo | Country of birth (auto-derived from cedula prefix) |

---

## 12. CRON Jobs

### New CRONs

| CRON | Model | Method | Interval | Purpose |
|------|-------|--------|----------|---------|
| Document Expiry Check | `ueipab_hr_employee` | `_cron_check_document_expiry()` | Weekly (Monday) | Alert HR for expiring RIF + Cedula |
| Collection Stagger | `hr.data.collection.request` | `_cron_start_pending()` | Every 30 min | Auto-start draft requests (staggered) |
| HR Email Checker | External script | — | Every 15 min | Monitor recursoshumanos@ for document replies |

### Document Expiry Check Logic

```python
def _cron_check_document_expiry(self):
    today = fields.Date.today()
    employees = self.env['hr.employee'].search([
        ('employee_type', '=', 'employee'),
    ])

    for emp in employees:
        for doc_type, date_field, label in [
            ('RIF', 'ueipab_rif_expiry_date', 'RIF'),
            ('Cedula', 'id_expiry_date', 'Cedula de Identidad'),
        ]:
            expiry = getattr(emp, date_field)
            if not expiry:
                continue
            days_left = (expiry - today).days

            if days_left <= 0:
                # EXPIRED — urgent alert + optional auto-trigger renewal
                self._create_expiry_alert(emp, label, 'expired', expiry)
            elif days_left <= 30:
                # 30-day warning — email HR Manager
                self._create_expiry_alert(emp, label, 'warning_30', expiry)
            elif days_left <= 60:
                # 60-day warning — Odoo activity
                self._create_expiry_alert(emp, label, 'warning_60', expiry)
```

---

## 13. Integration Points

| System | Integration | Direction | Notes |
|--------|-------------|-----------|-------|
| WhatsApp (MassivaMovil) | Send/receive messages + images | Bidirectional | Primary channel for Phase 1 rollout |
| Email (recursoshumanos@) | Send escalations, receive documents | Bidirectional | Lower-cost alternative, Freescout mailbox_id=4 |
| Claude AI (Anthropic) | NLU + Vision (RIF/Cedula photo analysis) | Outbound | Haiku 4.5 for cost efficiency |
| Odoo `hr.employee` | Write verified data (except name/work_email) | Outbound | Protected field guardrails |
| Odoo `ir.attachment` | Store document photos | Outbound | Via identification_attachment_ids |
| Freescout (HR mailbox) | Read employee replies, link escalations | Read | mailbox_id=4, MySQL direct access |
| Payslip Batch | Extract target employees | Read | 44 employees from recent batches |

---

## 14. Security Considerations

- RIF/Cedula contain sensitive personal information → restrict to `hr.group_hr_user`
- WhatsApp conversations may contain personal data → same access as HR private fields
- Document attachments → linked to employee with HR-only access
- CRON alerts → only to HR Manager (`hr.group_hr_manager`)
- Model access: `hr.group_hr_user` minimum, `hr.group_hr_manager` for batch operations
- **Protected fields:** `name` and `work_email` are READONLY for this entire system

---

## 15. Development Phases

### Phase A: Foundation -- COMPLETED (2026-02-18)
- [x] Create `ueipab_hr_employee` module v17.0.1.0.0 (RIF fields, expiry CRON, employee form RIF group)
- [x] Create `hr.data.collection.request` model (within `ueipab_ai_agent` v17.0.1.16.0)
- [x] Create views (tree with progress bar, form with 5-phase notebook tabs, search with filters)
- [x] Add "Recoleccion de Datos" menu under AI Agent > Operaciones
- [x] Add `data_collection_state` computed field on hr.employee
- [x] Security rules: user (read) + manager (full CRUD)
- [x] Skill data record: `hr_data_collection` (max_turns=15, timeout=72h)
- [x] Installed and verified in testing (CRUD test with Gustavo Perdomo OK)

### Phase B: Skill Implementation -- COMPLETED (2026-02-18)
- [x] Create `hr_data_collection.py` skill class (390+ lines)
- [x] Implement 5-phase conversation logic with smart confirmation
- [x] Implement all ACTION markers: PHASE_COMPLETE (phone/cedula/cedula_expiry/rif_number/rif_expiry/address/emergency), SAVE_DOCUMENT (cedula/rif), ESCALATE, RESOLVED
- [x] Implement `on_resolve()` — write data to employee with protected field checks (name/work_email NEVER touched)
- [x] Phone normalization: `normalize_ve_phone()` — all VE formats → `+58 XXX XXXXXXX`
- [x] RIF validation: `validate_rif_format()` — normalizes to `VXXXXXXXXX` (no dashes, official VE convention)
- [x] Cedula expiry: `parse_cedula_expiry()` — `06/2035` → `2035-06-30` (last day of month)
- [x] Address parsing: `parse_ve_address()` — extracts city, state (Odoo code V01-V24), zip from free text
- [x] Personal data: nationality auto-derived from cedula prefix (V→VE), gender/birthday/place_of_birth markers
- [x] Skill registered via `@register_skill('hr_data_collection')` decorator
- [x] Verified in testing: get_context, get_greeting (smart confirmation), get_system_prompt, process_ai_response (marker parsing), on_resolve (employee write-back with structured address)

### Phase C: Document Handling -- COMPLETED (2026-02-18)
- [x] PDF-to-image conversion via PyMuPDF (fitz) — first page rendered at 2x resolution for Claude Vision
- [x] `_convert_pdf_to_image()` on conversation model — tries archived binary first, falls back to URL download
- [x] `_get_conversation_history()` enhanced: PDFs sent as image blocks so Claude can analyze via Vision
- [x] Archive cron updated: now archives both `image` AND `document` types (was image-only)
- [x] `_save_document_to_employee()` on skill — downloads latest attachment, creates ir.attachment with naming ("Cedula - V15128008.jpg", "RIF - V151280087.pdf"), links to employee `identification_attachment_ids`
- [x] SAVE_DOCUMENT markers now trigger actual document saving (not just boolean flags)
- [x] Original file format preserved: PDFs stored as PDFs, images as images (conversion only for Vision)
- [x] Claude Vision already handles RIF/Cedula data extraction via system prompt (Phase B)
- [x] Name mismatch detection: system prompt instructs Claude to ESCALATE if RIF name differs from employee record
- [x] `external_dependencies` added to manifest: `fitz` (PyMuPDF)
- [x] Module version bumped to 17.0.1.17.0
- [x] Verified in testing: PDF→PNG conversion (53KB), conversation history with image blocks, attachment creation + naming + linking

### Phase D: Email Integration -- COMPLETED (2026-02-18)
- [x] `_send_escalation_email()` on conversation model — sends HTML email with employee name, reason, Odoo links
- [x] HR skill `process_ai_response` returns `send_escalation_email` action on ESCALATE markers
- [x] Email to `recursoshumanos@ueipab.edu.ve` with subject `[GLENDA-HR] Requiere atencion: {name} — {reason}`
- [x] Freescout auto-creates conversation in HR mailbox (mailbox_id=4) from received email
- [x] `action_process_reply` engine handles `send_escalation_email` action key
- [x] HR email checker script: `scripts/ai_agent_hr_email_checker.py` (DRY_RUN default, --live)
- [x] Monitors HR mailbox for employee replies with attachments (images + PDFs)
- [x] Matches sender work_email to active `hr.data.collection.request` records
- [x] Reads attachments from Freescout disk (`/var/www/freescout/storage/app/attachment/`)
- [x] Uploads to Odoo via XML-RPC: creates ir.attachment, links to `identification_attachment_ids`
- [x] Updates request phase status (cedula_photo_received / rif_photo_received)
- [x] Posts Freescout internal note `[GLENDA-HR] Documento recibido y procesado`
- [x] `guess_doc_type()` heuristic: filename keywords → cedula/rif/unknown
- [x] State file: `scripts/ai_agent_hr_email_checker_state.json`
- [x] Verified: Odoo escalation email (dry run), Freescout attachment read (50KB test), script dry run OK

### Phase E: Batch Operations + Stagger CRON -- COMPLETED (2026-02-18)
- [x] Batch launch wizard: `hr.data.collection.create.wizard` + `hr.data.collection.create.line` (TransientModels)
- [x] Wizard shows employee status indicators (phone, cedula, address, existing request)
- [x] Two access points: "Recoleccion de Datos" button on payslip batch form + standalone menu
- [x] Wizard 2-state form: select (with toggle/deselect-all) → done (summary + "Ver Solicitudes")
- [x] Stagger CRON: `_cron_start_pending()` on `hr.data.collection.request` (every 30 min)
- [x] Respects `ai_agent.stagger_batch_size` (default 2) and `ai_agent.stagger_max_active` (default 10)
- [x] Counts ALL active conversations (all skills) for capacity check
- [x] Individual commit/rollback per request start (one failure doesn't block others)
- [x] `hr_payroll_community` added as dependency (payslip batch view inheritance)
- [x] Security: wizard + line models accessible to all users
- [x] Module version bumped to 17.0.1.18.0

### Phase F: Document Expiry Tracking (Estimated: 1 day)
- [ ] Weekly CRON for combined RIF + Cedula expiry check
- [ ] Activity/email notification creation
- [ ] Optional: auto-trigger renewal request for expired documents

### Phase G: Testing with Gustavo -- COMPLETED (2026-02-18)
- [x] Live test with Gustavo Perdomo (Request #9, Conversation #25)
- [x] Full 5-phase conversation completed: phone → cedula → RIF → address → emergency
- [x] All data written to hr.employee correctly (including attachments)
- [x] Cedula photo: Claude Vision extracted name, detected name discrepancy → escalation email sent
- [x] RIF photo: Claude Vision extracted RIF number, expiry date, and address
- [x] Address parsing: `parse_ve_address()` extracts city (El Tigre), state (V02 Anzoátegui), zip (6050) from free text
- [x] Country always set to Venezuela on address confirmation
- [x] Personal data fields: nationality (auto-derived from V-prefix), gender, birthday, place_of_birth
- [x] Private phone mirrors mobile_phone
- [x] Escalation email deduplication (one per conversation)

**Bugs found and fixed during Gustavo test:**
1. `_extract_visible_text()` truncated messages after ACTION markers — fixed to strip marker lines only
2. RIF format stored with dashes (`V-15128008-7`) — fixed to dashless convention (`V151280087`)
3. VE state code mapping wrong (V01=Anzoátegui) — corrected (V01=Amazonas, V02=Anzoátegui)
4. Country field missing from address write — made unconditional
5. Claude not emitting markers for confirmed data — reinforced system prompt rules 5-6
6. Duplicate escalation emails (4x for same issue) — added `escalation_date` dedup guard
7. `private_phone` not populated — added to on_resolve() Phase 1 writes

### Phase G.2: Testing with Alejandra + Alberto -- COMPLETED (2026-02-18/19)
- [x] Live test with Alejandra Lopez (Request #12, Conversation #28, Employee #570)
- [x] Live test with Alberto Perdomo (Request #13, Conversation #29, Employee #765)
- [x] Both conversations hit max_turns=15 limit and failed — fixed to max_turns=30
- [x] Alberto: all 5 phases completed, 18 fields written to employee, 2 attachments (Cedula PDF + RIF PDF)
- [x] Alejandra: all 5 phases completed (manually recovered), 17 fields written, 2 attachments (Cedula + RIF photos)
- [x] Alejandra: escalation email sent for name discrepancy (ALEJANDRA CRISTINA LOPEZ SAYAGO vs ALEJANDRA LOPEZ)
- [x] Freescout ticket properly created via email (FS #39571 in HR mailbox #4)

**Bugs found and fixed during Alejandra/Alberto tests:**

| # | Bug | Root Cause | Fix | Commit |
|---|-----|-----------|-----|--------|
| 1 | Conversations fail at 15 turns | `turn_count` counts ALL inbound messages (old ones batched). 15 turns insufficient for full 5-phase collection. | Increased `max_turns` from 15 to 30 in DB + `skills_data.xml` | `0b4eb76` |
| 2 | ESCALATE short-circuits phase markers | `process_ai_response()` returned early on ESCALATE before processing PHASE_COMPLETE/SAVE_DOCUMENT markers. All data confirmations silently dropped when escalation present. | Moved PHASE_COMPLETE + SAVE_DOCUMENT processing BEFORE ESCALATE/RESOLVED checks | `0b4eb76` |
| 3 | First escalation email never sent | `_handle_escalation()` sets `escalation_date` before the `if not self.escalation_date` email send check, making it always False | Capture `is_first_escalation` flag BEFORE calling `_handle_escalation()` | `f69702a` |
| 4 | Wrong Freescout conversation linked | Bridge stored `conv_number` (display number) but FS URLs use auto-increment `id` | Changed to store `conversation_db_id` (note: superseded by bridge refactor) | `634c2b3` |
| 5 | Direct SQL INSERT created orphan FS conversations | Escalation bridge created Freescout conversations via raw SQL INSERT, bypassing Laravel pipeline (wrong state, source_via, folder_id, etc.) | **Removed ALL Freescout MySQL operations from bridge.** Escalation now via email only (Odoo → mail.mail → FS auto-creates). Bridge only sends WA group notification. | `65a1598` |
| 6 | Freescout base URL wrong | `soporte.ueipab.edu.ve` used everywhere — domain doesn't exist | Changed to `freescout.ueipab.edu.ve` in all 4 files | `43c1ac2` |
| 7 | FS ticket ID formatted with comma | `escalation_freescout_id` was `Integer` field — Odoo adds thousands separator (39,571) | Changed to `Char` field. Added computed `escalation_freescout_url` with `widget="url"` for clickable link | `43c1ac2` |
| 8 | Duplicate attachments on employee | `_save_document_to_employee()` creates new attachment every time, even for same doc_type. Multiple SAVE_DOCUMENT emissions stack duplicates. | Added deduplication: search existing attachments by prefix ("Cedula -" / "RIF -"), remove before creating new | `43c1ac2` |

**Cleanup performed:**
- Deleted 2 orphan FS conversations (#39427 FREDDY GONZALEZ, #39569 ALEJANDRA LOPEZ) created by wrong SQL INSERT
- Cleaned up 4 duplicate attachments on Alberto's employee #765 (kept 1 Cedula PDF + 1 RIF PDF)
- Cleared stale `escalation_freescout_id` references on Conv #13 and #28
- Sent proper escalation email for Alejandra → FS #39571 created correctly via email

### Phase H: Progressive Rollout (Weeks 2-6)
- [ ] Week 2: 5 employees — small batch validation
- [ ] Week 3: 8 employees — ramp up
- [ ] Weeks 4-5: 10 employees each — steady state
- [ ] Week 6: 10 employees + stragglers — final batch
- [ ] Post-rollout monitoring and cleanup

---

## 16. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | Email alternative for RIF | **YES** — dual-channel (WhatsApp + email to recursoshumanos@). Email preferred for follow-ups to reduce costs. |
| 2 | RIF renewal workflow | **YES** — CRON can auto-trigger targeted renewal request (single-phase, not full 5-phase). |
| 3 | Partial completion | After 72h timeout + 3 reminders → mark `partial`. HR Manager notified via email. |
| 4 | Address granularity | **Hybrid** — Claude extracts full text from RIF, save to `private_street`. Auto-populate city/state/zip from defaults (El Tigre/Anzoategui/6050/VE). Claude adapts if different city. |
| 5 | Existing data | **Smart confirmation** — check existing data, quick confirm ("Tu cedula es V15128008, confirmas?"). Don't re-enter from scratch. Phases with complete data become quick 1-message confirmations. |
| 6 | Document type | Reuse `identification_attachment_ids` for both Cedula and RIF photos, with clear naming. |
| 7 | Escalation mechanism | **Email only** — send to recursoshumanos@ueipab.edu.ve. Auto-creates Freescout conversation for HR resolution. No WA group notification. |
| 8 | Protected fields | `name` and `work_email` are NEVER modified. Mismatches trigger escalation. |

---

## 17. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `ueipab_ai_agent` v1.15.0 | Installed (testing) | Base skill framework + multimodal support |
| `ueipab_hr_employee` | **NEW** | Employee extensions (RIF fields) |
| `oh_employee_documents_expiry` | Installed | Document expiry tracking patterns |
| `hr_employee_updation` | Installed | `id_expiry_date`, `identification_attachment_ids` fields |
| Claude Vision (multimodal) | Available (v1.13.0) | RIF/Cedula photo analysis |
| MassivaMovil WA API | Active | Image reception |
| Freescout HR mailbox | Active (mailbox_id=4) | Email channel + escalation |

**Explicitly NOT depending on:** `tdv_hr_payroll` — its `rif` Char field is replaced by `ueipab_rif` in the new `ueipab_hr_employee` module.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-18 | 0.1.0 | Initial planning document |
| 2026-02-18 | 0.2.0 | Major refinements: dual-channel (WA + email), Cedula tracking (Phase 2), protected fields (name/work_email NEVER TOUCH), `identification_attachment_ids` reuse for Cedula + RIF, escalation via email to HR Manager, progressive 30-day rollout, smart confirmation for existing data, Freescout HR mailbox integration (mailbox_id=4), combined RIF + Cedula expiry CRON |
| 2026-02-18 | 0.3.0 | Phase A completed: `ueipab_hr_employee` v1.0.0 installed, `ueipab_ai_agent` v1.16.0 upgraded, `hr.data.collection.request` model + views + menu + security + skill record. PDF document support added to accepted formats (Section 4.10). |
| 2026-02-18 | 0.4.0 | Phase B completed: skill class with 5-phase logic, utility functions, all ACTION markers. Phase C completed: PDF-to-image via PyMuPDF for Claude Vision, SAVE_DOCUMENT saves to employee `identification_attachment_ids`, archive cron handles PDFs. Module v1.17.0. |
| 2026-02-18 | 0.5.0 | Phase D completed: Escalation email to recursoshumanos@ with Odoo links, HR email checker script for Freescout HR mailbox attachment processing, Freescout disk attachment reading, doc type heuristic. Phases A-D complete — ready for testing (Phase G). |
| 2026-02-18 | 0.6.0 | Phase G completed: Live test with Gustavo Perdomo (5-phase conversation). Fixed 7 bugs: `_extract_visible_text()` truncation, RIF dashless format, VE state code mapping, unconditional country write, marker emission enforcement, escalation email dedup, private_phone write. Added 4 personal data fields to Phase 2 (nationality, gender, birthday, place_of_birth — auto-derived where possible). Added `parse_ve_address()` for structured address parsing (city/state/zip extraction). |
| 2026-02-18 | 0.7.0 | Phase E completed: Batch wizard (`hr.data.collection.create.wizard` + line model), payslip batch button, standalone menu, stagger CRON (`_cron_start_pending()`, 30 min, batch_size=2, max_active=10), `hr_payroll_community` dependency. Module v1.18.0. |
