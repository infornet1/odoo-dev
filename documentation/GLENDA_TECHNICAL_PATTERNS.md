# Glenda Technical Patterns

Reference for all Glenda-specific implementation details. See also [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md).

---

## Silent Timeout + Proactive Quiet Hours (Feature #55)

- **`send_reminders` field on `ai.agent.skill`** (Boolean, default True) — if False, `_cron_check_timeouts` skips all `_send_reminder()` calls and closes the conversation silently via `action_timeout()` after one `reminder_interval_hours` window (24h for general_inquiry). No WA messages sent.
- **`general_inquiry` skill** has `send_reminders=False` — no "Te escribo por última vez…" farewell WA; conversations just expire silently.
- **`_in_proactive_quiet_hours()`** — returns True during 20:30–07:30 VET (overnight). Configurable via `ai_agent.proactive_quiet_start` / `ai_agent.proactive_quiet_end` params. Applied in `_cron_check_timeouts` to defer reminder WA sends during the window (silent timeouts still proceed — no WA cost).
- **Reactive replies are always allowed** — `_cron_poll_messages` (customer-triggered) is NOT gated by quiet hours; only `_cron_check_timeouts` (proactive) is blocked.
- **NameError fix** — `tertiary_phone` and `own_phones` are now defined in `_cron_poll_messages` alongside `primary_phone` (previously only defined inside `_get_or_create_general_inquiry_conversation`, causing NameError on non-primary account messages).

---

## OdooBot Bridge / Discuss (Feature #54)

- **File:** `addons/ueipab_ai_agent/models/mail_bot_glenda.py` — `_inherit = 'mail.bot'`
- **Hook:** overrides `_get_answer()` — fires only on `channel_type == 'chat'` (private OdooBot DM)
- **Guards:** `ai_agent.dry_run = True` → skips; `credits_ok = False` → blocked; any exception → falls back to default OdooBot silently
- **Knowledge:** imports `_INSTITUTIONAL_KNOWLEDGE` from `general_inquiry.py` at call time — same pricing/policies as WA Glenda
- **History:** fetches last 10 `mail.message` records from channel; builds alternating user/assistant list; merges consecutive same-role turns
- **Cost:** zero MassivaMóvil credits — never touches `whatsapp_service.py`; Claude Haiku only (~$0.001–0.003/conv)
- **Frontend next step:** install `im_livechat` (Odoo Community module, free) + extend `_get_answer` to also handle `channel_type == 'livechat'` → floating chat bubble on school website for customers
- **Announcement script:** `scripts/send_glenda_odoobot_announcement.py` — sends HTML email to all 52 internal users (set `DRY_RUN = False` to send)

---

## Auto Draft Payment — Payment Journal Map (Feature #51)

- **Config key:** `ai_agent.payment_journal_map` (JSON `ir.config_parameter`) — set in prod param id=71, testing param id=87
- **Schema:** `{"keywords": {"venezuela": {"VES": 162, "USD": 159}, ...}, "fallback_veb": 162, "fallback_usd": 158}`
- **10 banks mapped:** venezuela, mercantil, plaza, banplus, provincial/bbva (→ Banplus journal id=164), bancamiga, cashea, zelle, bicentenario
- **Currency ids:** USD=1, VEB=2 (used in all VEB journals); VES from OCR normalised to VEB
- **Matching:** VES amounts converted via BCV rate → USD for invoice comparison; exact ±2% tolerance; partial fallback (oldest-first)
- **Dedup:** last-4 digits of referencia, 30-day window, same partner — blocks draft creation entirely
- **Draft creation:** `account.payment` state=draft, never auto-posts; `payment_method_line_id` from journal's first inbound line
- **pagos@ email:** Odoo deep link + BCV conversion line + invoice match info + duplicate/no-match warning block
- **`pagos_receipt_processor.py`:** standalone script for Freescout unassigned convs; same pipeline via XML-RPC; image from `_embedded.attachments[].fileUrl` or body `<img>` regex; Freescout API `POST /conversations/{id}/threads` for note; subject prefix `[GLENDA]`; cron `/etc/cron.d/pagos_receipt_processor` every 15 min, production LIVE; sets `bank_reference` (bank ref number), `ref` (FS subject/communication), `date`+`effective_date` (from receipt, 2-digit year safe); only `state=published` convs processed; payment auto-confirmed via `action_post()` (not left as draft); `ai_agent.openai_api_key` prod param id=71, testing param id=88
- **Sender filter (2-tier):** `SYSTEM_EMAILS` hard-blocks automation accounts (`finanzas@`, `pagos@`, `mailer-daemon`, etc.) unconditionally; other `ueipab.edu.ve` senders (employees) get an early Odoo `customer_rank > 0` lookup — processed if they are also a parent/customer (e.g. employee with child enrolled), skipped silently otherwise; pre-fetched partner reused downstream (no double XML-RPC call)
- **`action_post()` None marshal quirk:** Odoo 17 XML-RPC server marshals `action_post` return value with `allow_none=False` — raises `Fault("cannot marshal None")` even when the post succeeded; script catches this specific Fault, re-reads payment `state`, treats as success if `state == 'posted'`
- **Bank code detection:** `_BANK_CODE_MAP` maps Venezuelan 4-digit account prefixes to bank keywords (e.g. `0174`/`0166` → `banplus`, `0102` → `venezuela`, `0105` → `mercantil`, `0172` → `bancamiga`). Strategy A regex scans `\b0NNN\b` as fallback after text keywords fail. GPT B/C prompts also include explicit code→name hints. Prevents wrong-journal fallback when receipt shows account number but no bank name text.

