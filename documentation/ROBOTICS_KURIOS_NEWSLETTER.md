# Robotics Kurios Newsletter — Community Email Blast

**Created:** 2026-06-22 · **Status:** Preview sent / awaiting go-ahead for full blast
**Script:** `scripts/send_robotics_kurios_newsletter.py`

A celebratory HTML newsletter announcing the Instituto Privado "Andrés Bello"
gold-medal win (1st place, **Desafío #14**) at the **Torneo Regional de Robótica
Kurios — Zona Oriente**, held Saturday **20 June 2026** at **Colegio Integral
El Manglar** (Nueva Barcelona, Edo. Anzoátegui).

**Champions:** Isaac Carrillo · Jadasa Mayz · Andrés Córdoba

---

## Send parameters

| Field | Value |
|-------|-------|
| FROM | `Instituto Andrés Bello <soporte@ueipab.edu.ve>` |
| REPLY-TO | `soporte@ueipab.edu.ve` |
| SUBJECT | `¡EL ANDRÉS BELLO SE ADUEÑA DEL ORO EN EL REGIONAL DE ROBÓTICA KURIOS!🏅🤖` |
| Transport | `mail.mail` via XML-RPC (`state='outgoing'`) + trigger queue cron id=3 |
| Target DB | `DB_UEIPAB` (production) — config `config/production.json` |

**One email per address.** The community list is hard-coded in `RAW_RECIPIENTS`
(the raw blob supplied by the CEO). A regex flattens every `;`-joined row into
individual addresses, dedupes case-insensitively (order preserved), and sends
**one individual `mail.mail` per address** — no grouped `email_to`.

- **269** unique addresses parsed · **268** deliverable · **1** skipped
  (`olysamg@gmail.com` — known hard bounce since 2026-05-17, conv #44815).
- `todalacomunidad@ueipab.edu.ve` is included as the final recipient.

## Usage

```bash
# 1) Dry-run — parses + lists every recipient, sends nothing
python3 scripts/send_robotics_kurios_newsletter.py

# 2) Preview — sends ONE real email to the CEO for visual review
python3 scripts/send_robotics_kurios_newsletter.py --preview

# 3) Full blast — one individual email to all 268 deliverable addresses
python3 scripts/send_robotics_kurios_newsletter.py --live
```

---

## Media hosting

Images/videos are served by nginx from the existing flyers web root:

- **Disk:** `/var/www/dev/flyers/kurios/`
- **URL:**  `https://dev.ueipab.edu.ve/flyers/kurios/<file>`
- **Source:** `/home/ftpuser/odoo-dev/kuriospicsanz/` (copied 2026-06-22)
- nginx `location /flyers/` → `alias /var/www/dev/flyers/;` (already public, HTTP 200)

The school **logo** uses the canonical square asset
`https://odoo.ueipab.edu.ve/web/image/res.company/1/logo` (1080×1080 — renders
cleanly in the circular header frame).

### Media map (from CEO's `kuriospicsanz` folder)

| Slot | File(s) | Role in email |
|------|---------|---------------|
| Hero poster | `2.jpeg` | Official tournament poster (names the 3 champions, Desafío 14, El Manglar) |
| Results | `4.jpeg` | "Desafío 14 — Tabla de Posiciones Final": Andrés Bello 1º @ 03:49 |
| Podium | `5.jpeg` | Students with certificates on the El Manglar stage |
| Triumph collage | `1.jpeg` | "Kurios Robotics 2026 — moments of triumph and teamwork" |
| **Flagged video 1** | `3.mp4` (poster `8.jpeg`) | ⭐ DESTACADO — action on the field |
| **Flagged video 2** | `2-2.mp4` (poster `14.jpeg`) | ⭐ DESTACADO — moment of triumph |
| Photo album | `6,7,9,10,11,12,13,15,16,17,18,19,20,21.jpeg` | 2-column responsive grid, each clickable |
| Promo flyers | `a,b,c,d,e,f.jpeg` | Single row of 6 clickable thumbnails (offerings) |
| Unused | `g.mp4`, `h.jpeg` | Copied to host but not embedded (per scope: flyers a–f only) |

**Videos in email:** HTML email cannot embed `<video>` reliably, so each flagged
video renders as a clickable poster still (yellow border) + a "▶️ Reproducir video"
button, both linking to the hosted `.mp4`. Poster frames use landscape stills
(`8.jpeg`, `14.jpeg`) because no `ffmpeg` is available on the host to extract frames.

### Flyer legend (row of 6, a→f)
a = STEAM & Fútbol (Historia Copa Mundial) · b = Inscripciones 2026-2027 ·
c = Clases de Robótica (alianza Kurios) · d = Curso de Dibujo y Pintura ·
e = Bachillerato Virtual 100% online · f = Cursos de Inglés After School (MOA)

---

## Layout (top → bottom)

1. **Header** — square logo on navy→Kurios-blue gradient (`#1a1a6e → #2b6fd6`),
   yellow `#ffd400` badge "🏅🤖 ¡CAMPEONES REGIONALES DE ROBÓTICA KURIOS!"
2. **Hero poster** (`2.jpeg`, edge-to-edge)
3. **Headline** + dateline (El Tigre · Zona Oriente · sábado 20 de junio)
4. **Lead** — two paragraphs adapted from the press release
5. **Champions card** — yellow card: 3 names + "🥇 Medalla de Oro · 1er Lugar · Desafío #14"
6. **Results ranking** (`4.jpeg`)
7. **Featured videos** — two ⭐ DESTACADO video cards (`3.mp4`, `2-2.mp4`)
8. **Podium + collage** (`5.jpeg`, `1.jpeg`)
9. **Photo album** — 14-photo 2-column grid (6–21)
10. **Closing** congratulations
11. **Promo flyers row** — a–f thumbnails
12. **Footer** — navy bar with RIF J-08008617-1, IG, web, soporte@, phones

---

## Design notes / reuse

- Based on `scripts/send_english_guide_announcement_email.py` (most recent
  community blast with school logo + gradient header).
- Brand palette from the school's own flyers: navy `#1a1a6e`, Kurios blue
  `#2b6fd6`, accent yellow `#ffd400`, gold `#f0a500`.
- All `<img>` use inline width + `max-width` + `height:auto` for mobile reflow;
  album cells are `width:50%`, flyer cells `width:16%` (wrap on narrow clients).
- Spanish copy uses HTML entities (`&aacute;`, `&ntilde;`, …) for cross-client safety.

## Rebuild / preview locally

```python
# render HTML → /tmp/kurios_preview.html
python3 - <<'PY'
import importlib.util
s=importlib.util.spec_from_file_location("kn","scripts/send_robotics_kurios_newsletter.py")
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
open('/tmp/kurios_preview.html','w').write(m._build_html())
PY
# screenshot
google-chrome --headless --no-sandbox --window-size=620,4000 \
  --screenshot=/tmp/kurios_preview.png /tmp/kurios_preview.html
```

## Resilience features (added after first-run crash)

The blast runs ~65 min with 140 s idle gaps between batches. Two hardening
mechanisms were added after the first live attempt crashed:

1. **Auto-reconnect `call()`** — a single XML-RPC `ServerProxy` keeps one
   keep-alive socket, which `smtp.gmail.com`/Odoo's proxy **closes during the
   140 s sleep**. The next call then throws `ssl.SSLEOFError: EOF occurred in
   violation of protocol`. `call()` now retries up to 4× and rebuilds the
   connection on any `SSLError/socket.error/OSError/ProtocolError/Fault/EOFError`.
   In practice every batch boundary logs one `reconnecting…` warning then
   succeeds — **cosmetic, not a failure**. (Future polish: reconnect proactively
   at the top of each batch to suppress the warning entirely.)
2. **Crash-safe resume state** — every queued address is persisted to
   `STATE_FILE` (env `KURIOS_STATE`) immediately after send. On restart the
   script skips anything already recorded → **idempotent, zero double-sends**.
   To force a full re-send, delete the state file.

## Running on production (Option A — deployed)

Files live on prod host `10.124.0.3:/root/kurios/`:
- `send_robotics_kurios_newsletter.py`
- `kurios_prod_creds.json` — **xmlrpc block only** (url/db/user/api_key), chmod 600.
  *Not* the full production.json (no server root password). ⚠️ contains an API key.
- `kurios_sent_state.json` — resume ledger (286 addresses after the run).

Fire detached (survives SSH drop):
```bash
systemd-run --unit=kurios-blast --collect \
  --setenv=KURIOS_PROD_CFG=/root/kurios/kurios_prod_creds.json \
  --setenv=KURIOS_STATE=/root/kurios/kurios_sent_state.json \
  python3 /root/kurios/send_robotics_kurios_newsletter.py --live
journalctl -u kurios-blast -f       # live progress: "◆ Batch N/NN released"
```

Prod facts (verified read-only 2026-06-22): host `python3 3.12.3`; Odoo container
`ueipab17`; outgoing mail server = **`smtp.gmail.com:587` STARTTLS** auth
`soporte@ueipab.edu.ve` (Workspace ~2,000 ext. recipients/day — 286 is safe);
mail-queue cron id=3 runs **hourly**, so the per-batch `method_direct_trigger`
is what releases each batch immediately.

## Pending enhancements

- **⏳ Mid-run progress check (PENDING)** — today progress is only visible via
  `journalctl -u kurios-blast -f` on the prod host. Add a lightweight way to
  query progress mid-run without SSH/journal: e.g. have the script write a
  `kurios_progress.json` (batch N/total, sent count, last address, ETA) after
  each batch, plus a `--status` mode that prints it. Lets the operator (or a
  monitor) poll a single file instead of parsing logs.
- **Proactive reconnect** — rebuild the XML-RPC connection at the top of each
  batch (instead of catching the SSL EOF on the first call) to suppress the
  cosmetic `reconnecting…` warning at every boundary. Functionally irrelevant.

## Desafío 12 correction edition (2026-06-22)

After the first blast, the **Desafío 12** team (Fabriccio Figueroa · Mariana
Farías · Luis Goite) was found to have been **involuntarily omitted** and a
claim was raised to the event judges. Correction handled by a second script
`scripts/send_robotics_kurios_d12_correction.py` (forked from this one):

- **Approach A (integrated):** full newsletter + a D12 recognition block placed
  right after the Desafío 14 ranking — sincere omission acknowledgment card →
  D12 poster (`desafio12.jpg`) → names card → dedicated 5-photo gallery
  (`missing-desafio12-album1..5.jpeg`). No invented medal — celebrates their
  "destacada participación".
- **Subject:** `¡Debut de oro! El Andrés Bello brilla con los Desafíos 12 y 14 en Robótica 🏆`
- **Recipients (5, each individual):** 4 D12 families
  (`luis.goite@`, `velamaria.pqt@`, `maderamariana@`, `figueroays@`) +
  **`todalacomunidad@ueipab.edu.ve`** → intentional **full-community re-send** of
  the corrected edition.
- **`--live` guard:** refuses to send when the recipient list is empty.
- State file `/root/kurios/kurios_d12_state.json` (separate from the first run).
- **Sent 2026-06-22 from prod** (`systemd-run --unit=kurios-d12`): 5/5,
  `Result=success`, zero failures.

## All-teams recap edition (2026-06-22)

A third edition celebrating **every** competition team (not just the Desafío 14
champions). Script `scripts/send_robotics_kurios_recap.py` (forked from the
original), same prod/batching/resilience infra.

- **Subject:** `Orgullo tigrense: nuestros 7 equipos en el Regional de Robótica Kurios 🤖💙`
- **Structure:** header → hero (`2.jpeg`) → "¡Felicitaciones a TODOS nuestros
  equipos!" headline + reframed lead (7 teams; gold in D14; pride for all) →
  **D14 gold champions card** → **all-teams gallery** (one full-width poster +
  name caption per team) → collage (`1.jpeg`) → closing → flyers → footer.
- **Deliberately removed** (redundant with the first blast to the same audience):
  the Desafío 14 ranking image and the two "Revive los momentos en video" blocks.
- **Teams featured (7 / 19 students), no invented placements:**
  | Poster | Team | Students |
  |--------|------|----------|
  | `2.jpeg` | Desafío 14 🥇 ORO | Isaac Carrillo · Jadasa Mayz · Andrés Córdoba |
  | `desafio3.jpg` | Desafío 3 | Rael Tenorio · Athena Cruz |
  | `desafio4.jpg` | Desafío 4 | Lucía Pereira · Saileh Muñoz · Miranda Cuellar |
  | `desafio5.jpg` | Desafío 5 | Lucía González · Héctor Calles · Alexandra Sánchez |
  | `desafio7a.jpg` | Desafío 7 (A) | Santiago Martínez · Pedro Chanchamire · Álvaro Laya |
  | `desafio12.jpg` | Desafío 12 | Fabriccio Figueroa · Mariana Farías · Luis Goite |
  | `desafio-unidad111r.jpg` | Unidad 111 R | Sabrina Torres · Sebastián Delgado · Ariela Figueroa |
- **Recipients:** community list + `todalacomunidad@` → **270 parsed / 269
  deliverable** (`olysamg@` bounce skipped). One individual email each.
- **State file:** `/root/kurios/kurios_recap_state.json`.
- **Status: SENT 2026-06-22** from prod (`systemd-run --unit=kurios-recap`):
  **269/269 sent, 0 failures** (`exception` flat at 232 baseline), 27 batches,
  `Result=success`. `todalacomunidad@` released in batch 1 (full-community
  fan-out). Fire command used:
  ```bash
  systemd-run --unit=kurios-recap --collect \
    --setenv=KURIOS_PROD_CFG=/root/kurios/kurios_prod_creds.json \
    --setenv=KURIOS_STATE=/root/kurios/kurios_recap_state.json \
    python3 /root/kurios/send_robotics_kurios_recap.py --live
  ```

## Log

- **2026-06-22** — Built script + media hosting; dry-run 268→286 deliverable
  (after partner list added); previews to `gustavo.perdomo@` (ids 8002, 8005).
- **2026-06-22 ~12:50 VET** — First `--live` on prod (Option A, systemd).
  **Crashed after batch 1** (10 sent) on `ssl.SSLEOFError` at the batch-2
  boundary — single connection went stale over the 140 s sleep, no retry.
- **2026-06-22 ~12:57 VET** — Added auto-reconnect + resume state; seeded state
  with the 10 already-sent; **relaunched and completed at 14:09 VET**.
  Final: **286/286 sent, 0 failures** (`exception` flat at 232 baseline),
  10 resumed, 1 bounce skipped. systemd `Result=success`.
