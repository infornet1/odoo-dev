# Encuesta — Plan de Contingencia Académica (Modelo Bimodal)

**Status:** 🟢 **LIVE IN PRODUCTION** — deployed + blasted 2026-06-29 (email 169/169 + WA 9/9; voting open through Jul 1)
**Type:** Emergency institutional SÍ/NO consultation · **Service account:** `votacion@ueipab.edu.ve` (same account as the budget vote)
**Module:** `ueipab_attendance_report` **v17.0.1.6.31** (prod) · **notice_key:** `contingencia_academica_2026`

---

## 1. Purpose

A SÍ/NO consultation asking ACTIVE families whether to activate a **bimodal academic
contingency plan** (Google Classroom + Google Meet) so the school year is not interrupted
while government directives keep students at home. The measure activates **only upon
reaching 50% + 1** approval of the total roster ("plantilla").

This is an *emergency* one-off vote built on the **same reusable voting stack** as the
2026-2027 budget vote and the PDVSA continuity campaign — it is not a new subsystem.

> **Why it lives in `ueipab_attendance_report`:** historical, not architectural. The
> `partner.communication.ack` model + the `/partner-ack/<token>` public controller +
> the monitor views already live there (that module became the home for public
> token-route controllers). Re-homing them to `ueipab_ai_agent`/`ueipab_campaigns` is
> documented tech debt (CLAUDE.md → *PENDING — Refactor*); decision **2026-06-29: leave
> as-is** for this campaign.

---

## 2. Vote mechanism

Reuses `partner.communication.ack` (one row per family, unique `token`, audit fields):

| Customer action | URL | ACK state | Meaning |
|---|---|---|---|
| SÍ estoy de acuerdo | `/partner-ack/<token>/si` | `continuing` | Aprueba el plan bimodal |
| NO estoy de acuerdo | `/partner-ack/<token>/no` | `leaving` | Mantener esquema actual |

- `notice_key = 'contingencia_academica_2026'`
- `notice_label = 'Plan de Contingencia Académica — Modelo Bimodal'`
- **Deadline gate:** `_VOTE_DEADLINES['contingencia_academica_2026'] = date(2026, 7, 1)`
  in `controllers/partner_ack.py`. Gate is `today > deadline` → voting is **open through
  all of Jul 1**, closed from Jul 2 (48h window opened 2026-06-29).
- From / CC / Reply-To and all `mailto:` → `votacion@ueipab.edu.ve`.

> ⚠️ The model's `state` Selection labels are budget-era (`continuing`="Opción A",
> `leaving`="Opción B"), so the **monitor list badge** still reads Opción A/B — read
> **Opción A = SÍ (de acuerdo)**, **Opción B = NO**. The public pages, confirmation
> email, and the **"Voto Asistido" wizard** all show the correct SÍ/NO wording
> (see §3.5).

---

## 3. Components

### 3.1 Backend — `addons/ueipab_attendance_report/controllers/partner_ack.py` (v17.0.1.6.29)
Made notice-key-aware for `contingencia_academica_2026`, mirroring the budget special-case:
- `_VOTE_DEADLINES` → adds the contingencia deadline.
- `_vote_context()` → SÍ label **"SÍ — Estoy de acuerdo ✅"** (green) / NO **"NO — Mantener
  el esquema actual"** (amber).
- `_page_contingencia_success()` → SÍ "Está de acuerdo con la activación del plan
  bimodal — Google Classroom + Google Meet"; NO "Prefiere mantener el esquema actual y
  esperar nuevas disposiciones de las autoridades"; both note the 50%+1 condition.
- `_page_success_yes/_no` early-return to the contingencia page for this key.
- `_page_voting_closed()` → contingencia copy (deadline 01/07/2026).
- `_send_ack_confirmation()` → CC confirmation to `votacion@` (same inbox as
  budget/default), with a `[Contingencia Académica]` subject prefix for this key.

Budget, default-continuity, and the model's PDVSA auto-confirm logic are **untouched**.

### 3.2 Sender — `scripts/send_contingencia_vote_email.py`  (host-run HYBRID)
The Google Sheet needs google libs + creds (host only; **not** in the Odoo container), so:
- **Stage 1 (host):** reads the **Customers tab** of sheet
  `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA` — col C `Status=ACTIVE`, **col J `Email`**
  (the authoritative blast list), col B `Name`, col L `Phone`. (Sheet row 1 is a junk
  "Tasa BCV" row; the real header is row 2 — read `Customers!A2:M` then drop the first row.)
