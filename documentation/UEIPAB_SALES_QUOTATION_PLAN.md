# UEIPAB Sales Quotation System — `ueipab_sales` Implementation Plan

**Status:** TESTING — Phases 1–5 built, validated & **PDF layout approved by Gustavo 2026-06-11** ("EUREKA", v3: logo 49px centered in header cell); next: Phase 6 (Glenda) + convenio due-date scheduling (§11, under analysis) → prod
**Created:** 2026-06-11
**Owner:** Gustavo Perdomo

**⚠️ EMAIL SAFETY RULE (Gustavo, 2026-06-11):** NEVER send any test email to customers. Test emails go ONLY to gustavo.perdomo@ueipab.edu.ve, CC pagos@ueipab.edu.ve, Reply-To pagos@ueipab.edu.ve.
**Consumers:** Glenda AI Agent (Telegram/WA) **and** human Sales team members (Sales app UI)

---

## 1. Purpose & Background

Move enrollment pricing out of Glenda's system prompt (`skills/general_inquiry.py`) into structured Odoo data, so quotations are **100% accurate by construction** — the LLM never writes a number; it triggers an engine that reads products and builds a real `sale.order`.

**Driver:** Comunicado oficial 10/06/2026 "Proceso de Inscripciones 2026-2027" defines 3 time-windowed enrollment llamados. Prompt-embedded prices have already caused stale/wrong quotes (conv #286 NELLYS ARAY, supervisor score 2/5; Opción A/B confusion post-vote).

**Benefits:**
- One source of truth: product → quotation → invoice (what Glenda quotes = what finance bills)
- Time expiration handled by data (validity dates), not prompt edits — 1 Aug rollover needs zero deployment
- Auditable: every quote is a numbered `sale.order` document tied to the partner
- Portal link: parent can view (and optionally sign) the quote online
- Sales team can create identical quotes manually via the Sales app

---

## 2. Pricing Source — Comunicado 10/06/2026 (Opción A aprobada)

### Three enrollment llamados

| Llamado | Window | Inscripción | Mensualidad | Convenio de pago |
|---|---|---|---|---|
| 1er — Promoción Especial | 11/06 → 31/07/2026 | **$187.51** | **$197.38** | ✅ Yes — preferential rate; solvency required **through June only**; julio+agosto payable normally; convenio schedules inscripción, septiembre, seguro, enciclopedias |
| 2do — Promoción Vacacional | 01/08 → 31/08/2026 | **$207.93** | **$218.88** | ❌ No — must be solvent by 31/07/2026 |
| 3er — Regular | 01/09 → 30/09/2026 | **$218.88** | **$218.88** | ❌ No — fully solvent with 2025-2026 |

### Other facts
- From **17/07/2026**: julio + agosto mensualidades billed in advance to statements
- Guía de Inglés: $35 hasta 31/07 → $40 desde 01/08
- Anuales per student: seguro $30.58 + inglés $35/$40 + olimpiadas $10 + enciclopedia $36 = **$111.58 / $116.58**
- From 01/09/2026: credit billing, 35% discretionary discount, industry-employer reimbursement **discontinued**
- Hermanos discounts (on base $218.88): 2 → −5% ($207.94) · 3 → −8% ($201.37) · 4+ → −11% ($194.80)
- Pronto pago: −5% on mensualidad ($207.93) — ⚠️ numerically equal to 2do llamado inscripción; keep concepts separate
- Administración opens Mon–Fri normally through all of August

### ✅ Business decisions (Gustavo, 2026-06-11)
- [x] **Stacking 1:** hermanos % **also applies under promo** → promo mensualidad per student: H2 $187.51 / H3 $181.59 / H4+ $175.67 (197.38 × 0.95/0.92/0.89)
- [x] **Stacking 2:** quotes in **USD** + mandatory note on every quote/PDF/message: *"Debe ser pagado a la tasa BCV del día"*
- [x] **Portal acceptance:** **read-only** in phase 1 (`require_signature=False`, `require_payment=False` on AI quotes)

---

## 3. Current Production State (audited 2026-06-11, read-only)

- `sale`, `sale_management`, `sale_pdf_quote_builder`, `sale_product_configurator`, `portal`, `crm` — **installed**; 1 test quotation (S00001, delete after exploration)
- Product catalog: 15 placeholder products at $1.00 (invoicing is manual-amount based today)
- **Reference product config — clone from `product.template` id=8 "MENSUALIDAD":** `detailed_type=consu`, customer tax id=1 "Exento (ventas)" 0%, invoice_policy=order, UoM Units, USD, income account empty (inherits category "All"), sale_ok=True
- Settings after Gustavo's setup wizard run (2026-06-11):
  - `portal_confirmation_sign=True` ✓ keep
  - `portal_confirmation_pay=True` ⚠️ **must disable** — no online payment provider; parents would be blocked from accepting
  - `sale.default_confirmation_template=11` — auto confirmation email on order confirm ⚠️ suppress for Glenda quotes
  - `quotation_validity_days=30` — override per-quote with llamado end date
  - Quotation Templates group: **not enabled** (settings toggle)
  - Pricelists: Basic only; single "Lista de precios USD predeterminada"
- Sales access: gustavo.perdomo@, alberto.perdomo@, finanzas@, tdv.devs@ = Sales Administrator; dubinis.cabeza@ = Own Documents

---

## 4. Product Catalog (Phase 1)

Category: keep **"All"** (inherits income account); filter via `default_code` prefixes.

### Inscripción — one per llamado (expiring)

| Code | Name | Price | Window |
|---|---|---|---|
| `INS2627-L1` | Inscripción 2026-2027 · 1er Llamado (Promoción Especial) | $187.51 | 11/06–31/07/2026 |
| `INS2627-L2` | Inscripción 2026-2027 · 2do Llamado (Promoción Vacacional) | $207.93 | 01/08–31/08/2026 |
| `INS2627-L3` | Inscripción 2026-2027 · 3er Llamado (Regular) | $218.88 | 01/09–30/09/2026 |

### Mensualidad — per case

| Code | Name | Price/student | Applies |
|---|---|---|---|
| `MEN2627-PROMO` | Mensualidad · Convenio 1er Llamado | $197.38 | convenio by 31/07 |
| `MEN2627-BASE` | Mensualidad · Tarifa regular | $218.88 | 1 student no convenio |
| `MEN2627-PP` | Mensualidad · Pronto pago (−5%) | $207.93 | early-pay window |
| `MEN2627-H2` | Mensualidad · 2 hermanos (−5%) | $207.94 | per student |
| `MEN2627-H3` | Mensualidad · 3 hermanos (−8%) | $201.37 | per student |
| `MEN2627-H4` | Mensualidad · 4+ hermanos (−11%) | $194.80 | per student |

### Anuales — per student

| Code | Name | Price | Valid |
|---|---|---|---|
| `SEG2627` | Seguro Escolar (Seguros Caracas) | $30.58 | all year |
| `ING2627-P` | Guía de Inglés · promo | $35.00 | hasta 31/07 |
| `ING2627-R` | Guía de Inglés · regular | $40.00 | desde 01/08 |
| `OLI2627` | Olimpiadas | $10.00 | all year |
| `ENC2627` | Enciclopedia | $36.00 | all year |

`description_sale` carries the validity text (shows on quote lines and PDF).

---

## 5. `ueipab_sales` Module (Phase 3)

New module `addons/ueipab_sales/` — v17.0.1.0.0.

| # | Feature | Detail |
|---|---|---|
| 1 | `is_glenda_quote` Boolean + `quote_channel` Selection (telegram/whatsapp/manual) on `sale.order` | Set by quote engine; list filter + form badge so finance distinguishes bot vs human quotes |
| 2 | **Customer-email suppression** for `is_glenda_quote` orders | Override confirmation-mail hook → Odoo sends nothing; delivery exclusively via Glenda message with portal link. Global toggle param `ueipab_sales.suppress_ai_quote_emails` (default True) |
| 3 | **Acceptance policy defaults** | Engine-created quotes: `require_signature=True`, `require_payment=False` regardless of company default (wizard re-runs can't re-enable online payment) |
| 4 | **Validity = llamado end date** | Engine sets `validity_date` to min(llamado end, today + N); promo window self-enforces in portal |
| 5 | Custom **PDF "Acuerdo de Inscripción"** | See §7 |
| 6 | (Nice-to-have) sequence `GQ/2026/####` for bot quotes; acceptance webhook → Glenda congratulates + notifies admin | Phase 2 of module |

Settings to change in Odoo (not module code): enable Quotation Templates group; disable portal payment requirement (keep signature). Decide whether template 11 stays as confirmation email for human quotes (recommended: yes).

---

## 6. Quotation Templates (Phase 4)

`sale.order.template` — one per case per llamado (prices differ per window):

- 1er Llamado: `1 estudiante` / `2 hermanos` / `3 hermanos` / `4+ hermanos` (lines: INS-L1 ×n + MEN ×n + SEG/ING-P/OLI/ENC ×n)
- 2do Llamado: same 4 (INS-L2, MEN base/hermanos, ING-R)
- 3er Llamado: same 4 (INS-L3)

= 12 templates. Engine picks by `date.today()` → llamado + `n_students` → case. Exact mensualidad product per case pends the stacking decisions (§2).

**Reference quote (validates engine):** 1 student, 1er llamado = $187.51 + $197.38 + $111.58 = **$496.47 primer mes** (matches Glenda conv #123 quote to NELLYS).

---

## 7. Custom Quotation PDF — "Acuerdo de Inscripción" (Phase 5)

Agreement-style layout with school logo, following the **Relación de Liquidación** pattern in `ueipab_payroll_enhancements`:

| Element | Pattern (from Relación) | For ueipab_sales |
|---|---|---|
| Report model | `models.AbstractModel`, `_name = 'report.<module>.<template_id>'` (exact match), `_get_report_values(docids, data)` builds a `reports` list of dicts | `report.ueipab_sales.quotation_agreement` over `sale.order` |
| QWeb template | `<t t-call="web.html_container">` → `<t t-call="web.basic_layout">` (UTF-8 safe), inline styles, 6.5–8pt tables, colored section headers (`<h5 style="background-color:#...; color:white">`) | Same skeleton; sections below |
| Paper format | Custom `report.paperformat`: Letter portrait, margins 10, `dpi=90`, `disable_shrinking=True`, no header line | `paperformat_quotation_agreement` |
| Report action | `ir.actions.report` `report_type=qweb-pdf`, `print_report_name` from partner name + date | `'Acuerdo_Inscripcion_%s_%s' % (partner, date)` |
| Logo | n/a in Relación | `<img t-att-src="image_data_uri(doc.company_id.logo)" style="max-height:80px"/>` — company logo is 1080×1080 square ✓ |

**Layout sections (agreement form):**
1. Header: logo + "ACUERDO DE INSCRIPCIÓN 2026-2027" + quote number + validity date
2. Representante data: name, cédula, phone, email / students + grades
3. Llamado box: which promoción applies + window ("Promoción Especial · válida hasta el 31/07/2026")
4. Pricing table: quote lines (inscripción, mensualidad ×10 months note, anuales) + totals
5. Convenio de pago terms (1er llamado only): payment schedule block
6. Condiciones: solvency requirement, expiration, post-expiry price ladder
7. Signature blocks: Representante / UEIPAB Administración + date lines

---

## 8. Glenda Integration — `ACTION:QUOTE` (Phase 6)

```
Parent asks price → Glenda emits ACTION:QUOTE:<n_students>
→ engine (ai_agent_conversation.py): date.today() → active llamado
→ pick sale.order.template (llamado × case) → create sale.order (partner from conversation)
→ is_glenda_quote=True, quote_channel, validity=llamado end, signature-only
→ read computed lines/total → format Spanish message verbatim + portal link (+PDF on request)
→ _send_to_user()
```

- Prompt change in `skills/general_inquiry.py`: replace the big COTIZACIÓN block with a short instruction ("price/enrollment-cost questions → emit ACTION:QUOTE:<n>") + keep solvency/convenio conversational knowledge
- Unidentified contact → identity ring first (existing flow); no quote without partner
- Repeat ask within same conv → reuse existing open quote, don't duplicate

---

## 9. Tracking Checklist

### Phase 0 — Decisions (Gustavo) ✅ 2026-06-11
- [x] Stacking 1: hermanos × promo → % stacks on promo rate
- [x] Stacking 2: USD + BCV-rate note on everything
- [x] Portal acceptance: read-only phase 1
- [ ] Delete test quotation S00001 (production)

### Phase 1 — Product catalog (testing) ✅ 2026-06-11
- [x] 17 products created (id=8 config cloned; +3 PROMO-H variants from stacking decision)
- [x] Validated via engine quotes (totals match hand-calc)

### Phase 2 — Sales settings (testing) ✅ 2026-06-11
- [x] Quotation Templates enabled
- [x] Portal payment requirement disabled (signature kept available)
- [ ] Confirm template 11 policy for human quotes (prod-time decision)

### Phase 3 — `ueipab_sales` module (testing) ✅ 2026-06-11
- [x] Module v17.0.1.0.0: `is_glenda_quote`/`quote_channel`, `_send_order_notification_mail` suppression (param `ueipab_sales.suppress_ai_quote_emails`, default True), `create_ai_quote()` engine, ribbon + filters
- [x] Installed in testing, clean

### Phase 4 — Quotation templates (testing) ✅ 2026-06-11
- [x] 12 templates created (3 llamados × 4 cases), BCV note as terms
- [x] Setup script idempotent: `scripts/setup_ueipab_sales_catalog.py` (reuse for prod)

### Phase 5 — PDF Acuerdo de Inscripción (testing) ✅ 2026-06-11
- [x] AbstractModel + QWeb + paperformat + action (binding on sale.order print menu)
- [x] Sample rendered (S00004, 2 hermanos, $973.20) — sent to Gustavo
- [x] Layout approval by Gustavo (2026-06-11, v3 — logo reduced 35% to 49px, centered in first header cell with padding; test mails 1112/1113/1114)

### Phase 6 — Glenda `ACTION:QUOTE` (testing)
- [ ] ACTION:QUOTE marker handler in `ai_agent_conversation.py` → `sale.order.create_ai_quote()`
- [ ] Prompt trim in `skills/general_inquiry.py` (quotation block → ACTION instruction + conversational knowledge)
- [ ] Test matrix: 3 llamados × 3 cases = 9 quotes verified (llamado override param for simulating L2/L3 dates)

**Validated engine totals (testing, 2026-06-11, L1):** 1 student $496.47 ✓ · 2 hermanos $973.20 ✓ · 3 hermanos $1,442.04 ✓ — S00003/S00004/S00005 (test partner Admin1; no emails sent)

### Phase 7 — Production deploy
- [ ] Products + settings + module + templates in prod
- [ ] Glenda prompt v-bump both envs
- [ ] First live quote monitored; supervisor cron review

---

## 10. Convenio Due-Date Scheduling — 1er Llamado only ✅ BUILT v17.0.1.1.0 (2026-06-11)

**Requirement (Gustavo):** under the 1er-llamado convenio, the customer can set a **specific payment due date per product**. **Final dates are set ONLY at premise signing** — Glenda may discuss a tentative schedule conversationally, but the binding dates are entered by the Sales team in the UI when the family visits to sign.

**Implemented (B + C approved):**
1. `ueipab_payment_due_date` (Date) on `sale.order.line` — visible column in order lines, set at signing
2. PDF "CONVENIO DE PAGO — FECHAS ACORDADAS" section (green header, 1er llamado only): Concepto | Monto USD | Fecha acordada; prints **blank `____/____/______` lines when unset** → the printed Acuerdo doubles as the fill-in form signed on premise
3. **"Generar Plan de Pagos"** button on confirmed orders (with confirm-dialog) → `action_generate_payment_plan()`: one **draft invoice per due-date group**, `invoice_date_due` = agreed date, BCV note in narration, lines linked to SO via `sale_line_ids`. Guards: order must be confirmed; all lines must have dates (UserError lists missing); double-run blocked while non-cancelled invoices exist
4. Existing WA/email invoice-reminder infra + Glenda balance queries pick the invoices up automatically — zero new reminder code

**Validated in testing (S00004, 2 hermanos):** confirm produced **0 customer emails** (suppression ✓); 4 draft invoices: 15/07 $375.02 (INS) · 15/08 $131.16 (SEG+ING) · 01/09 $375.02 (MEN) · 01/10 $92.00 (OLI+ENC) = $973.20 = order total ✓; double-run guard ✓; PDFs with-dates + blank-dates sent to Gustavo (mail 1115).

**Workflow:** Glenda quotes + invites family to visit → family comes to premise → team confirms order, enters final dates per line, prints Acuerdo, both sign → "Generar Plan de Pagos" → invoices carry the schedule; reminders chase each due date automatically.

**Remaining business question:**
- [ ] Date limits per concept (e.g. must everything be paid by 30/09?) — currently no constraint enforced

---

## 11. References

- Relación PDF pattern: `addons/ueipab_payroll_enhancements/models/liquidacion_breakdown_report.py` + `reports/liquidacion_breakdown_report.xml` + `reports/report_actions.xml`
- Logo: `https://odoo.ueipab.edu.ve/web/image/res.company/1/logo` (1080×1080)
- Glenda prompt: `addons/ueipab_ai_agent/skills/general_inquiry.py` (v58.1 — Opción A only)
- ACTION marker dispatch: `addons/ueipab_ai_agent/models/ai_agent_conversation.py`
- Comunicado: El Tigre, 10/06/2026 — "Proceso de Inscripciones Período 2026-2027"
