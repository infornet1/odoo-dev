# Attendance — Dangling Open Records (kiosk) Issue & Fix

**Date:** 2026-06-29 · **Env:** production (`DB_UEIPAB` / `odoo.ueipab.edu.ve`) · **Trigger:** review of the company kiosk for empl. **Josefina Rodríguez (emp #590)**
**Kiosk URL:** `https://odoo.ueipab.edu.ve/hr_attendance/b93082d2-62ea-45d5-bfee-eee86f1dc9bc` → that token is **Company 1's `attendance_kiosk_key`** (the shared company kiosk, not employee-specific). The kiosk page is healthy (**HTTP 200**).

---

## 1. Symptoms

- **Josefina (emp #590):** a dangling attendance row **#7950 — check_in `2026-06-02 11:00:00`, check_out = NULL**, `worked_hours = 0`, and **every audit field NULL** (`create_date`, `write_date`, `create_uid`, `in_mode`, `in_ip_address`). State shows `checked_out` only because a *later* closed row is her `last_attendance_id`.
- **Company-wide:** 28 rows had `check_out = NULL`. ~20 were **today's** still-at-work sessions (normal). **9 were stale** (prior-day dangling):
  - **3 null-audit "ghost" rows** (raw-SQL inserts, no check_out): #7950 Josefina (Jun-2), #8013 David Hernández (Jun-24), #7987 Gabriel España (Jun-24) — all at the round `11:00:00` UTC = 07:00 VET.
  - **6 genuine kiosk arrivals never checked out** (real `create_date`/`in_mode=kiosk`): #38 Administrador 3Dv (Oct-2025), #413 maria.morales, #746 Yosmari González, #2674 Abrahima Martínez, #4362 Gustavo Perdomo (Mar-2), #7823 Andrés Morales (Jun-19).
- **Server log noise (separate issue):** recurring `ERROR … odoo.sql_db: bad query: UPDATE "hr_attendance" SET "check_out"=…` from **three workers at the same millisecond** for the same id → PostgreSQL **`could not serialize access due to concurrent update`**. Cause = kiosk **check-out double/triple-submit** (and the `last_attendance_id` compute racing). Non-fatal (Odoo retries), but noisy.

## 2. Root cause

- **Null-audit ghost rows** come from a **raw-SQL `INSERT` that omitted `check_out`** and bypassed the ORM (hence NULL `create_date`). The current `sync_control_asistencia.py` always sets `check_out` (13:30 VET) and uses the ORM on prod, so the live rows are from an **older/manual backfill** modelled on it — but the raw-SQL path was the latent hazard.
- **Genuine dangling rows** are ordinary "forgot to check out" sessions that the same-day evening WiFi auto-fill (`attendance_daily_alert.py`) didn't catch (inserted after the run, or no WiFi match), with **no prior-day safety net** to close them.
- **Serialization errors** are a frontend double-submit on the Odoo kiosk check-out button.

## 3. Fix — cleanup (one-off)

The sweep script below (run `--live`) closes all 9 stale rows: each gets `check_out = check_in + 60s` → `worked_hours ≈ 0`, a deliberately obvious **"needs-review"** signature RRHH can correct. (Non-destructive — no deletes; reversible by reopening.) Today's sessions are never touched.

> ✅ **Applied 2026-06-29:** `python3 scripts/attendance_close_stale_open.py --env production --live` → **9 rows closed, 0 failed, 0 stale-open remaining**. (Re-runnable / idempotent.)

## 4. Fix — prevention (recurrence)

1. **Nightly safety-net sweep** — `scripts/attendance_close_stale_open.py` closes any prior-day dangling open row regardless of how it was created. Install:
   ```
   # /etc/cron.d/attendance_close_stale_open  (03:45 UTC = 23:45 VET, after the evening alert)
   45 3 * * *  root  /usr/bin/python3 /opt/odoo-dev/scripts/attendance_close_stale_open.py --live --env production >> /var/log/attendance_close_stale_open.log 2>&1
   ```
2. **Hardened raw-SQL path** — `sync_control_asistencia.py` `PsycopgBackend.create_attendance()` now (a) **refuses to insert a NULL check_out**, and (b) **stamps `create_uid/write_uid/create_date/write_date`** so no future row is a null-audit ghost.
3. **Kiosk double-submit guard** — ✅ built + tested in `testing`, ⏳ pending prod deploy. Root cause: the public kiosk guards the **barcode** path (`lockScanner` + `ui.block`) but **not the manual** path — `onManualSelection` → `makeRpcWithGeolocation` awaits a slow `getCurrentPosition(enableHighAccuracy)` **without blocking the UI**, so users tap again → 2–3 concurrent `manual_selection` RPCs → concurrent check-out UPDATEs → `could not serialize access`. Fix: `ueipab_attendance_report/static/src/js/kiosk_double_submit_guard.js` (v17.0.1.6.28) `patch()`es `kioskAttendanceApp.prototype` to add a re-entrancy lock + `ui.block()` around `onManualSelection`/`kioskConfirm` (no core edits; into bundle `hr_attendance.assets_public_attendance`). Verified in testing: module installed 17.0.1.6.28, kiosk renders HTTP 200, guard present in the compiled bundle. **Prod deploy** (gated — kiosk is prod-critical): scp `ueipab_attendance_report` → `docker exec ueipab17 odoo -u ueipab_attendance_report -d DB_UEIPAB --stop-after-init` → restart → verify kiosk 200 + guard in bundle.

## 5. Status

| Item | Status |
|------|--------|
| Sweep/cleanup script `attendance_close_stale_open.py` | ✅ created (committed) |
| `sync_control_asistencia.py` raw-SQL hardening | ✅ done (committed) |
| Production cleanup of the 9 stale rows | ✅ **applied 2026-06-29 — 9 closed, 0 remaining** |
| `/etc/cron.d/attendance_close_stale_open` nightly guard | ✅ **installed on the cron host (dev), cron active** |
| Kiosk check-out double-submit guard | ✅ **DEPLOYED to prod 2026-06-29** (v17.0.1.6.28; verified: kiosk HTTP 200 + guard in prod bundle). Also brought the lagging prod attendance 1.6.25→1.6.28 (incl. 1.6.27 hr.leave CC fix). |

**Related:** [ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md](ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) (daily alert / WiFi auto-fill) · [CONTROL_ASISTENCIA_BRIDGE.md](CONTROL_ASISTENCIA_BRIDGE.md) · Josefina context: `project_josefina_overpayment` memory.
