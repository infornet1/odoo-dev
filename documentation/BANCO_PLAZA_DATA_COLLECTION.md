# Banco Plaza Employee Data Collection Campaign

**Status:** Dry-run validated — ready to go live  
**Module:** `ueipab_hr_employee` v17.0.1.4.0  
**Created:** 2026-06-16

---

## Purpose

Banco Plaza requires 4 additional fields per employee to open mass payroll accounts:

| XLSX Col | Field | Format |
|----------|-------|--------|
| D | Segundo Nombre | Text (blank = no aplica) |
| F | Segundo Apellido | Text (blank = no aplica) |
| O | Operadora | 3-digit carrier code (412, 414, 416, 421, 422, 424, 426, etc.) |
| P | Número Telefónico | 7-digit number (without prefix) |

Source file: `/home/ftpuser/odoo-dev/Plantilla-Empleados-UEIPAB-FILLED(1).xlsx`  
Data rows: 8–51 (44 employees) | Headers: row 7 | Footer: row 54  

---

## Architecture

### Two-server design

| Server | Role |
|--------|------|
| `odoo.ueipab.edu.ve` (prod, `10.124.0.3`) | Hosts the public form + stores submissions in `ir.config_parameter` |
| `freescout.ueipab.edu.ve` (dev) | Hosts XLSX file + blast/sync scripts |

Submissions flow: employee fills form → stored in prod Odoo param → `sync_banco_plaza_xlsx.py` pulls via XML-RPC → writes XLSX.

### `ir.config_parameter` keys (prod Odoo, `DB_UEIPAB`)

| Key | Content |
|-----|---------|
| `banco_plaza.form_secret` | HMAC-SHA256 secret for token generation |
| `banco_plaza.employees` | JSON list of all 44 employees (set by blast script) |
| `banco_plaza.submissions` | JSON dict keyed by employee email, updated on each submit |
| `banco_plaza.campaign_open` | `'True'` / `'False'` — gates form access |
| `banco_plaza.dry_run` | `'True'` → all form ACK emails route to CEO inbox only |

---

## Public Form

**URL pattern:** `https://odoo.ueipab.edu.ve/banco-plaza-form/<token>`  
**Controller:** `addons/ueipab_hr_employee/controllers/banco_plaza_form.py`  
**Auth:** public (`auth='public'`)  
**Token:** `HMAC-SHA256(form_secret, employee_email.lower())[:24]`

### Features
- Pre-filled with XLSX data + any prior submission (re-editable)
- Client-side: digits-only JS filter on Operadora (max 3) and Número (max 7); auto-uppercase on name fields; disable-on-submit guard
- Server-side: name regex `[A-Za-záéíóúÁÉÍÓÚüÜñÑ'\s\-]+`; operadora `^\d{3}$`; número `^\d{7}$`; cross-validation (operadora ↔ número must both be present or both absent)
- Multi-edit: re-submittable until `campaign_open=False`
- On submit: saves to `banco_plaza.submissions` + sends 2 ACK emails

### ACK emails on submit

1. **Employee receipt** (`_send_ack_employee`): blast-style email to employee showing confirmed data, green rows for changed fields, "Actualizar mis datos" button. CC + Reply-To `recursoshumanos@ueipab.edu.ve`.
2. **HR diff notification** (`_send_notify_hr`): diff table (ANTERIOR vs NUEVO) to `recursoshumanos@ueipab.edu.ve`.

### Dry-run flag

When `banco_plaza.dry_run = 'True'` (set in `ir.config_parameter`):
- ACK email → `gustavo.perdomo@ueipab.edu.ve` (no CC)
- HR notify → `gustavo.perdomo@ueipab.edu.ve`
- Subject prefixed with `[DRY-RUN]`
- Submission data is **still saved normally** — dry-run only affects email routing

---

## Scripts

### `scripts/send_banco_plaza_data_blast.py` — Blast email sender

Reads XLSX, enriches phone data from prod Odoo, generates per-employee HMAC tokens, stores employee list + secret in prod Odoo params, sends personalized HTML emails.

```bash
# Test single employee (always → CEO inbox, no real employee email)
python3 scripts/send_banco_plaza_data_blast.py --test-employee ARCIDES

# Send to ALL 44 employees (live)
python3 scripts/send_banco_plaza_data_blast.py --live
```

**Email content:**
- Blue UEIPAB header + greeting
- Contingency plan intro paragraph
- Data table (red rows = PENDIENTE fields)
- Yellow CTA box with "Confirmar y/o Actualizar mis Datos →" button after the table
- HR contact footer

**Key constants:**
- `CEO_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'`
- `CC_EMAIL = 'recursoshumanos@ueipab.edu.ve'`
- `REPLY_TO = 'recursoshumanos@ueipab.edu.ve'`
- `FORM_BASE = 'https://odoo.ueipab.edu.ve/banco-plaza-form'`

**`ODOO_NAME_OVERRIDE`** — 4-part name exceptions (confirmed):
- `gustavo.perdomo@` → ('JOSE', 'MATA')
- `alejandra.lopez@` → ('CRISTINA', 'SAYAGO')

### `scripts/sync_banco_plaza_xlsx.py` — XLSX sync

Pulls `banco_plaza.submissions` from prod Odoo via XML-RPC and writes changes to the local XLSX file.

```bash
# Preview only (no file write)
python3 scripts/sync_banco_plaza_xlsx.py

# Apply changes to XLSX
python3 scripts/sync_banco_plaza_xlsx.py --apply
```

---

## Go-Live Checklist

1. **Validate full flow** with test employee (email → form → submit → ACK emails)
2. **Flip dry-run off** in prod Odoo:
   ```python
   # via Odoo shell or XML-RPC
   env['ir.config_parameter'].sudo().set_param('banco_plaza.dry_run', 'False')
   ```
3. **Send blast to all employees:**
   ```bash
   python3 scripts/send_banco_plaza_data_blast.py --live
   ```
4. **Monitor** responses in `banco_plaza.submissions` (prod Odoo param)
5. **Close campaign** when collection is complete:
   ```python
   env['ir.config_parameter'].sudo().set_param('banco_plaza.campaign_open', 'False')
   ```
6. **Sync XLSX:**
   ```bash
   python3 scripts/sync_banco_plaza_xlsx.py          # preview
   python3 scripts/sync_banco_plaza_xlsx.py --apply  # write
   ```
7. Submit completed XLSX to Banco Plaza

---

## Phone Validation Notes

- `VALID_OPS` check removed — any 3-digit numeric code accepted (covers 422 and future carriers)
- Three employees had corrupt phone data in XLSX (operadora=41, numero=48321963 = backup WA number): LUIS RODRIGUEZ, MARIA FIGUERA, ROBERT QUIJADA — these are treated as PENDIENTE by the blast script

---

## ARCIDES ARZOLA — Test Employee

- **Row:** 10 in XLSX
- **Token:** `44f1a3285e79b67968f3bf48`
- **Form URL:** `https://odoo.ueipab.edu.ve/banco-plaza-form/44f1a3285e79b67968f3bf48`
- **Dry-run submission recorded:** 2026-06-16 19:53 (test values — not real data)
