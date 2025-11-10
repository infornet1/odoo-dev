# PHASE TRANSITION CHECKLIST

## Script Configuration Changes Between Phases

### Current Status: PHASE 1 (Local Development)

The `sync-monthly-salary-from-spreadsheet.py` script is currently configured for **LOCAL TESTING**.

---

## PHASE 1 → PHASE 2 TRANSITION

**ONLY after Phase 1 is 100% complete and validated**, update the script configuration:

### File to Modify:
`/opt/odoo-dev/scripts/sync-monthly-salary-from-spreadsheet.py`

### Lines to Change:
Lines 32-40

### Current Configuration (Phase 1):
```python
# PHASE 1: Local development database
# For Phase 2, change to: host='10.124.0.3', port=5432, database='testing'
self.db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'odoo17',
    'user': 'odoo',
    'password': 'odoo'
}
```

### Change To (Phase 2):
```python
# PHASE 2: Production-acceptance database
# Local testing completed successfully on [DATE]
self.db_config = {
    'host': '10.124.0.3',
    'port': 5432,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo'
}
```

---

## Pre-Transition Validation

**Before changing configuration, verify all Phase 1 gates passed:**

- [ ] Database schema changes applied successfully locally
- [ ] Test sync (1 employee) completed with correct values
- [ ] Full sync (45 employees) completed successfully
- [ ] Total monthly salary = $12,753.41 exactly
- [ ] All enhanced notes formatted correctly with exchange rate
- [ ] Aguinaldos salary structure created in local Odoo
- [ ] Test payslips generate correctly with 2x multiplier
- [ ] Sample calculations match spreadsheet exactly
- [ ] Existing payroll structures still work (regression test passed)
- [ ] No errors, no data corruption, no interference
- [ ] Backup tables created for all operations
- [ ] User explicitly approved transition to Phase 2

---

## Testing After Configuration Change

After updating the script configuration for Phase 2:

1. **Verify Connection String:**
```bash
# Should show: 10.124.0.3:5432/testing
python3 sync-monthly-salary-from-spreadsheet.py --test
```

2. **Run Test Mode First:**
```bash
# This will update only 1 employee on production-acceptance
python3 sync-monthly-salary-from-spreadsheet.py --test
```

3. **Verify Results Match Local:**
- Compare employee salary values
- Compare notes format
- Verify backup table created
- Check no interference with existing contracts

4. **Only Then Run Production Mode:**
```bash
python3 sync-monthly-salary-from-spreadsheet.py --production
```

---

## Quick Reference

| Phase | Host | Port | Database | Purpose |
|-------|------|------|----------|---------|
| Phase 1 | localhost | 5433 | odoo17 | Local dev/testing |
| Phase 2 | 10.124.0.3 | 5432 | testing | Production-acceptance |

---

## Rollback

If issues are found in Phase 2 and you need to go back to local testing:

1. Change configuration back to localhost
2. Debug and fix issues locally
3. Re-validate all Phase 1 gates
4. Get user approval again
5. Change back to 10.124.0.3

---

**IMPORTANT:** Never run the script against production-acceptance (10.124.0.3) until Phase 1 is 100% complete and approved!
