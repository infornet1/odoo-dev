# SMS Channel — MassivaMóvil SMS API Integration (Invoice Reminder Wizard)

**Created:** 2026-06-24
**Status:** 🛠️ PLAN — pre-flight passed (1000 credits); not yet built
**Goal:** Add **SMS** as a 3rd delivery channel in the "Recordatorio de Saldo" wizard
(`account.invoice.reminder.wizard`, `ueipab_payroll_enhancements`), alongside the
existing **Email** and **WhatsApp** channels.
**Related:** [WA_INVOICE_REMINDER_PLAN.md](WA_INVOICE_REMINDER_PLAN.md)

---

## 0. Pre-flight check (2026-06-24) ✅

Balance endpoint (read-only, no SMS sent):

```
GET/POST https://sistema.massivamovil.com/webservices/obtenerCreditoDisponible
         ?usuario=webmaster@ueipab.edu.ve&clave=***&api=json
-> HTTP 200  {"creditos": "1000", "mensaje": "consulta exitosa"}
```

Credentials valid; **1000 SMS credits** available. HTTPS OK, both GET and POST work.

---

## 1. ⚠️ This is a DIFFERENT API from the WhatsApp one

| | WhatsApp (existing) | **SMS (new)** |
|---|---|---|
| Host | `whatsapp.massivamovil.com/api` | `sistema.massivamovil.com/webservices` |
| Auth | `secret` + `account` (unique_id) | **`usuario` (email) + `clave` (password)** |
| Config file | `config/whatsapp_massiva.json` | **`config/sms_massiva.json`** (gitignored) |
| Phone format | `+58XXXXXXXXXX` | **`58XXXXXXXXXX`** (no `+`) |

Do **not** reuse the WA secret/account — SMS uses the webmaster login/clave.

---

## 2. Endpoints

**Send** (GET or POST form-data; POST recommended for volume):
```
https://sistema.massivamovil.com/webservices/SendSms
  usuario=<email>  clave=<password>  telefonos=<...>  texto=<...>  api=json
```

**Balance:**
```
https://sistema.massivamovil.com/webservices/obtenerCreditoDisponible
  usuario=<email>  clave=<password>  api=json
```

`&api=json` → JSON response; omit or `&api=XML` → XML. Always send over **https**.

### Response (JSON)
```json
{ "mensaje": "Envio Exitoso", "status": "1",
  "telefonos": [ { "sid": "584265207594", "status": "0",
                   "num_celular": "584265207594", "texto": "..." } ] }
```
- Top-level `status` **> 0** = number of messages accepted in the batch; **negative** = error.
- Per-recipient result in `telefonos[].status` (`0` = OK).
- Balance reply: `{"creditos": "<n>", "mensaje": "consulta exitosa"}`.

---

## 3. Batching & multi-message rules

- **Max 50 numbers per request** (tanda/bloque). Chunk the recipient list into ≤50.
- **Same message to many:** `telefonos` = phones joined by `;`, single `texto`.
  - `telefonos="584265207594;584242195147"` · `texto="prueba 1"`
- **Different message per number:** phones `;`-joined, `texto` = messages `|`-joined,
  **counts must match.**
  - `telefonos="58...A;58...B"` · `texto="msg A|msg B"`
- Our case = **per-customer balance** → use the *different-message* form (`|`-joined),
  ≤50 per batch. (Each customer's balance differs, so we can't use the same-message form.)

---

## 4. ⚠️ Character restrictions (CRITICAL — affects message text)

**Allowed:** `. , ; : - _ " @ / % ( ) = !`

**Forbidden:** `' ¡ ¿ \ º | { } [ ] \` ^ Ü € ? $ # á é í ó ú ñ`

Implications for our Spanish messages — they **must be sanitized**:
- **Strip accents:** á→a, é→e, í→i, ó→o, ú→u, ü→u. ("Andrés" → "Andres")
- **`ñ` → `n`** ("compañía" → "compania")
- **No `$`** → write amounts as `USD 128.30` (not `$128.30`)
- **No `?`** (drop question marks), **no `'`**, **no `#`**, **no `|`** in the text
  (`|` is the multi-message separator).