- **Stage 2 (container):** the script pipes itself into
  `docker exec <container> odoo shell -d <db>`, receives recipients via env
  `CONT_RECIPIENTS_JSON`, matches each email → `res.partner` (email index, name fallback),
  reuse-or-creates the ACK, and queues the `mail.mail`.
- **Idempotent:** skips already-voted (`state != pending`) and any address already in an
  outgoing/sent `mail.mail` with this subject.
- **TARGET_ENV** env var selects the target: default `testing` (`odoo-dev-web`/`testing`),
  `production` (`ueipab17`/`DB_UEIPAB`). A full prod `--live` send prompts `BLAST PROD`.
- **ACTIVE-only:** only col-C `Status == ACTIVE` rows are emailed; non-ACTIVE rows never
  enter the list. ACTIVE rows with no col-J email are logged (handle via WhatsApp).
- **`ENSURE_PARTNERS=true`** (opt-in, default off): auto-create a minimal `res.partner`
  for any ACTIVE col-J email that has no Odoo match, so every ACTIVE family gets a ballot.
  Run a DRY first to see the unmatched count before enabling (avoids duplicate partners).
- **Batched delivery:** all mails are created `outgoing` + committed first (a crash never
  loses them — Odoo's mail cron drains any remainder), then **sent in batches of
  `BATCH_SIZE` (default 10) with a `BATCH_PAUSE` (default 20s) gap and a fresh SMTP
  connection per batch** — mitigates Gmail rate-limit / idle-socket `SSLEOFError`. 169
  recipients → 17 batches (16×10 + 9), ~5m20s of spacing. Run the prod blast **detached**
  (`nohup … &`) so it drains in the background. Idempotent + resumable on re-run.

Modes (run on the host):
```bash
python3 scripts/send_contingencia_vote_email.py             # DRY (read sheet, match, no writes)
python3 scripts/send_contingencia_vote_email.py --test      # CEO preview (dry)
python3 scripts/send_contingencia_vote_email.py --test --live   # real CEO send (one email)
python3 scripts/send_contingencia_vote_email.py --live      # FULL send (sheet ACTIVE)
TARGET_ENV=production python3 scripts/send_contingencia_vote_email.py --test --live   # prod CEO preview
```

### 3.3 Service account — `scripts/wire_votacion_mailserver.py`
Idempotent, **testing-DB-guarded** odoo-shell script that creates a dedicated outgoing
`ir.mail_server` (`smtp.gmail.com:587` STARTTLS, `from_filter=votacion@`, sequence 5) so
only `From=votacion@` routes through the authenticated account. App password from env
`VOTACION_SMTP_PASS` only (never hardcoded); without it, `--live` skips server creation.
**Not run --live** — awaiting the Gmail app password. Until wired, `votacion@` sends via
the **default** mail server as a header (From/CC/Reply-To).

### 3.4 Prod deploy — `scripts/deploy_contingencia_survey_prod.sh`
Surgical: copies ONLY the survey files — `controllers/partner_ack.py`,
`wizard/vote_assist_wizard.py`, `views/vote_assist_wizard_views.xml`, `__manifest__.py`
— into the already-installed prod module (backs up each first), `-u`, restart, verify
version. Surgical (not whole-module) so unrelated dev working-tree changes (e.g.
`attendance_fix.py`) are not dragged into prod. Interactive `DEPLOY` confirmation.

### 3.5 WhatsApp — `scripts/send_contingencia_wa.py`
Reaches families over WhatsApp via Glenda's MassivaMóvil numbers, sending each a
**tokenized SÍ/NO link** that reuses the family's existing ballot — tapping records the
vote through the same controller (no email). Two modes:
- **Default send** (`--live`): the **9 ACTIVE no-email families** (all have phones), one
  ballot each. DRY is write-free; `--test` sends one WA to the CEO's phone.
- **Reminder** (`--remind`): targets **pending** voters (state='pending'), **reusing each
  ballot's existing token** (no new ballots). Splits across two numbers via
  `--account {backup,tertiary}` + `--shard A/B`, caps per run via `--cap N`, 120s anti-spam,
  per-account state files (idempotent), auto-stop after the window. **Freshness re-check**:
  re-reads each ballot's state right before sending and skips anyone who voted mid-wave.
- WA account status is live via `GET {api.base_url}/get/wa.accounts` (read-only). ⚠️ a
  reconnected number gets a **new `unique` id** — refresh `whatsapp_massiva.json` before
  sending from it.

### 3.6 Progress digest — `scripts/contingencia_survey_digest.py`
XML-RPC (prod) digest to the **school director + CEO**: delivery stats + SÍ/NO/pending
tally + 50%+1 progress bar; flags when the threshold is reached ("puede cerrarse con
aprobación de Dirección/CEO"). Params: `contingencia.digest_to` (CSV; default CEO),
`contingencia.plantilla_total` (50%+1 base; **set to 178** = full plantilla → threshold
**90 SÍ**). `--cron` sends only when the tally changed (state file) and auto-stops after
the window. Cron: `/etc/cron.d/contingencia_digest` every 20 min on the dev server.
(Recipients wired: `gustavo.perdomo@` + `arcides.arzola@`.)

### 3.7 "Voto Asistido" wizard labels (v1.6.31)
`wizard/vote_assist_wizard.py` — the assisted-vote decision radio uses **static** labels
**"SÍ — Estoy de acuerdo" / "NO — No estoy de acuerdo"** (stored values stay
`continuing`/`leaving`). ⚠️ **Lesson:** a context-aware `fields_get` override keyed on
`default_ack_id` (tried in v1.6.30) does **not** work in the real UI — Odoo's web client
strips `default_*` keys and caches view metadata on view load. Use **static** labels for
per-field display; hard-refresh (Ctrl+Shift+R) to clear the client view cache.

---

## 4. Survey copy (approved 2026-06-29)

**Subject:** Encuesta Institucional — Plan de Contingencia Académica (Modelo Bimodal)

> **Contexto y Justificación.** Respetando fielmente las directrices emitidas por las
> autoridades gubernamentales orientadas a salvaguardar la integridad de nuestra comunidad
> estudiantil, es de carácter prioritario mantener a los alumnos resguardados en sus hogares.
> Ante este escenario, la institución plantea el uso de medios tecnológicos como un canal
> seguro, eficiente y viable para evitar la interrupción del año escolar. A solicitud de
> diversos representantes, se evalúa la activación del Plan de Contingencia Académica bajo el
> modelo **bimodal**, utilizando exclusivamente **Google Classroom y Google Meet**.
> *(Nota: la medida se activará de inmediato únicamente al alcanzar el **50% + 1** del total
> de la plantilla.)*
>
> **Pregunta.** ¿Está usted de acuerdo con la activación del Plan de Contingencia Académica
> bajo el modelo bimodal (Google Classroom y Google Meet), como canal seguro de aprendizaje
> desde el hogar?
> - **SÍ ESTOY DE ACUERDO.** Autorizo la activación del plan bimodal y me comprometo a
>   implementar las herramientas tecnológicas institucionales.
> - **NO ESTOY DE ACUERDO.** Prefiero mantener el esquema actual y esperar nuevas
>   disposiciones de las autoridades.

---

## 5. Monitoring

**AI Agent → Operaciones → Comunicados a Representantes** (`partner.communication.ack`).
Search → **Agrupar por → Campaña**, expand `contingencia_academica_2026`. Group by
**Decisión** for the live tally. Read **Opción A = SÍ**, **Opción B = NO**, **Pendiente =
sin responder**. Per-family form shows channel, timestamp, response time, IP, audit notes,
and the assisted-vote (`📞 Registrar voto asistido`) + public-form buttons.

---

## 6. Testing verification (2026-06-29)

- Module upgraded to 17.0.1.6.29 + container restarted.
- Public pages curl-verified: SÍ → green "Estoy de acuerdo / Está de acuerdo con la
  activación del plan bimodal"; NO → amber "Mantener el esquema actual"; re-hit → "Ya
  respondiste"; landing + deadline gate OK.
- Sender DRY: **169 ACTIVE-with-email** (9 ACTIVE no-email → WA), **168 matched**, 1
  unmatched (testing data gap). `--test --live` queued+**sent** a real CEO email
  (`from=votacion@`, links `/si` `/no`, `cc=False` on test).
- Mail-server wiring DRY: testing-guarded, skips safely without the password.

---

## 7. Production deploy runbook

**A. Code (routes + pages):**
```bash
bash scripts/deploy_contingencia_survey_prod.sh        # type DEPLOY; verifies v17.0.1.6.29
```
Prod nginx already serves `/partner-ack/<token>` for the budget vote — no new route
whitelist needed.

**B. Service account `votacion@` (gated):**
1. Obtain the Gmail app password for `votacion@ueipab.edu.ve`.
2. Confirm **DMARC/SPF/DKIM** alignment for `votacion@` (⚠️ domain is `p=none` since
   2026-05-20 — see CLAUDE.md DMARC note). Do not external-blast until aligned.
3. (Optional) wire the dedicated server in prod (the wiring script is testing-locked by
   design; a prod variant/guard relaxation is a separate gated change). Until then,
   `votacion@` sends via the default server as a header.

**C. Blast (after A + B):**
```bash
TARGET_ENV=production python3 scripts/send_contingencia_vote_email.py --test --live   # CEO preview FIRST
TARGET_ENV=production python3 scripts/send_contingencia_vote_email.py --live          # full send (prompts BLAST PROD)
```
Run on a host with docker access to `ueipab17` **and** google libs + creds (the prod
host). If the prod host lacks google libs, read the sheet on dev and hand off the
recipients JSON.

**Rollback:** restore `…/ueipab17_addon_backups/contingencia-<TS>/*` + `docker restart ueipab17`.

---

## 8. Pre-blast checklist

- [x] A – module deployed to prod (now **v17.0.1.6.31**) + version verified
- [x] Recipient list reconciled vs Customers ACTIVE col J (house rule — the source)
- [x] Deadline (2026-07-01) confirmed
- [x] CEO preview reviewed in prod (`--test --live`) before full send
- [x] No-email ACTIVE families (9) handled via WhatsApp
- [ ] B – `votacion@` Gmail app password + DMARC/SPF/DKIM alignment (optional hardening;
      deliverability already proven via the default server, same as the budget vote)

---

## 9. Live operations log (2026-06-29)

All times VET. Survey fired same day as build.

1. **Prod deploy** v1.6.28→**1.6.29** (`deploy_contingencia_survey_prod.sh`); `/partner-ack`
   route smoke = HTTP 200.
2. **CEO email preview** in prod (`--test --live`) → `state=sent`, `from=votacion@`, `/si`
   `/no` links OK; preview ballot cleaned.
3. **Email blast** ~17:17 → **169/169 sent** (all `mail.mail` state=sent, 0 failed),
   background batches of 10 + 20s pause (17 batches). Prod DRY first: 169/169 matched, 0
   unmatched.
4. **WhatsApp to the 9 no-email families** → **9/9 sent** (msgId 87691–87699), from backup
   +584248944898, tokenized links.
5. **Digest** wired: params `plantilla_total=178` / `digest_to = gustavo.perdomo@ +
   arcides.arzola@`; cron every 20 min; first reports delivered to CEO + director.
6. **"Voto Asistido" wizard** fix: v1.6.30 (`fields_get` override — failed in UI) →
   **v1.6.31 static SÍ/NO** (works); deployed + verified in prod.
7. **WA reminder wave 1** (`--remind`, same-token): split **backup +584248944898 (shard
   0/2, 40)** + **tertiary +584148321963 (shard 1/2, 40)** = 80 messages, in parallel,
   freshness re-check on. (Primary +584148321989 reconnected per vendor — but its
   MassivaMóvil `unique` id changed; config refresh deferred, not used for this wave.)

**Ballot base:** 178 (169 email + 9 WA) = full plantilla; **threshold 90 SÍ**.

**Open / next:**
- Monitor via the digest; when **SÍ ≥ 90**, CEO/Dirección may close the survey (it also
  auto-closes after the Jul 1 deadline gate).
- WA reminder **wave 2** (~remaining pending) can run next day, capped, same two numbers.
- After the survey closes: remove `/etc/cron.d/contingencia_digest`.
- Optional: refresh `whatsapp_massiva.json` with the primary's new `unique` + restore it as
  Glenda's dedicated number (separate infra task).
- Optional: `votacion@` dedicated `ir.mail_server` + DMARC alignment.
