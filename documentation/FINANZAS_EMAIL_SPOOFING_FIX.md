# Finanzas@ Email Spoofing & Backscatter Fix

**Date:** 2026-05-13
**Updated:** 2026-05-14
**Status:** Fully Hardened
**Reported by:** Gustavo Perdomo

---

## Problem

13 conversations appeared in the **Deleted folder** of the `finanzas@ueipab.edu.ve` FreeScout mailbox today, all with subject `Delivery Status Notification (Failure)` from `mailer-daemon@googlemail.com`.

---

## Root Cause

**Email spoofing / backscatter spam.** A compromised third-party server (`gosportrotaryclub.org`) was sending mass emails to random `@email.com` addresses (e.g. `f47h2sfuzuh88v1dq7wv@email.com`) using `finanzas@ueipab.edu.ve` as the forged From/Return-Path address.

When those emails bounced (550 "mailbox unavailable"), `mail.com` sent the NDR (Non-Delivery Report) back to the forged sender — `finanzas@`. Google delivered them to the finanzas@ inbox, and FreeScout ingested them.

### Key Evidence

| Indicator | Finding |
|-----------|---------|
| Original `Message-ID` domain | `@gosportrotaryclub.org` — NOT ueipab servers |
| Message-IDs in FreeScout | None found — finanzas@ never sent these |
| Destination addresses | Random tokens (e.g. `f47h2sfuzuh88v1dq7wv@email.com`) |
| FreeScout handling | Auto-routed to Deleted (correct — `Auto-Submitted` header detected) |
| Volume | 13 bounces, first occurrence in 30+ days |
| Your outbox | Clean — no compromise of finanzas@ account |

### Why Spoofing Was Possible

`ueipab.edu.ve` had **no SPF and no DMARC record**, allowing anyone to forge the domain as the email sender with zero enforcement.

| Record | Before | After |
|--------|--------|-------|
| SPF | ❌ Missing | ✅ Added |
| DKIM | ✅ Already present (`google._domainkey`) | ✅ Unchanged |
| DMARC | ❌ Missing | ✅ Added |

---

## Fix Applied

Two DNS TXT records added via **DigitalOcean DNS** on 2026-05-13:

### SPF (root domain `@`)
```
v=spf1 include:_spf.google.com ip4:64.23.157.121 ~all
```
- `include:_spf.google.com` — covers all FreeScout mailboxes (use `smtp.gmail.com`)
- `ip4:64.23.157.121` — covers server (Odoo / scripts)
- `~all` — softfail; upgrade to `-all` after confirming no other sending sources

### DMARC (`_dmarc` subdomain)

**Initial (2026-05-13):**
```
v=DMARC1; p=quarantine; rua=mailto:finanzas@ueipab.edu.ve; pct=100
```

**Upgraded to `p=reject` (2026-05-14):** ✅
```
v=DMARC1; p=reject; rua=mailto:finanzas@ueipab.edu.ve; pct=100
```
- `p=reject` — spoofed emails blocked at recipient server before delivery; fully stops backscatter
- Upgrade triggered by: campaign escalation (13 → 78 bounces/day) + first DMARC report confirming legitimate email 100% passing
- `rua=` — daily aggregate reports continue to arrive at `finanzas@`

---

## Verification

```bash
host -t TXT ueipab.edu.ve
# v=spf1 include:_spf.google.com ip4:64.23.157.121 ~all

host -t TXT _dmarc.ueipab.edu.ve
# v=DMARC1; p=quarantine; rua=mailto:finanzas@ueipab.edu.ve; pct=100
```

SPF confirmed propagated on 2026-05-13.
DMARC `p=quarantine` confirmed propagated on 2026-05-13.
DMARC `p=reject` deployed on 2026-05-14 (propagation in progress).

---

## FreeScout Behavior (No Changes Needed)

FreeScout correctly auto-routes NDR/bounce emails (`Auto-Submitted` header) to the **Deleted folder** (state=3, folder type=70). This is expected behavior — no workflow rule or script was responsible.

The 2 other deleted conversations that day were legitimate internal automated emails:
- `[BDV-AUTO] ✅ Daily statement processed successfully` (from `finanzas@ueipab.edu.ve`)
- `Tasa BCV Actualizada: 504,914600` (from `finanzas@ueipab.edu.ve`)

These were also auto-deleted by FreeScout because they originated from an internal address — correct behavior.

---

## DMARC Aggregate Reports

Daily XML reports are sent automatically by major providers to **`finanzas@ueipab.edu.ve`**.

### What to expect

- **Senders:** `noreply-dmarc-support@google.com`, `postmaster@yahoo.com`, `dmarcreport@microsoft.com`
- **Subject format:** `Report domain: ueipab.edu.ve Submitter: google.com ...`
- **Attachment:** `.xml.gz` file (compressed XML, not human-readable directly)
- **Frequency:** Once per day per provider (usually arrives early morning)

### Reading the reports

Paste the XML into **https://dmarcian.com/dmarc-xml/** to get a readable table. Look for:

| Source IP | DKIM | SPF | Meaning |
|-----------|------|-----|---------|
| `209.85.x.x` | pass | pass | Google Workspace — expected ✅ |
| `64.23.157.121` | pass | pass | Your server (Odoo/FreeScout) — expected ✅ |
| Any other IP | fail | fail | Spoofing attempt — investigate ⚠️ |

### Raw XML structure (reference)

```xml
<record>
  <row>
    <source_ip>209.85.128.47</source_ip>
    <count>5</count>
    <policy_evaluated>
      <dkim>pass</dkim>
      <spf>pass</spf>
    </policy_evaluated>
  </row>
</record>
```

---

## Upgrade Path

### Step 1 — SPF hardening (`~all` → `-all`)

After 1–2 weeks with no delivery complaints, update the SPF record in DigitalOcean DNS:

```
v=spf1 include:_spf.google.com ip4:64.23.157.121 -all
```

`-all` = hard fail — unauthorized servers are rejected outright (currently `~all` = softfail).

### Step 2 — DMARC hardening (`p=quarantine` → `p=reject`) ✅ Done 2026-05-14

Upgraded after first DMARC report (Google, covering 2026-05-13) confirmed:
- 43 legitimate Google Workspace emails → all `pass` ✅
- 2 spoofed emails from `198.163.192.180` (Uzbektelekom, Tashkent 🇺🇿) → `quarantine` ✅
- No unknown legitimate sending sources found

Current record:
```
v=DMARC1; p=reject; rua=mailto:finanzas@ueipab.edu.ve; pct=100
```

---

## Follow-up Actions

- [x] **DMARC reports** — first report received 2026-05-14 from Google; only expected IPs found
- [x] **Upgrade DMARC** `p=quarantine` → `p=reject` — deployed 2026-05-14
- [ ] **Monitor bounce volume** — should drop significantly within 24–48h of 2026-05-14 as `p=reject` propagates
- [ ] **Upgrade SPF** `~all` → `-all` — around 2026-05-27 if no delivery complaints; update `ueipab.edu.ve` TXT in DigitalOcean DNS
- [ ] **Check other domains / subdomains** if any are used for sending email
