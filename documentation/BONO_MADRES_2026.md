# Bono Día de las Madres 2026

**Status:** Testing — pending production deployment
**Version:** ueipab_payroll_enhancements 17.0.1.67.0
**Implemented:** 2026-05-06
**Event date:** Domingo 10 de mayo de 2026 (Día de las Madres, Venezuela)

One-time discretionary bonus of $10–$15 USD for all employees in recognition of Mother's Day. Amount configured via System Parameters — no code change needed to adjust it.

---

## Business Context

- Discretionary gratification — **not a contractual entitlement**, no contract field added
- Flat amount for all employees (same value regardless of salary grade)
- Payslip acknowledgment included for HR audit trail
- Same email dispatch flow as Aguinaldos (batch email wizard)

---

## Salary Structure

| Field | Value |
|-------|-------|
| Name | `Bono Día de las Madres` |
| Code | `BONO_MADRES` |
| Parent | `BASE` |
| Testing structure id | 11 |

### Salary Rules

| Code | Seq | Category | Formula | Accounting |
|------|-----|----------|---------|------------|
| `BONO_MADRES` | 10 | Earnings (BASIC) | reads `ir.config_parameter` via `payslip.env` | None (earnings don't post) |
| `BONO_MADRES_NET` | 200 | NET | `result = BONO_MADRES` | Debit `5.1.01.10.001` / Credit `1.1.01.02.001` |

**Testing rule IDs:** `BONO_MADRES` = 69, `BONO_MADRES_NET` = 70

---

## Amount Configuration

The bonus amount is stored in `ir.config_parameter`, **not hardcoded** in the rule.

**To change the amount:**
Settings → Technical → Parameters → System Parameters → search `payroll.bono_madres_2026` → edit **Value**

| Key | Default | Current (testing) |
|-----|---------|-------------------|
| `payroll.bono_madres_2026` | `12.50` | `12.50` |

Rules read it at compute time via:
```python
result = float(payslip.env['ir.config_parameter'].sudo().get_param('payroll.bono_madres_2026', '12.50'))
```

**Important:** Set the correct amount in System Parameters **before** clicking Compute on payslips. Once payslips are confirmed (`done`) they cannot be recomputed.

---

## Email Template

| Field | Value |
|-------|-------|
| Name | `Bono Día de las Madres - Entrega Especial` |
| Testing template id | 77 |
| Production template id | *assigned on deployment* |
| Model | `hr.payslip` |
| Subject | `🌸 Bono Día de las Madres │ Nro.: {{object.number}}{{ (" │ Lote: " + object.payslip_run_id.name) if object.payslip_run_id else "" }}` |
| From | `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>` |
| To | `{{object.employee_id.work_email}}` |
| CC | `recursoshumanos@ueipab.edu.ve` |
| Theme | Rose pink gradient (`#ad1457` → `#e91e8c`) |
| Attachment | None |

**Template source:** `addons/ueipab_payroll_enhancements/data/mail_template_payslip.xml`
`record id="email_template_bono_madres"`

### Body sections

| Section | Description |
|---------|-------------|
| Header | Pink/rose gradient — "🌸 Bono Día de las Madres" |
| Employee info | Nro. comprobante, período, nombre, cédula, cuenta |
| Info box | Warm institutional message — "Un reconocimiento con cariño" |
| Desglose del Bono | Single row: `BONO_MADRES` amount in Bs. |
| Total a Recibir | USD amount + VEB at applied exchange rate |
| Exchange rate reference | Dashed pink box — tasa aplicada |
| Ack button | Green gradient — `object._get_acknowledgment_url()` |
| Footer | Standard HR footer |

**Amount rendering:** `object.get_line_amount('BONO_MADRES') * (object.exchange_rate_used or 1.0)`

---

## Acknowledgment

Uses the existing payslip acknowledgment infrastructure:

- **Ack URL:** `object._get_acknowledgment_url()` (same as all other payslips)
- **Landing page:** Updated to show correct amount for `BONO_MADRES` payslips
  - File: `controllers/payslip_acknowledgment.py`
  - Change: `AGUINALDOS` fallback extended to `('AGUINALDOS', 'BONO_MADRES')`
- **Ack tracking:** Payroll → Payslips → Ack Status (same view as regular payslips)
- **Ack confirmation email:** Auto-sent on employee click (existing template id=67/46)

---

## HR Workflow (Testing & Production)

1. **Set bonus amount** — Settings → System Parameters → `payroll.bono_madres_2026`
2. **Create batch** — Payroll → Batches → New
   - Dates: e.g. 01/05/2026 – 11/05/2026
   - Structure: **Bono Día de las Madres**
3. **Generate payslips** — "Generate Payslips" button → all active employees
4. **Compute** — Compute Payslips (reads amount from System Parameters)
5. **Set exchange rate** — enter BCV rate on the batch
6. **Confirm payslips** — action_validate_payslips()
7. **Send emails** — Batch email wizard → select **"Bono Día de las Madres - Entrega Especial"** → Send
8. **Track acks** — Payroll → Payslips → Ack Status

---

## Production Deployment Checklist

| Step | Action |
|------|--------|
| A | Backup `DB_UEIPAB` — `pg_dump` |
| B | `scp` updated `ueipab_payroll_enhancements` to `/home/vision/ueipab17/addons/` |
| C | Upgrade module: `docker exec ueipab17 /usr/bin/odoo -d DB_UEIPAB -u ueipab_payroll_enhancements --stop-after-init` |
| D | Run setup script: `docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http < /home/vision/scripts/setup_bono_madres.py` |
| E | `docker restart ueipab17` |
| F | Verify: Settings → System Parameters → `payroll.bono_madres_2026` = `12.50` (or desired amount) |
| G | Verify: Settings → Technical → Email → Templates → "Bono Día de las Madres - Entrega Especial" exists |
| H | Verify: Payroll → Configuration → Salary Structures → "Bono Día de las Madres" exists with 2 rules |
| I | Smoke test: create 1-employee payslip with structure `BONO_MADRES`, compute → confirm amount correct |

**Note:** Module upgrade alone creates the email template (XML record). The setup script creates the salary structure and rules and seeds the System Parameter. Both are required.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_bono_madres.py` | Creates salary structure + rules + seeds System Parameter. Idempotent — safe to re-run. |
| `scripts/fix_bono_madres_rule.py` | Updates the BONO_MADRES rule formula only. Use if rule needs to be corrected without full re-setup. |

---

## Design Decisions

| Decision | Choice | Reason |
|---------|--------|--------|
| Contract field? | No | One-time discretionary bonus; contract fields imply recurring contractual obligation |
| Salary input line? | No | Flat amount for all employees; no per-employee variation needed |
| Amount storage | `ir.config_parameter` | HR-adjustable without touching code; readable from salary rule via `payslip.env` |
| Acknowledgment | Yes | Zero marginal effort; provides HR audit trail |
| PDF attachment | None | Not needed for a simple cash bonus; Aguinaldos had one due to complex 2-month breakdown |
| New module? | No | Extends existing `ueipab_payroll_enhancements` — same pattern as Aguinaldos |

---

## Known Limitations

- **`env` not available in salary rule safe_eval** — must access config parameter through `payslip.env`, not bare `env`. Direct arithmetic and object attribute access are allowed; standalone `env[]` lookups are not.
- **`noupdate="1"` on template XML** — the email template only loads on first install (not on subsequent upgrades). If the template body needs to be updated post-deployment, use direct SQL on `mail_template.body_html` JSONB field (same pattern as other templates).
- **Template id differs between environments** — testing id=77, production id assigned at deployment time. Do not hardcode the id anywhere.
