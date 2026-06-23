# Payment Notice Email Blast — Banco de Venezuela Unavailable

**Created:** 2026-06-22
**Script:** `scripts/send_payment_notice_email.py`
**Status:** ✅ **SENT — fired `--live` 2026-06-22 20:02 (local)** against DB_UEIPAB; 269
recipients, 27 batches × 10, From/Reply-To `pagos@`. Two previews approved by CEO first.

---

## Purpose

One-off community blast informing all parents/representatives that the **Banco de
Venezuela** account is temporarily **unavailable** for payments, and listing the
alternative accounts (transfers + pago móvil) to use instead.

Built on the proven throttled-batch infrastructure validated by the Kurios
robotics newsletter (2026-06-22, see [[ROBOTICS_KURIOS_NEWSLETTER]] and memory
`patterns-prod-email-blast`).

---

## Message content (rendered as branded HTML)

- **Subject:** `AVISO IMPORTANTE SOBRE PAGOS 🚨`
- **Beneficiario:** INSTITUTO PRIVADO ANDRÉS BELLO, C.A. — RIF **J-08008617-1**

**🏦 Transferencias (Cuentas Corrientes):**

| Banco | Cuenta |
|-------|--------|
| Banco Plaza | 0138-0032-47-0320013870 |
| Banco BanPlus | 0174-0127-12-1274138559 |
| Banco Mercantil | 0105-0069-93-1069377856 |
| Banco Bancamiga | 0172-0702-44-7024976891 |

**📲 Pago Móvil:**

| Opción | Teléfono | Bancos |
|--------|----------|--------|
| A | 0414-1906296 | Mercantil 0105 / Banplus 0174 |
| B | 0414-2337463 | Banco Plaza 0138 |
| C | 0414-4375222 | Bancamiga 0172 |

**🌎 Pagos en Divisas** (captured from `/costos-escolaridad`; credit-card via Banco
Mercantil intentionally omitted):

| Método | Dato |
|--------|------|
| Zelle | pagos@ueipab.edu.ve — a nombre de INSTITUTO PRIVADO ANDRÉS BELLO, C.A. |
| Binance | Pay ID 383 867 49 |

The plain text the CEO supplied is rendered into the same branded card layout as the
Kurios newsletter: navy/yellow header with the 1080×1080 square logo, a beneficiary
card, two account tables (monospace numbers for easy copy), closing, and footer.

> **Single source of truth:** account numbers live in the `TRANSFERENCIAS` /
> `PAGO_MOVIL` lists at the top of the script. Edit there — the HTML renders from them.

---

## Recipients

- Hard-coded community list (identical to the Kurios newsletter list,
  `todalacomunidad@ueipab.edu.ve` included).
- **269 unique deliverable addresses** after case-insensitive dedup.
- **1 skipped** known hard-bounce (`olysamg@gmail.com`, EMIRO GONZALEZ, conv #44815).
- Every address gets its **own individual email** (one `mail.mail` per address —
  no shared To/CC, no leaked address lists).

---

## Sending infrastructure (reused verbatim from Kurios)

| Setting | Value |
|---------|-------|
| `BATCH_SIZE` | 10 emails per batch |
| `BATCH_INTERVAL` | 140 s between batches |
| `SEND_DELAY` | 0.15 s between individual creates |
| ETA | ~27 batches → **~60 min** for the full list |
| From | `pagos@ueipab.edu.ve` (Administración) — **see decision #1** |
| Reply-To | `pagos@ueipab.edu.ve` |
| Mail queue cron | id=3, `method_direct_trigger` per batch (releases immediately) |

**Resilience features carried over:**
- **SSL idle-socket reconnect:** `call()` rebuilds the XML-RPC connection on
  `SSLError`/`socket.error`/`ProtocolError`/`Fault`/`EOFError` (≤4 retries).
  Without this the first Kurios run crashed after batch 1 (`ssl.SSLEOFError`).
- **Crash-safe resume:** every sent address persisted to the state file
  (`PAYMENT_NOTICE_STATE`, default `/tmp/payment_notice_sent_state.json`)
  immediately after send → re-run skips them → zero double-sends.

---

## Usage

```bash
# 1. Dry-run — lists all recipients, sends nothing
python3 scripts/send_payment_notice_email.py

# 2. Preview — real send to CEO only (gustavo.perdomo@ueipab.edu.ve), with banner
python3 scripts/send_payment_notice_email.py --preview

# 3. Single explicit address (uses resume state — never double-sends)
python3 scripts/send_payment_notice_email.py --to someone@example.com

# 4. FULL community blast
python3 scripts/send_payment_notice_email.py --live
```

### Recommended deploy (detached, from the PROD host) — same as Kurios

Because the blast spans ~60 min, fire it detached so an SSH drop can't halt it:

```bash
# Stage script + minimal xmlrpc creds under /root/ on prod (10.124.0.3)
systemd-run --unit=payment-notice-blast --collect \
  --setenv=PAYMENT_NOTICE_PROD_CFG=/root/payment_notice/prod_cfg.json \
  --setenv=PAYMENT_NOTICE_STATE=/root/payment_notice/sent_state.json \
  python3 /root/payment_notice/send_payment_notice_email.py --live

journalctl -u payment-notice-blast -f
```

The creds file is the **xmlrpc block only** (`url`/`db`/`user`/`api_key`), NOT the
full `production.json` (keeps the server root password off the box).

> ⚠️ The script defaults `PROD_CFG` to `config/production.json` for local dev runs.
> On the prod host, set `PAYMENT_NOTICE_PROD_CFG` to the minimal creds file.

---

## Verification

Mails are created `auto_delete=True`, so successful sends vanish from `mail_mail`.
Confirm the run by watching the `mail_mail` `exception` count stay flat — failures
land there and persist. Gmail Workspace caps ~2,000 external recipients/day; 269 is
well within budget.

---

## Decisions (resolved 2026-06-22)

1. **From/Reply-To address** → `pagos@ueipab.edu.ve` for both. CEO-approved after a
   live preview confirmed the `pagos@` send-as alias delivers cleanly. (Fallback if it
   had bounced: `soporte@` sender + `pagos@` Reply-To.)
2. **Audience scope** → full community list as-is (269 deliverable).
3. **Channel** → **email only**.
4. **Credit card via Banco Mercantil** → intentionally **omitted**. Zelle + Binance Pay
   added from `/costos-escolaridad` per CEO request.

---

## Related

- `documentation/ROBOTICS_KURIOS_NEWSLETTER.md` — parent template
- Memory `patterns-prod-email-blast` — systemd deploy, SSL reconnect, resume pattern
- Memory `feedback_test_email_routing` — tests go to gustavo.perdomo@ (use `--preview`)