- Keep within **160 chars** (1 SMS = 1 credit; longer = multiple credits).

A `_sanitize_sms(text)` helper is required: unicode-normalize (NFKD, drop combining
marks), map `ñ/Ñ`, strip forbidden chars, collapse whitespace.

### Proposed SMS-safe template (generic / Standard, ~150 chars)
```
Colegio Andres Bello: su saldo pendiente es de USD {monto}. Le invitamos a pagar
a la tasa BCV oficial, consultela en bit.ly/tasabcv. Recordatorio automatico de cobranza.
```
(PDVSA-segment variant could add a short "adelante 35%" line — TBD, same sanitizer.)

---

## 5. Forbidden content & compliance
Massiva prohibits: **SMS políticos, de envite y azar** (gambling/lottery/horse racing).
Balance reminders are fine.

---

## 6. Wizard integration design (proposed)

Mirror the existing WA channel in `account.invoice.reminder.wizard`:

- **Eligibility:** new `sms_will_send` per line = `not biz_skip and bool(mobile)`
  (same `mobile` source as WA; normalize to `58XXXXXXXXXX`, strip `+`/spaces).
- **Stats:** `sms_count` computed (selected & sms_will_send).
- **Button:** "Enviar SMS" in the footer; `action_send_sms()` calls `_sync_eligibility()`
  first (same authoritative-recompute guard as email/WA), then sends.
- **Message by segment** (reuse the WA rule): `all` → Standard for everyone;
  PDVSA segments → PDVSA variant for PDVSA rows. Sanitized for SMS.
- **Send mechanism — decision D-SMS-1 below.**
- **Dedup:** same-day guard (state file `scripts/sms_reminder_state.json` or per-line
  status), to avoid double-charging credits.
- **Config:** `config/sms_massiva.json` (gitignored) — usuario/clave/base_url.
- **Result handling:** parse `telefonos[].status`; mark each line sent/failed; surface
  a tally + remaining `creditos` (call balance after).

---

## 7. Open decisions (need sign-off before build)

| ID | Decision | Options |
|----|----------|---------|
| **D-SMS-1** | Send mechanism | (a) **Inline** from the wizard (fast — SMS has no 120s anti-spam; OK for ≤50–100 in one POST per 50-batch) vs (b) **background script + poller** like WA (safer for large lists / avoids UI HTTP timeout). Recommend **(a) inline with ≤50 chunking** given the bulk endpoint is fast; fall back to script only if lists get very large. |
| **D-SMS-2** | Message length/variant | Single short Standard SMS for all, OR a distinct PDVSA SMS variant. Recommend **single Standard** first (simplest, 1 credit). |
| **D-SMS-3** | Channel selection UI | Separate "Enviar SMS" button (recommend) vs a channel multi-select. |
| **D-SMS-4** | Credit guard | Pre-check `obtenerCreditoDisponible` ≥ recipient count before sending; abort with a clear message if insufficient. Recommend **yes**. |
| **D-SMS-5** | Dedup scope | Per-day per-partner (recommend) vs none. |

---

## 8. Implementation phases (once approved)

1. **Phase 1 — Client lib:** `config/sms_massiva.json` (done) + a small `sms_massiva`
   helper (send batch, balance, `_sanitize_sms`, phone-normalize, response parse).
2. **Phase 2 — Wizard:** `sms_will_send`/`sms_count`, "Enviar SMS" button,
   `action_send_sms()` with `_sync_eligibility` + ≤50 chunking + credit guard + dedup.
3. **Phase 3 — Test:** dry-run (build batches, no send) → single live SMS to an
   internal number → small live batch → verify per-recipient status + credit decrement.
4. **Phase 4 — Deploy:** testing → prod (scp + `-u ueipab_payroll_enhancements` + restart).

Test sends go to an internal number only (never customers) until validated.

---

## 9. Security
- Credentials in `config/sms_massiva.json` (**gitignored** — confirmed `git check-ignore`).
  Never commit the clave; never log it.
- Use HTTPS; consider moving creds to `ir.config_parameter` for prod parity (like the
  Freescout/WA pattern) in a later pass.
