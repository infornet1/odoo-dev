"""
Sync NIDYA LIRA's attendance records from production → testing.
Also updates her work_email in testing to gustavo.perdomo@ueipab.edu.ve.

Run inside Odoo shell:
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/sync_nidya_attendance.py
"""
import xmlrpc.client
from datetime import datetime

# ── Production (XML-RPC) ──────────────────────────────────────────────────────
PROD_URL  = 'https://odoo.ueipab.edu.ve'
PROD_DB   = 'DB_UEIPAB'
PROD_USER = 'tdv.devs@gmail.com'
PROD_KEY  = 'f69330e5bd6ae043320f054e9df9fcbbb34522db'

TEST_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'

# ── Connect to production ─────────────────────────────────────────────────────
print("── Connecting to production via XML-RPC …")
common = xmlrpc.client.ServerProxy(f'{PROD_URL}/xmlrpc/2/common', allow_none=True)
prod_uid = common.authenticate(PROD_DB, PROD_USER, PROD_KEY, {})
if not prod_uid:
    print("ERROR: Production authentication failed.")
    exit(1)
prod = xmlrpc.client.ServerProxy(f'{PROD_URL}/xmlrpc/2/object', allow_none=True)
print(f"   OK — UID {prod_uid}")

# ── Find NIDYA LIRA in production ─────────────────────────────────────────────
prod_emps = prod.execute_kw(PROD_DB, prod_uid, PROD_KEY,
    'hr.employee', 'search_read',
    [[('name', 'ilike', 'NIDYA')]],
    {'fields': ['id', 'name', 'work_email']})
if not prod_emps:
    print("ERROR: NIDYA not found in production.")
    exit(1)
prod_emp = prod_emps[0]
print(f"── Production: [{prod_emp['id']}] {prod_emp['name']} | {prod_emp['work_email']}")

# ── Fetch all her attendance records from production ──────────────────────────
prod_att = prod.execute_kw(PROD_DB, prod_uid, PROD_KEY,
    'hr.attendance', 'search_read',
    [[('employee_id', '=', prod_emp['id'])]],
    {'fields': ['check_in', 'check_out', 'worked_hours'], 'order': 'check_in asc'})
print(f"── Production attendance records: {len(prod_att)}")
for a in prod_att[:5]:
    print(f"   {a['check_in']} → {a.get('check_out') or '(no exit)'} ({a['worked_hours']:.2f}h)")
if len(prod_att) > 5:
    print(f"   … and {len(prod_att) - 5} more")

# ── Find NIDYA LIRA in testing (via ORM) ──────────────────────────────────────
test_emp = env['hr.employee'].search([('name', 'ilike', 'NIDYA')], limit=1)
if not test_emp:
    print("ERROR: NIDYA not found in testing.")
    exit(1)
print(f"\n── Testing:    [{test_emp.id}] {test_emp.name} | {test_emp.work_email or '(no email)'}")

# ── Clear existing testing records via SQL (bypass Odoo constraints) ──────────
env.cr.execute("SELECT COUNT(*) FROM hr_attendance WHERE employee_id = %s", (test_emp.id,))
existing_count = env.cr.fetchone()[0]
print(f"── Testing existing records: {existing_count} (will clear and reimport)")
env.cr.execute("DELETE FROM hr_attendance WHERE employee_id = %s", (test_emp.id,))
print(f"   Cleared.")

# ── Import all production records via SQL (bypasses overlap constraint) ────────
# Production data has biometric glitches (e.g. 93h sessions) — direct SQL
# insert is correct for testing purposes.
created = 0
for att in prod_att:
    check_in  = att['check_in']
    check_out = att.get('check_out') or None
    worked    = att.get('worked_hours', 0.0) or 0.0
    env.cr.execute("""
        INSERT INTO hr_attendance (employee_id, check_in, check_out, worked_hours)
        VALUES (%s, %s, %s, %s)
    """, (test_emp.id, check_in, check_out, worked))
    created += 1

env.cr.commit()
print(f"\n── Attendance sync: {created} records imported (direct SQL)")

# ── Update work_email in testing ──────────────────────────────────────────────
old_email = test_emp.work_email
test_emp.work_email = TEST_EMAIL
env.cr.commit()
print(f"── Email updated: '{old_email}' → '{TEST_EMAIL}'")

# ── Final verification ────────────────────────────────────────────────────────
total = env['hr.attendance'].search_count([('employee_id', '=', test_emp.id)])
print(f"\n── Testing total attendance records now: {total}")
print(f"── Email confirmed: {test_emp.work_email}")
print("\n✓ Done.")
