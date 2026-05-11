# PDVSA Campaign — Production Deploy & Bulk Send (Friday 15-May-2026)

**Status:** PENDING
**Target date:** Friday 2026-05-15, ~9:00 AM VET (13:00 UTC)
**Owner:** Gustavo Perdomo

---

## Quick-reference facts

| Item | Value |
|---|---|
| Module to deploy | `ueipab_attendance_report` |
| Testing version (current) | 17.0.1.5.2 |
| Target version | 17.0.1.6.0 |
| Production server | `10.124.0.3` |
| Container | `0ef7d03db702_ueipab17` |
| Production DB | `DB_UEIPAB` |
| Module path (host) | `/home/vision/ueipab17/addons` |
| PDVSA tag id (prod) | **26** (confirmed — same as testing) |
| Partners to email | **71** (with email, active, PDVSA tag) |
| Test partner (prod) | id=**7** — Gustavo Perdomo `<gustavo.perdomo@ueipab.edu.ve>` |
| Deadline communicated | Monday 08-Jun-2026, 12:30 p.m. |

---

## Pre-flight checklist (day before or morning of)

- [ ] Confirm `ueipab_attendance_report` v17.0.1.6.0 is committed and clean on `main`
- [ ] `partner.communication.ack` model NOT yet in production — deploy will create it
- [ ] Backup production DB before any module upgrade
- [ ] Confirm `votacion@ueipab.edu.ve` mailbox is monitored (will receive 71 CC emails)
- [ ] Confirm Google Doc is publicly readable:
      `https://docs.google.com/document/d/1z9_Dr3qvWdytEcrDUCp7NcVoJQHq4MKiveNoV_kC2jE/edit?tab=t.0`

---

## Step 1 — Backup production database

```bash
ssh root@10.124.0.3 \
  "docker exec 0ef7d03db702_ueipab17 bash -c \
   'pg_dump -h postgres -U odoo DB_UEIPAB | gzip > /var/lib/odoo/DB_UEIPAB_pre_pdvsa_20260515.sql.gz' \
   && echo BACKUP_OK"
```

---

## Step 2 — Copy module to production

```bash
# Tarball on dev server
cd /opt/odoo-dev/addons
tar -czf /tmp/ueipab_attendance_report.tar.gz ueipab_attendance_report/

# Ship to production
scp /tmp/ueipab_attendance_report.tar.gz root@10.124.0.3:/tmp/

# Swap on production host
ssh root@10.124.0.3 "
  cd /home/vision/ueipab17/addons
  mv ueipab_attendance_report ueipab_attendance_report.backup_20260515
  tar -xzf /tmp/ueipab_attendance_report.tar.gz
  echo COPY_OK
"
```

---

## Step 3 — Upgrade module (creates partner_communication_ack table)

```bash
ssh root@10.124.0.3 \
  "docker exec 0ef7d03db702_ueipab17 /usr/bin/odoo \
   -d DB_UEIPAB -u ueipab_attendance_report \
   --stop-after-init --http-port=18069 2>&1 | tail -5"
```

Expected last line: `Stopping gracefully` (no ERROR lines).

```bash
# Restart to load new controllers
ssh root@10.124.0.3 "docker restart 0ef7d03db702_ueipab17 && echo RESTARTED"
# Wait ~20 s then check
sleep 20 && curl -s -o /dev/null -w "%{http_code}" https://odoo.ueipab.edu.ve/web/health
# Expect: 200
```

---

## Step 4 — Update production nginx

On the production server (`10.124.0.3`), find the Odoo proxy location regex and add `partner-ack`:

```bash
ssh root@10.124.0.3 "grep -n 'notice-ack\|location ~' /etc/nginx/sites-enabled/odoo.ueipab.edu.ve"
```

Edit the matching line — add `|partner-ack` after `notice-ack`:

```
# Before
location ~ ^/(web|...|notice-ack|employee-info)(/|$) {

# After
location ~ ^/(web|...|notice-ack|glenda-calibracion|employee-info|partner-ack)(/|$) {
```

```bash
ssh root@10.124.0.3 "nginx -t && nginx -s reload && echo NGINX_OK"
```

### Smoke-test the route

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "https://odoo.ueipab.edu.ve/partner-ack/00000000-0000-0000-0000-000000000000"
# Expect: 200 (shows "Enlace no válido" page — proves route hits Odoo)
```

---

## Step 5 — Dry run (confirm 71 partners found)

Run from dev server — pipes script stdin into prod container via SSH:

```bash
{ cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } | \
  ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http" \
  2>&1 | grep -v "^20[0-9][0-9]-\|WARNING\|DEBUG"
