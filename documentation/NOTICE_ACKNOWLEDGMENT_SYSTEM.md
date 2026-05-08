# Notice Acknowledgment System

**Module:** `ueipab_attendance_report` v17.0.1.5.0
**Status:** Production deployed 2026-05-08 (email send scheduled next week)
**Last Updated:** 2026-05-08

---

## 1. Purpose

Generic system for tracking whether employees have read and acknowledged institutional communications sent by email. Built to be reusable across any future campaign — policy updates, handbooks, guides, announcements — without writing new code.

First use case: **Gestión de Control de Asistencia — Guía Visual** (attendance guide sent May 2026).

---

## 2. Architecture

### 2.1 Model — `hr.notice.acknowledgment`

| Field | Type | Description |
|-------|------|-------------|
| `notice_key` | Char | Machine key identifying the campaign, e.g. `attendance_guide_v1` |
| `notice_label` | Char | Human-readable title shown in UI and confirmation page |
| `employee_id` | Many2one | Links to `hr.employee` |
| `token` | Char (UUID) | Auto-generated on `create()`, unique per employee per send |
| `state` | Selection | `pending` → `acknowledged` |
| `sent_date` | Datetime | Auto-set to now on create |
| `ack_date` | Datetime | Set by public controller when employee clicks |
| `ack_ip` | Char | IP address captured at click time |
| `days_pending` | Integer | Computed (non-stored): days since sent without acknowledgment |

**Key methods:**
- `_get_ack_url()` — returns `https://<web.base.url>/notice-ack/<token>`
- `action_mark_acknowledged()` — HR manual override (records `ack_ip='manual-hr'`)
- `action_reset_pending()` — resets to pending for re-sends

### 2.2 Public Controller — `/notice-ack/<token>`

```
GET /notice-ack/<token>
  auth='public' — no login required
  → Looks up hr.notice.acknowledgment by token
  → If not found: renders "invalid token" page (red ✗)
  → If already acknowledged: renders "already done" page (blue 📋)
  → If pending:
      state = 'acknowledged'
      ack_date = now()
      ack_ip = X-Forwarded-For or remote_addr
      → renders "confirmation registered" page (green ✅)
```

Response pages are inline HTML (no QWeb template dependency) styled with UEIPAB navy/blue colors.

### 2.3 Email Template

| Setting | Value |
|---------|-------|
| Testing id | 84 |
| Production id | 58 |
| Model | `hr.notice.acknowledgment` |
| From | `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>` |
| To | `{{ object.employee_id.work_email }}` |
| CC | `recursoshumanos@ueipab.edu.ve` |
| Subject | `Gestión de Control de Asistencia - Guía Visual \| Andrés Bello` |

**Key QWeb in body** (stored via SQL — bypasses ORM sanitizer):
- Employee name: `<t t-out="object.employee_id.name"/>`
- ACK button URL: `<a t-att-href="object._get_ack_url()">...</a>`

---

## 3. Send Flow

```
1. Create hr.notice.acknowledgment records
   env['hr.notice.acknowledgment'].create({
       'notice_key':   'attendance_guide_v1',
       'notice_label': 'Gestión de Control de Asistencia — Guía Visual',
       'employee_id':  emp.id,
   })
   → token auto-generated, state=pending, sent_date=now

2. Send email via template
   tmpl.send_mail(ack.id, force_send=True)
   → email_to: employee work email
   → CC: recursoshumanos@ueipab.edu.ve
   → body rendered: employee name + unique ACK button URL

3. Employee clicks green button in email
   → browser hits /notice-ack/<token>
   → controller sets state=acknowledged, ack_date, ack_ip
   → employee sees confirmation page

4. HR tracks status
   Payroll → Reports → Notice Acknowledgments
   → filter by Pending / Acknowledged
   → group by notice_key
   → Manual Acknowledge button for employees who can't click
```

---

## 4. Odoo UI — HR View

**Menu:** Payroll → Reports → Notice Acknowledgments

**Tree view columns:** Employee | Notice Title | Status (badge) | Sent On | Acknowledged On | Days Pending | IP

**Filters:**
- Pending — all unacknowledged records
- Acknowledged — confirmed records

**Group By:** Notice (default) | Status | Employee

**Form view actions:**
- `Mark Acknowledged (Manual)` — for employees without email access
- `Reset to Pending` — for re-sends

**Security:**
- `hr_payroll_community_manager` — full CRUD
- `hr_payroll_user` — read only

---

## 5. Future Campaigns

To track acknowledgment for a new communication:

1. **Create records** with a new `notice_key`:
   ```python
   for emp in employees:
       env['hr.notice.acknowledgment'].create({
           'notice_key':   'reglamento_interno_v1',
           'notice_label': 'Reglamento Interno 2026',
           'employee_id':  emp.id,
       })
   ```

2. **Update template body** (or create a new template) with the communication content + ACK button.

3. **Send** via `tmpl.send_mail(ack.id, force_send=True)` per record.

4. **Track** in the Notice Acknowledgments menu filtered by `notice_key`.

No new code is needed for additional campaigns.

---

## 6. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_attendance_email_template.py` | Create/update testing template id=84, create ack record, send test email |
| `scripts/send_attendance_guide_production.py` | Bulk send to all production employees (creates ack records + sends) |

---

## 7. Infrastructure Notes

### nginx (dev.ueipab.edu.ve)
The following routes were added to the Odoo proxy location regex:
```nginx
location ~ ^/(web|website|...|notice-ack|attendance-ack|attendance-fix|attendance-correction)(/|$) {
    proxy_pass http://127.0.0.1:8019;
}
```
Without this, public routes return 404 (handled by Flask on port 5000 instead of Odoo).

### odoo.conf — dbfilter
Changed from `^(DB_UEIPAB|testing|openeducat_demo)$` to `^testing$`.

When multiple databases match the filter, Odoo cannot determine which DB to use for cookieless public requests — returns 404 on custom routes. Single-DB filter forces auto-selection.

### web.base.url
Set to `https://dev.ueipab.edu.ve` (was `http://dev.ueipab.edu.ve:8019`).
Affects all generated URLs: ACK buttons, attendance report links, payslip links.

---

## 8. Technical Notes — mail.template body_html (JSONB)

`body_html` uses `render_engine='qweb'` and stores as multilingual JSONB.

**Critical rules:**
1. Always write body via **direct SQL** — ORM write only updates the current language key
2. Update **both** `en_US` and `es_VE` — system language is `es_VE`; stale key causes ORM to return old body
3. SQL: `UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s` with `json.dumps({'en_US': body, 'es_VE': body})`
4. Use **QWeb** syntax (`t-out`, `t-att-href`) — NOT Jinja2 `{{ }}`
5. Via XML-RPC (no direct DB): call `write({'body_html': body}, context={'lang': 'es_VE'})` then `{'lang': 'en_US'}`

---

## 9. Version History

| Version | Date | Change |
|---------|------|--------|
| 17.0.1.5.0 | 2026-05-08 | Initial: model, controller, views, email template, ACK button. Deployed to production. Email send to all employees scheduled for next week. |
