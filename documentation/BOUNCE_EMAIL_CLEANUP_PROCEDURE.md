# Bounce Email Cleanup Procedure

**Created:** 2026-05-21  
**Author:** Gustavo Perdomo / Claude Code  
**Applies to:** Campaign emails sent from `votacion@ueipab.edu.ve`, `soporte@ueipab.edu.ve`, and any bulk send that routes replies to Freescout.

---

## Overview

When bulk emails are sent to representantes (budget vote, PDVSA continuity, attendance reports, etc.), delivery failures land as **Delivery Status Notification (DSN)** conversations in the Freescout `soporte@` inbox (mailbox_id=3). These must be periodically cleaned to:

1. Remove dead emails from Odoo contacts and the Customers Google Sheet
2. Log the bounced addresses for CS follow-up
3. Clear the Freescout inbox of DSN noise

---

## Trigger

Run this procedure after any bulk email campaign, or whenever the `soporte@` Freescout inbox accumulates DSN conversations.

---

## Step 1 — Identify Bounced Emails via Freescout API

Fetch all active DSN conversations from `soporte@` (mailbox_id=3):

```python
import json, requests, re

cfg = json.load(open('/opt/odoo-dev/config/freescout_api.json'))
headers = {'X-FreeScout-API-Key': cfg['api_key']}
base = cfg['api_url']

all_dsn = []
for status in ['active', 'closed']:
    for page in range(1, 10):
        resp = requests.get(f'{base}/conversations', headers=headers, params={
            'mailboxId': 3, 'status': status, 'page': page})
        convs = resp.json().get('_embedded', {}).get('conversations', [])
        if not convs:
            break
        for c in convs:
            subj = (c.get('subject') or '').lower()
            if any(k in subj for k in ['delivery', 'bounce', 'failure', 'undeliver']):
                all_dsn.append({'id': c['id'], 'subject': c.get('subject', ''), 'status': status})
```

For each DSN conversation extract the bounced email from the thread body:

```python
for c in all_dsn:
    r = requests.get(f'{base}/conversations/{c["id"]}', headers=headers, params={'embed': 'threads'})
    threads = (r.json().get('_embedded') or {}).get('threads') or []
    body = (threads[0].get('body') or '') if threads else ''
    emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', body, re.I)
    # Filter noise
    real = [e for e in emails if not any(x in e.lower() for x in
        ['google', 'mailer', 'daemon', 'postmaster', 'ueipab.edu.ve'])]
```

---

## Step 2 — Triage: Failure vs Delay

**Key distinction:**

| DSN Type | Meaning | Action |
|---|---|---|
| `Delivery Status Notification (Failure)` | Email definitively rejected — permanent bounce | Remove email everywhere |
| `Delivery Status Notification (Delay)` | Temporary delivery problem — may resolve itself | Check for accompanying Failure DSN before acting |

**Rule:** Only remove an email from Odoo/Sheet if there is at least one **Failure** DSN for that address — either active or in closed history (`[DUPLICADO]`, `[REVISION]` prefix). Delay-only addresses may recover; check historical closed convs first.

**Exception:** Delay-only addresses that were previously marked `[RESUELTO-AI]` likely recovered before — leave them in place and just close the active delays.

---

## Step 3 — Cross-reference with Customers Sheet and Odoo

### Google Sheet — Customers tab col J

```python
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_file(
    '/opt/odoo-dev/config/google_sheets_credentials.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc = build('sheets', 'v4', credentials=creds)
SHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'

rows = svc.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='Customers!A2:L').execute().get('values', [])
data = rows[1:]  # skip header row

for i, row in enumerate(data):
    row = (row + [''] * 12)[:12]
    name = row[1]        # col B
    emails_raw = row[9]  # col J
    emails = [e.strip().lower() for e in emails_raw.split(';') if e.strip()]
    hits = [e for e in emails if e in bounced_set]
    if hits:
        print(f'Row {i+3} | {name} | bounced: {hits}')
```

### Odoo PROD — res.partner

