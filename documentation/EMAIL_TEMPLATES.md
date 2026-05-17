# Email Templates Documentation

## Overview

| Template | Use Case | Template ID (Testing/Production) |
|----------|----------|----------------------------------|
| Payslip Compact Report | Regular payroll | - |
| Payslip Email - Employee Delivery | Monthly detailed view with acknowledgment **(DEFAULT)** | 43 / 37 |
| Aguinaldos Email - Christmas Bonus Delivery | December Christmas bonuses | 44 / 38 |
| Payslip Ack Confirmation | Auto-sent after employee acknowledges payslip | 67 / 46 |

**Syntax Rules:**
- Headers (subject): Jinja2 `{{object.field}}`
- Body (body_html): QWeb `t-out="object.field"`

---

## Payslip Email - Employee Delivery Template

**Last Updated:** 2025-12-15

| Field | Value |
|-------|-------|
| Subject | `Comprobante de Pago - Nro.: {{ object.number }} - Lote: {{ object.payslip_run_id.name if object.payslip_run_id else "N/A" }}` |
| Email From | `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>` |
| Email To | `{{ object.employee_id.work_email }}` |
| Email CC | `recursoshumanos@ueipab.edu.ve` |

**Features:**
- Uses `object.exchange_rate_used` dynamically (fixed 2025-11-28)
- Includes digital acknowledgment button
- Button text: "Enviar conformidad digital"
- Acknowledgment title: "Acuso conformidad y recepcion digital de este comprobante"
- Records confirmation with date, time, and IP
- Deduction labels: IVSS 4%, FAOV 1%, Paro Forzoso 0.5%

### Exchange Rate Fix (2025-11-28)
- **Problem:** Template had hardcoded rate `241.5780` in JSONB `body_html` field
- **Solution:** Changed to `object.exchange_rate_used or 1.0` for dynamic lookup
- **Affected:** Both `es_VE` and `en_US` locale versions

### Salary Breakdown Fix (2025-12-15)
- **Problem:** Salary breakdown section was empty in delivered emails (DICIEMBRE15 batch)
- **Root Cause:** Template used `filtered(lambda ...)` which gets silently stripped in QWeb email rendering
- **Symptoms:** Working NOVIEMBRE30 emails had ~9KB body, broken emails only ~3KB
- **Solution:**
  1. Added `get_line_amount(code)` helper method to `hr.payslip` model
  2. Replaced all `filtered(lambda l: l.code == 'CODE')` with `object.get_line_amount('CODE')`
  3. Fixed via direct SQL update to `mail_template.body_html` JSONB field

**Template Update Method:**
```sql
UPDATE mail_template SET body_html = (SELECT pg_read_file('/tmp/template.json')::jsonb) WHERE id = 37;
```

**Template Features:**
- Uses `object.get_line_amount('VE_SALARY_V2')` instead of lambda filters
- Uses `object.exchange_rate_used or 1.0` for dynamic exchange rate
- Both `en_US` and `es_VE` locales identical (22,900 chars each)

---

## Aguinaldos Email Template

**Last Updated:** 2025-12-19 | **Template IDs:** Testing: 44, Production: 38

| Field | Value |
|-------|-------|
| Subject | `Aguinaldos (Bono Navideno) - Nro.: {{object.number}}{{ (" - Lote: " + object.payslip_run_id.name) if object.payslip_run_id else "" }}` |
| Email From | `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>` |
| Email To | `{{object.employee_id.work_email}}` |
| Email CC | `recursoshumanos@ueipab.edu.ve` |
| Salary Rule Code | `AGUINALDOS` (not VE_AGUINALDO_V2) |

**Technical Implementation:**
- Uses `object.get_line_amount('AGUINALDOS')` for total amount
- Uses `aguinaldo_portion = aguinaldo_total / 2.0` for 50/50 split
- Uses `object.contract_id.ueipab_salary_v2` for monthly salary reference
- Dynamic exchange rate (no hardcoded values)

**Design:** Christmas theme with red/green gradient header

