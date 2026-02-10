# Freescout API Migration Plan

**Status:** Pending
**Created:** 2026-02-09
**Priority:** Medium

## Background

All Freescout integrations currently use **direct MySQL** (`pymysql`) to read and write data. This bypasses Freescout's Laravel ORM, causing recurring bugs:

| Bug | Root Cause | Date Fixed |
|-----|-----------|------------|
| Conversations in wrong folder | `folder_id` set to wrong type constant | 2026-02-09 |
| Closed conversations not visible in UI | `closed_at` / `closed_by_user_id` not set | 2026-02-09 |
| `user_updated_at` not set | ORM normally handles this on save | 2026-02-09 |

Freescout offers a REST API via the **API & Webhooks Module** that would handle these automatically through the ORM.

## Purchase Required

- **Module:** [API & Webhooks](https://freescout.net/module/api-webhooks/)
- **License:** One-time lifetime (AGPL-3.0)
- **Requirement:** Freescout >= 1.8.198, PHP `hash` extension
- **API Reference:** https://api-docs.freescout.net/
- **Auth:** API key (GET param, Basic Auth, or `X-FreeScout-API-Key` header)

## Migration Strategy: Hybrid

**Migrate writes to API, keep SQL for reads that the API cannot handle.**

### Phase 1 — Escalation Bridge (cleanest candidate)

**Script:** `scripts/ai_agent_escalation_bridge.py`

All operations have API equivalents:

| Current SQL | API Replacement |
|-------------|----------------|
| `SELECT MAX(number)+1` for new conv number | Not needed — API auto-assigns |
| `INSERT INTO customers` | `POST /api/customers` |
| `INSERT INTO conversations` (5+ fields manually) | `POST /api/conversations` (atomic with first thread) |
| `INSERT INTO threads` (customer msg + note) | Included in conversation create + `POST /api/conversations/{id}/threads` |
| `SELECT id FROM conversations WHERE number = %s` | `GET /api/conversations?number=...` |

**Benefits:** Eliminates race condition on `MAX(number)+1`, atomic conversation+thread creation, proper folder assignment.

### Phase 2 — Resolution Bridge (partial)

**Script:** `scripts/ai_agent_resolution_bridge.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Get conversation by ID | `GET /api/conversations/{id}` | Yes |
| Update subject + status + assignTo | `PUT /api/conversations/{id}` | Yes |
| Add internal note | `POST /api/conversations/{id}/threads` type=note | Yes |
| Close conversation (status + folder + closed_at) | `PUT /api/conversations/{id}` status=closed, byUser=id | Yes |
| Update customer_id + customer_email | `PUT /api/conversations/{id}` customerId=N | Yes (test first) |
| Search `threads.body LIKE '%email%'` | **No API equivalent** | **Keep SQL** |
| Get folder by type | `GET /api/mailboxes/{id}/folders` | Yes |

**Note:** The `close_related_conversations()` function must stay as SQL because it searches thread body content across all active conversations. No API endpoint supports full-text thread search.

### Phase 3 — Email Checker (partial)

**Script:** `scripts/ai_agent_email_checker.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Search threads for verification email replies | **No API equivalent** | **Keep SQL** |
| Update subject prefix | `PUT /api/conversations/{id}` | Yes |
| Close conversation | `PUT /api/conversations/{id}` | Yes |
| Add internal note | `POST /api/conversations/{id}/threads` | Yes |

### Phase 4 — Bounce Processor (partial)

**Script:** `scripts/daily_bounce_processor.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Scan conversations/threads for bounce patterns | **No API equivalent** (thread body search) | **Keep SQL** |
| Update subject prefix | `PUT /api/conversations/{id}` | Yes |
| Add internal note | `POST /api/conversations/{id}/threads` | Yes |

### Phase 5 — WA Health Monitor (evaluate)

**Script:** `scripts/ai_agent_wa_health_monitor.py`

| Current SQL | API Replacement | Migrate? |
|-------------|----------------|----------|
| Search by subject LIKE unlink notification | `GET /api/conversations?subject=...` | Test — unclear if API does partial match |

## API Limitations (hard blockers for full migration)

1. **No thread body search** — `GET /api/conversations` filters by `customerEmail`, `subject`, `tag`, `status`, but NOT by thread content. Our related conversation cleanup and email verification detection depend on `threads.body LIKE '%email%'`.

2. **No `customer_email` direct field** — API accepts `customerId` on conversation update. Need to verify it auto-updates `customer_email` (not documented explicitly).

3. **Conversation ID vs number** — API uses conversation `number` (display). Our Odoo `freescout_conversation_id` stores the DB `id` (primary key). Options: change Odoo field to store number, or look up number from id first.

## Implementation Notes

### Shared connection pattern

After migration, scripts will use both connections:

```python
# API for writes (proper ORM handling)
import requests
FS_API_URL = 'https://soporte.ueipab.edu.ve/api'
FS_API_KEY = '...'  # from config file
headers = {'X-FreeScout-API-Key': FS_API_KEY}

# SQL for reads that API can't do (thread body search)
import pymysql
fs_conn = pymysql.connect(...)
```

### Config addition needed

Add to `/opt/odoo-dev/config/freescout_api.json` (gitignored):
```json
{
    "api_url": "https://soporte.ueipab.edu.ve/api",
    "api_key": "GENERATED_AFTER_MODULE_INSTALL"
}
```

## Steps to Start

1. Purchase API & Webhooks module from freescout.net
2. Install module in Freescout (Manage > Modules)
3. Generate API key (Manage > API & Webhooks)
4. Add key to config file
5. Start with Phase 1 (escalation bridge) — smallest scope, full API coverage
6. Test `customerId` update on conversation via API before Phase 2