```python
import xmlrpc.client, json
cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
url, db, user, key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, key, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

for email in bounced_confirmed:
    rows = models.execute_kw(db, uid, key, 'res.partner', 'search_read',
        [[['email', 'ilike', email]]],
        {'fields': ['id', 'name', 'email'], 'limit': 5})
    for r in rows:
        print(f"id={r['id']} | {r['name']} | {r['email']}")
```

---

## Step 4 — Execute Cleanup

### 4a. Google Sheet: Remove email + red flag

```python
meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
sheet_ids = {s['properties']['title']: s['properties']['sheetId'] for s in meta['sheets']}
cust_sheet_id = sheet_ids['Customers']

# Update cell value (remove bounced email, keep others)
svc.spreadsheets().values().batchUpdate(spreadsheetId=SHEET_ID, body={
    'valueInputOption': 'RAW',
    'data': [{'range': f'Customers!J{row}', 'values': [[new_value]]}]
}).execute()

# Red flag the cell
svc.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={'requests': [{
    'repeatCell': {
        'range': {
            'sheetId': cust_sheet_id,
            'startRowIndex': row - 1, 'endRowIndex': row,
            'startColumnIndex': 9, 'endColumnIndex': 10,
        },
        'cell': {'userEnteredFormat': {
            'backgroundColor': {'red': 1.0, 'green': 0.0, 'blue': 0.0}
        }},
        'fields': 'userEnteredFormat.backgroundColor'
    }
}]}).execute()
```

### 4b. Google Sheet: Log to BounceEmail tab

Tab columns: **A=Date | B=Customer Name | C=Bounced Email | D=Source | E=Status**

```python
bounce_sheet_id = sheet_ids['BounceEmail']

# Get next empty row
existing = svc.spreadsheets().values().get(
    spreadsheetId=SHEET_ID, range='BounceEmail!A:A').execute().get('values', [])
next_row = len(existing) + 1

new_rows = [
    ['2026-05-21', 'CUSTOMER NAME', 'bounced@email.com', 'Campaign Name', 'Removed from Odoo + Sheet'],
]
svc.spreadsheets().values().update(
    spreadsheetId=SHEET_ID,
    range=f'BounceEmail!A{next_row}:E{next_row + len(new_rows) - 1}',
    valueInputOption='RAW',
    body={'values': new_rows}
).execute()
```

### 4c. Odoo PROD: Clean partner email

```python
# For full removal:
models.execute_kw(db, uid, key, 'res.partner', 'write', [[partner_id], {'email': ''}])

# For partial removal (keep other emails in semicolon list):
new_email = '; '.join(e for e in old_email.split(';') if bounced not in e.strip().lower())
models.execute_kw(db, uid, key, 'res.partner', 'write', [[partner_id], {'email': new_email}])
```

### 4d. Freescout: Close DSN conversations

```python
import time

for cid in conv_ids_to_close:
    r = requests.put(f'{base}/conversations/{cid}',
        headers={**headers, 'Content-Type': 'application/json'},
        json={'status': 'closed', 'byUser': 1})
    assert r.status_code == 204, f'Failed {cid}: {r.status_code}'
    time.sleep(0.3)  # be gentle with the API
```

**Important:** `byUser` is **required** alongside any status change — the API rejects the request without it. Use `byUser=1` (admin).

---

## Constraints

- **Freescout:** REST API only — never direct MySQL. Config: `/opt/odoo-dev/config/freescout_api.json`
- **Odoo:** XML-RPC to production. Testing usually mirrors prod contacts but verify first.
- **Do not close** SSH/system alert convs that land in soporte@ — those are router/infrastructure alerts, not bounce emails (subjects contain `system,error` or `script,error`).
- **Do not remove** Delay-only emails without a confirmed Failure DSN.

---

## Bounce History Log

| Date | Campaign | Bounced Emails Removed | Convs Closed |
|---|---|---|---|
| 2026-05-21 | Budget Vote 2026-2027 | annibelmartinez32@gmail.com, domin.anuel0608@gmail.com, dcontrerasperez82@gmail.com, williamjose.velasquezgonzalez@gmail.com, lacruzde@pdvsa.com | 24 (9 Failure + 15 Delay) |