**Salary Breakdown Section (Fixed 2025-12-19):**
- Salario Base Mensual (Referencia): from contract
- Aguinaldo LOTTT (50%): `aguinaldo_portion * exchange_rate`
- Aguinaldo Adicional UEIPAB (50%): `aguinaldo_portion * exchange_rate`
- Total Aguinaldos: `aguinaldo_total * exchange_rate`
- **Fix:** Math now adds up correctly (LOTTT + UEIPAB = Total)

**Content:** Explains Aguinaldos - 1 month per LOTTT + 1 additional month by UEIPAB policy

**Acknowledgment Button:** Included (same as Payslip Email template)

---

## Payslip Acknowledgment Landing Page

**Updated:** 2025-12-17

- Amount displayed in **VES (Bs.)** using payslip exchange rate
- Title: "Confirmar Recepcion Digital"
- Text: "Al hacer click en el boton, confirma que ha recibido y revisado este comprobante de pago de forma digital."
- Button: "Confirmar Recepcion Digital"
- Audit trail: Records date, time, and IP address

**Aguinaldos Fix (2025-12-17):**
- Landing page now correctly shows amount for Aguinaldos payslips
- Checks for `NET`/`VE_NET_V2` lines first
- Falls back to `AGUINALDOS` line for Christmas bonus payslips
- File: `controllers/payslip_acknowledgment.py:153-160`

---

## Payslip Ack Confirmation Email Template

**Added:** 2026-02-28 | **Template IDs:** Testing: 67, Production: 46

| Field | Value |
|-------|-------|
| Subject | `{{object.number}} ha sido confirmado exitosamente` |
| Email From | `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>` |
| Email To | `{{object.employee_id.work_email}}` |
| Email CC | `recursoshumanos@ueipab.edu.ve` |

**Trigger:** Automatically sent from `payslip_acknowledge_confirm()` controller after employee clicks "Confirmar Recepcion Digital" on the portal page.

**Content:**
- Green-themed "Confirmacion Registrada" header
- Payslip details: number, period, batch name
- Acknowledgment timestamp from `object.acknowledged_date`
- Contact info for HR questions

**Design:** Matches existing template style (same as reminder template but green instead of orange).

**Error Handling:** Wrapped in try/except — email failure never blocks the acknowledgment success page.

---

## mail.template body_html — Multilingual JSONB (Critical Pattern)

`body_html` uses `render_engine='qweb'` and stores as JSONB with per-language keys.

**Rules:**
- Always write via **direct SQL** updating **both** `en_US` and `es_VE` keys — ORM write only updates the current lang key; if `es_VE` is stale, the ORM reads the wrong version
- SQL pattern: `UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s` with `json.dumps({'en_US': body, 'es_VE': body})`
- Subject field is also JSONB — same pattern required
- Use `<t t-out="object.field"/>` or `<t t-att-href="object.method()"/>` (QWeb syntax, stored via SQL)
- `{{ object.field }}` Jinja2 syntax does NOT work — `render_engine='qweb'` ignores it
- For multilingual fix via XML-RPC (no direct DB access): call `write({'body_html': body}, context={'lang': 'es_VE'})` then again with `'en_US'`

---

## Adelanto de Prestaciones Sociales Email Template

- **Testing:** `mail_template` id=71 | **Production:** id=50
- Body managed via **direct SQL only** — ORM `Html` field sanitizer strips custom QWeb method calls (`object.get_liq_veb(...)`) on every `tmpl.write({'body_html': ...})`
- Always use: `env.cr.execute("UPDATE mail_template SET body_html = jsonb_set(body_html, '{en_US}', %s::jsonb) WHERE id=?", [json.dumps(body)])`
- Subject field is also `jsonb` — same SQL pattern required
- After SQL update, **restart Odoo** to flush ORM cache before sending test emails
- Production sync via psycopg2 inside Odoo container: `psycopg2.connect(host='postgres', dbname='DB_UEIPAB', user='odoo', password='odoo8069')`
- Color scheme: navy blue only — `#1a2c5b` (dark) / `#2471a3` (medium) / `#f0f4fa` (light bg). No red (`#c0392b`, `#7b1a1a`)
