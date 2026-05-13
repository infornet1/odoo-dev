# Freescout API Migration Plan

**Status:** Phases 2+3 Complete (2026-05-13) — Phase 1, 4, 5 pending
**Created:** 2026-02-09
**Priority:** Medium

## Background

All Freescout integrations currently use **direct MySQL** (`pymysql`) to read and write data. This bypasses Freescout's Laravel ORM, causing recurring bugs:

| Bug | Root Cause | Date Fixed |
|-----|-----------|------------|
| Conversations in wrong folder | `folder_id` set to wrong type constant | 2026-02-09 |
| Closed conversations not visible in UI | `closed_at` / `closed_by_user_id` not set | 2026-02-09 |
| `user_updated_at` not set | ORM normally handles this on save | 2026-02-09 |

Freescout offers a REST API via the **API & Webhooks Module** that handles these automatically through the ORM.

## Module

- **Module:** API & Webhooks — **installed and active (2026-05-13)**
- **License:** One-time lifetime (AGPL-3.0)
- **API Reference:** https://api-docs.freescout.net/
- **Auth:** `X-FreeScout-API-Key` header
- **Config:** `/opt/odoo-dev/config/freescout_api.json` (gitignored) — `api_url`, `api_key`, `webhook_secret`

## API Behaviour (discovered 2026-05-13)

| Aspect | Behaviour |
|--------|-----------|
| Conversation ID in URL | DB primary key (`conversations.id`) — NOT display number |
| `GET /api/conversations/{id}` | Returns status as string `"active"` / `"closed"` |
| `PUT /api/conversations/{id}` — status | Must be string (`"active"`, `"closed"`); `byUser` (int user ID) **required** alongside any status change |
| `PUT /api/conversations/{id}` — assignTo | Integer user ID — works, auto-moves to Assigned folder |
| `PUT /api/conversations/{id}` — customerId | Integer customer ID — accepted, not yet confirmed to update `customer_email` |
| `POST /api/conversations/{id}/threads` — note | `type: "note"`, `text: "<html>"`, `user: <int>` — `user` is **required** (not `userId`) |
| Folder assignment | Handled automatically by API — no `folder_id` needed |
| `closed_at` / `closed_by_user_id` | Set automatically on `status=closed` |
| `user_updated_at` | Updated automatically on any PUT |
| Success codes | PUT → 204, POST thread → 201 |

## Migration Strategy: Hybrid

**Migrate writes to API, keep SQL for reads that the API cannot handle.**

### Phase 1 — Escalation Bridge *(Pending)*

**Script:** `scripts/ai_agent_escalation_bridge.py`

Already migrated to email-only (2026-02-19) — no Freescout SQL. Full API migration deferred.

### Phase 2 — Resolution Bridge ✅ Complete (2026-05-13)

**Script:** `scripts/ai_agent_resolution_bridge.py`

| Operation | Before | After |
|-----------|--------|-------|
| Update subject + status + assignTo | SQL `UPDATE conversations` | `PUT /api/conversations/{id}` |
| Add internal note | SQL `INSERT INTO threads` + `UPDATE threads_count` | `POST /api/conversations/{id}/threads` |
| Customer reassignment (mailer-daemon) | Separate SQL pre-step | Folded into API payload as `customerId` |
| Folder assignment | Manual `get_freescout_folder()` SQL lookup | Auto-managed by API |
| Get conversation (subject check, mailbox_id) | SQL `SELECT` | **Kept SQL** (read-only, no API advantage) |
| Find customer by email | SQL join on `emails` + `customers` | **Kept SQL** (no API equivalent) |
| `close_related_conversations()` — search + close | SQL thread body search | **Kept SQL** (thread body search has no API equivalent) |

**Helper functions added to script:**
- `_get_fs_api_cfg()` — lazy-loads `freescout_api.json`
- `_fs_api_headers()` — returns auth header dict
- `fs_api_update_conversation(conv_db_id, payload, by_user_id=1)` — PUT wrapper, normalizes status to string, injects `byUser`
- `fs_api_add_note(conv_db_id, html_body, user_id=1)` — POST thread wrapper

### Phase 3 — Email Checker ✅ Complete (2026-05-13)

**Scripts:** `scripts/ai_agent_email_checker.py` + `scripts/ai_agent_hr_email_checker.py`

| Operation | Before | After |
|-----------|--------|-------|
| Update subject + close conversation | SQL `UPDATE conversations` | `PUT /api/conversations/{id}` |
| Add internal note | SQL `INSERT INTO threads` + `UPDATE threads_count` | `POST /api/conversations/{id}/threads` |
| Search threads for replies / attachments | SQL `SELECT` on `threads.from` / `attachments` | **Kept SQL** (no API equivalent) |
| Read current subject (idempotency guard) | SQL `SELECT subject` | **Kept SQL** (already connected for reads) |

### Phase 4 — Bounce Processor *(Pending)*

**Script:** `scripts/daily_bounce_processor.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Scan conversations/threads for bounce patterns | **No API equivalent** (thread body search) | **Keep SQL** |
| Update subject prefix | `PUT /api/conversations/{id}` | Yes |
| Add internal note | `POST /api/conversations/{id}/threads` | Yes |

### Phase 5 — WA Health Monitor *(Evaluate)*

**Script:** `scripts/ai_agent_wa_health_monitor.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Search by subject LIKE unlink notification | `GET /api/conversations?subject=...` | Test — unclear if API does partial match |

## API Limitations (hard blockers for full migration)

1. **No thread body search** — `GET /api/conversations` filters by `customerEmail`, `subject`, `tag`, `status`, but NOT by thread content. `close_related_conversations()` and email verification detection must stay SQL.

2. **`customer_email` not confirmed** — API accepts `customerId` on PUT but it's unconfirmed whether `customer_email` column updates automatically. Behaviour needs live verification.

## Shared connection pattern

Scripts use both connections:

```python
# API for writes (proper ORM handling)
import requests
# helpers: fs_api_update_conversation(), fs_api_add_note()

# SQL for reads that API can't do (thread body search)
import pymysql
fs_conn = pymysql.connect(...)
```
