"""
Sync attendance records for maintenance/security staff from production → testing.
ANDRES MORALES, PABLO NAVARRO, SERGIO MANEIRO

Does NOT change work_email — no test emails will be triggered.
Does NOT create hr.attendance.report records.

Run:
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/sync_maintenance_attendance.py
"""
import xmlrpc.client
from datetime import datetime

# ── Production (XML-RPC) ──────────────────────────────────────────────────────
PROD_URL  = 'https://odoo.ueipab.edu.ve'
PROD_DB   = 'DB_UEIPAB'
PROD_USER = 'tdv.devs@gmail.com'
PROD_KEY  = 'f69330e5bd6ae043320f054e9df9fcbbb34522db'

TARGET_NAMES = ['ANDRES MORALES', 'PABLO NAVARRO', 'SERGIO MANEIRO']

# ── Connect to production ─────────────────────────────────────────────────────
print("── Connecting to production via XML-RPC …")
common = xmlrpc.client.ServerProxy(f'{PROD_URL}/xmlrpc/2/common', allow_none=True)
prod_uid = common.authenticate(PROD_DB, PROD_USER, PROD_KEY, {})
if not prod_uid:
    print("ERROR: Production authentication failed.")
    exit(1)
prod = xmlrpc.client.ServerProxy(f'{PROD_URL}/xmlrpc/2/object', allow_none=True)
print(f"   OK — UID {prod_uid}\n")

# ── Process each employee ─────────────────────────────────────────────────────
total_synced = 0

for name in TARGET_NAMES:
    print(f"{'─'*60}")
    print(f"Processing: {name}")

    # Find in production
    prod_emps = prod.execute_kw(PROD_DB, prod_uid, PROD_KEY,
        'hr.employee', 'search_read',
        [[('name', 'ilike', name)]],
        {'fields': ['id', 'name', 'work_email']})
    if not prod_emps:
        print(f"  ⚠ Not found in production — skipping.")
        continue
    prod_emp = prod_emps[0]
    print(f"  Production: [{prod_emp['id']}] {prod_emp['name']}")

    # Fetch attendance from production
    prod_att = prod.execute_kw(PROD_DB, prod_uid, PROD_KEY,
        'hr.attendance', 'search_read',
        [[('employee_id', '=', prod_emp['id'])]],
        {'fields': ['check_in', 'check_out', 'worked_hours'], 'order': 'check_in asc'})
    print(f"  Production records: {len(prod_att)}")
    if prod_att:
        first = prod_att[0]['check_in']
        last  = prod_att[-1]['check_in']
        print(f"  Range: {first[:10]} → {last[:10]}")

    # Find in testing
    test_emp = env['hr.employee'].search([('name', 'ilike', name)], limit=1)
    if not test_emp:
        print(f"  ⚠ Not found in testing — skipping.")
        continue
    print(f"  Testing:    [{test_emp.id}] {test_emp.name} | email kept: {test_emp.work_email or '(none)'}")

    # Clear existing testing records
    env.cr.execute("SELECT COUNT(*) FROM hr_attendance WHERE employee_id = %s", (test_emp.id,))
    existing = env.cr.fetchone()[0]
    if existing:
        env.cr.execute("DELETE FROM hr_attendance WHERE employee_id = %s", (test_emp.id,))
        print(f"  Cleared {existing} existing testing records.")

    # Import via direct SQL (bypasses overlap constraint)
    inserted = 0
    for att in prod_att:
        check_in  = att['check_in']
        check_out = att.get('check_out') or None
        worked    = att.get('worked_hours', 0.0) or 0.0
        env.cr.execute("""
            INSERT INTO hr_attendance (employee_id, check_in, check_out, worked_hours)
            VALUES (%s, %s, %s, %s)
        """, (test_emp.id, check_in, check_out, worked))
        inserted += 1

    env.cr.commit()
    print(f"  ✓ {inserted} records imported.")
    total_synced += inserted
    # NOTE: work_email intentionally NOT changed — no test emails

print(f"\n{'═'*60}")
print(f"Total attendance records synced: {total_synced}")
print("work_email unchanged for all 3 employees — no emails will be sent.")
print("✓ Done.")