```

Expected output:
```
COMUNICADO PDVSA 2026-2027 — *** DRY RUN ***
Tag: id=26 'Representante PDVSA'
Found 71 partners with tag 'Representante PDVSA' and email
...
  [DRY] NOMBRE APELLIDO → email@domain.com
...
DRY RUN — no se crearon registros ni se enviaron correos
```

---

## Step 6 — Test send (Gustavo only)

Partner id=7 in production → `gustavo.perdomo@ueipab.edu.ve`.

```bash
{ echo "import os; os.environ['LIVE']='true'; os.environ['PARTNER_ID']='7'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } | \
  ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http" \
  2>&1 | grep -v "^20[0-9][0-9]-\|WARNING\|DEBUG"
```

Expected: `ack_id=N  mail_id=N`

Force-send immediately (Odoo mail queue may take minutes):

```bash
# Replace MAIL_ID with the id printed above
{ echo "env['mail.mail'].browse(MAIL_ID).send(); env.cr.commit(); print('sent')"; } | \
  ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http" \
  2>&1 | grep -v "^20[0-9][0-9]-\|WARNING\|DEBUG"
```

**Verify before proceeding:**
- [ ] Email received at `gustavo.perdomo@ueipab.edu.ve`
- [ ] `votacion@ueipab.edu.ve` received CC copy
- [ ] "Ver comunicado completo" link opens Google Doc
- [ ] "Sí, continuaré" link opens `https://odoo.ueipab.edu.ve/partner-ack/<token>/si` → success page
- [ ] "No continuaré" link opens `/no` → correct page
- [ ] ACK confirmation email arrives at `gustavo.perdomo@ueipab.edu.ve` + CC `votacion@`
- [ ] Decision recorded in Odoo: Payroll → Reports → Comunicados a Representantes

---

## Step 7 — Full blast (71 partners, ~9:00 AM VET)

Only proceed after Step 6 passes all checks.

```bash
{ echo "import os; os.environ['LIVE']='true'"; \
  cat /opt/odoo-dev/scripts/send_pdvsa_communication.py; } | \
  ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http" \
  2>&1 | grep -v "^20[0-9][0-9]-\|WARNING\|DEBUG"
```

Expected summary:
```
Enviados  : 71   (or 70 if Gustavo already sent in Step 6 — idempotent)
Omitidos  : 1    (Gustavo skipped — already has a record)
Errores   : 0
```

Script is **idempotent** — re-running skips any partner who already received the email.

---

## Step 8 — Post-send verification

```bash
# Check record count in production DB
{ echo "
acks = env['partner.communication.ack'].search([('notice_key','=','pdvsa_continuacion_2026_2027')])
by_state = {}
for a in acks:
    by_state[a.state] = by_state.get(a.state, 0) + 1
print('Total sent:', len(acks))
print('By state:', by_state)
"; } | ssh root@10.124.0.3 \
  "docker exec -i 0ef7d03db702_ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http" \
  2>&1 | grep -v "^20[0-9][0-9]-\|WARNING\|DEBUG"
```

Expected: `Total sent: 71`, `By state: {'pending': 71}` (responses arrive over following days).

---

## Rollback plan

If the module upgrade fails or causes issues:

```bash
ssh root@10.124.0.3 "
  cd /home/vision/ueipab17/addons
  rm -rf ueipab_attendance_report
  mv ueipab_attendance_report.backup_20260515 ueipab_attendance_report
  docker restart 0ef7d03db702_ueipab17
"
```

The `partner_communication_ack` table will remain in the DB but the module that uses it will be gone — no visible impact on users. If needed, drop it manually:

```bash
ssh root@10.124.0.3 \
  "docker exec 0ef7d03db702_ueipab17 psql -h postgres -U odoo -d DB_UEIPAB \
   -c 'DROP TABLE IF EXISTS partner_communication_ack;'"
```

---

## After Friday — monitor responses

HR tracking view: **Odoo Production → Payroll → Reports → Comunicados a Representantes**

Filter by `Pendientes` to see who hasn't responded as the June 8 deadline approaches.

Next action: **WA reminder blast** (Capability 2) — run June 3–5 for pending partners.
See [PDVSA_CONTINUITY_CAMPAIGN.md](PDVSA_CONTINUITY_CAMPAIGN.md) for that script spec.