---

## BCV Rate Context (Feature #44)

- **Param:** `ai_agent.bcv_rate_context` — set by `scripts/sync_bcv_to_odoo.py` every 30 min (`/etc/cron.d/sync_bcv_odoo`) from BCV MySQL (`exchange_rates_bcv.bcv_rates`, user `bcv_script`)
- **JSON shape:** `{"current": {"rate": N, "date": "YYYY-MM-DD"}, "history": [{date, rate, min_rate, max_rate}, ...]}` — last 30 days
- **Skill:** `general_inquiry.get_context()` → `_build_bcv_block()` injected into system prompt; host-side sync required (Docker can't reach host MySQL/Flask)
- **Fallback:** if param missing → "no disponible, consulta bcv.gob.ve" — degrades gracefully

---

## Invoice Balance Query — ACTION:QUERY_BALANCE (Feature #45)

- **Trigger:** `ACTION:QUERY_BALANCE:FOUND` (phone match) or `ACTION:QUERY_BALANCE:V-XXXXXXXX` (cédula)
- **Handler:** `_handle_balance_action()` → `_query_partner_balance()` → posted out_invoices, not_paid/partial, partner + children
- **Delivery:** `action_process_reply()` sends breakdown as separate WA message; partner balance pre-loaded into system prompt context when partner found by phone
- **Security:** only shows balance for identified partner; cédula not found → error message to customer

---

## Daily Executive Digest (Feature #46)

- **Script:** `scripts/glenda_daily_digest.py`
- **Cron:** `/etc/cron.d/glenda_daily_digest` daily 07:00 VET (`0 11 * * *` UTC) → `gustavo.perdomo@ueipab.edu.ve`
- **5 sections:** KPIs, by-skill table, topic frequency (12 categories), escalations, suspicious activity (same phone >3 convs / tokens >600 / 01:00-05:00 VET / turns >18)
- **Manual run:** `python3 scripts/glenda_daily_digest.py --env production [--date YYYY-MM-DD] [--dry-run]`
- **Delivery:** `mail.mail` state=outgoing — Odoo scheduler sends within minutes

---

## Quotation Engine & Enrollment Info

- **2026-2027 enrollment:** Costos anuales $101,58/alumno (Seguro $30,58 + Guía Inglés $25 + Olimpiadas $10 + Enciclopedia $36 — aplica a todos los niveles). Pago vía acuerdo especial may-jul. REQUISITO: 2025-2026 completamente saldado — no puede inscribir con deuda. PDVSA benefit discontinued — new prospect → billing handoff.
- **Seguro Escolar 2026-2027 (Feature #67 — PENDING, deploy after budget announcement):** Seguros Caracas Accidentes Escolares, Alt. 2, 24h. Coverages: muerte/invalidez $4,000; G.M. accidentales $4,000; atención in situ INCLUIDA; poliomielitis/tuberculosis $1,200. Claims: WA (+58)0414-903.3738 / amis@grupov.com.ve / APP Asegurados / 0800-SEGUCAR. Local advisor (El Tigre): Sra. Johanna Hernández de Yung — johannayungh@gmail.com / suscripcionyung2020@gmail.com / WA https://wa.me/584248340051. PDF: `/home/ftpuser/odoo-dev/SeguroEscolar26-27.pdf`.
- **Quotation engine:** mensualidad + inscripción + costos anuales ($101,58/alumno) + TOTAL PRIMER MES. Sibling discounts: 1st 5%, 2nd 8%, 3rd+ 11%. Enciclopedia $36 aplica a todos los niveles (ya incluida en $101,58).
- **Tarifas 2025-2026 (hasta 31 ago):** $197,38 regular / $162,39 pronto pago (10 primeros días)
- **Tarifas 2026-2027 (inscripción anticipada hasta 31 jul):** inscripción $187,51 / mensualidad sep $197,38; puede prepagar meses adicionales a $197,38 c/u con descuentos hermanos
- **Nueva mensualidad desde 1 sep 2026:** $218,88 regular / $207,93 pronto pago (5% dto) — preliminar
