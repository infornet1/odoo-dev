#!/usr/bin/env python3
"""
Fix V2 Structure - Remove Parent to Eliminate Duplicate Journal Entries

Problem: V2 structure inherits from BASE structure, which has 3 rules with
         accounting configured (BASIC, GROSS, NET). This causes duplicate
         journal entries when V2 payslips are confirmed.

Solution: Remove parent_id from V2 structure to make it completely independent.
"""

print("=" * 80)
print("FIX V2 STRUCTURE - REMOVE PARENT")
print("=" * 80)

# Get V2 structure
v2_struct = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)

if not v2_struct:
    print("\n❌ V2 structure not found")
    exit(1)

print(f"\n✅ V2 Structure: {v2_struct.name} (ID: {v2_struct.id})")

# Check current parent
if v2_struct.parent_id:
    print(f"\n⚠️  Current Parent: {v2_struct.parent_id.name} (ID: {v2_struct.parent_id.id})")
    print(f"   Parent Code: {v2_struct.parent_id.code}")
    print(f"   Parent Rules: {len(v2_struct.parent_id.rule_ids)}")

    # Show parent rules with accounting
    parent_with_acct = v2_struct.parent_id.rule_ids.filtered(
        lambda r: r.account_debit_id or r.account_credit_id
    )
    print(f"   Parent Rules with Accounting: {len(parent_with_acct)}")
    for rule in parent_with_acct:
        print(f"      - {rule.code}: {rule.name}")

    # Remove parent
    print(f"\n🔧 Removing parent from V2 structure...")
    v2_struct.write({'parent_id': False})

    # Commit the change
    env.cr.commit()

    print(f"✅ Parent removed successfully!")

    # Verify
    v2_struct.invalidate_recordset()
    v2_struct = env['hr.payroll.structure'].browse(v2_struct.id)

    if v2_struct.parent_id:
        print(f"\n❌ ERROR: Parent still exists!")
    else:
        print(f"\n✅ VERIFIED: V2 structure is now independent (no parent)")

else:
    print(f"\n✅ V2 structure already has no parent (independent)")

# Display final V2 structure status
print(f"\n" + "=" * 80)
print("FINAL V2 STRUCTURE STATUS")
print("=" * 80)

print(f"\n✅ Structure: {v2_struct.name}")
print(f"   Code: {v2_struct.code}")
print(f"   Parent: {v2_struct.parent_id.name if v2_struct.parent_id else 'None (Independent)'}")
print(f"   Total Rules: {len(v2_struct.rule_ids)}")

# Count rules with accounting
rules_with_acct = v2_struct.rule_ids.filtered(
    lambda r: r.account_debit_id or r.account_credit_id
)
print(f"   Rules with Accounting: {len(rules_with_acct)}")

print(f"\n📊 V2 Rules with Accounting:")
for rule in rules_with_acct.sorted(lambda r: r.sequence):
    print(f"   - {rule.code}: {rule.name}")

print(f"\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)

print(f"""
✅ V2 structure is now independent!

What this means:
----------------
1. V2 payslips will ONLY use V2's 11 rules
2. No more duplicate journal entries from BASE rules
3. Journal entry total should match V2 GROSS (~$162 for Alejandra Lopez)

Action Required:
----------------
1. ❌ DELETE the problematic journal entry PAY1/2025/11/0266
   - This entry has duplicate BASE rules and is incorrect
   - Go to Accounting > Journal Entries
   - Find PAY1/2025/11/0266
   - Cancel it (button_cancel) or delete it

2. ❌ CANCEL or DELETE the ALEJANDRA LOPEZ payslip (SLIP/704)
   - This payslip used the buggy structure configuration
   - Go to Payroll > Payslips
   - Find SLIP/704
   - Cancel or delete it

3. ✅ CREATE A NEW payslip for ALEJANDRA LOPEZ
   - Use the same period (Nov 1-15, 2025)
   - Select structure: "Salarios Venezuela UEIPAB V2"
   - Compute sheet
   - Verify: Should show ONLY V2 rules (11 lines)
   - Confirm
   - New journal entry should be ~$162.45 total (not $1,450!)

Expected Results (New Payslip):
-------------------------------
- Gross: ~$162.45
- Deductions: ~$5.75
- Net: ~$156.70 (disbursement)
- Journal Entry Total: ~$162.45 ✅ (matches GROSS, not $1,450!)
""")

print("=" * 80)
