#!/usr/bin/env python3
"""
Update Contract Prepaid Amounts for Test Cases
Date: 2025-11-17
Purpose: Set ueipab_vacation_prepaid_amount for YOSMARI and VIRGINIA
"""

print("="*80)
print("UPDATE CONTRACT PREPAID AMOUNTS")
print("="*80)

Employee = env['hr.employee']
Contract = env['hr.contract']

# Test Case 1: YOSMARI DEL CARMEN GONZÁLEZ ROMERO
# Liquidation: Sep 2024 - Oct 2025 (14.10 months)
# Prepaid: Aug 1, 2025 = $88.98
print("\n1. YOSMARI DEL CARMEN GONZÁLEZ ROMERO")
print("-" * 80)

yosmari = Employee.search([('name', 'ilike', 'YOSMARI')], limit=1)
if yosmari:
    print(f"   Employee: {yosmari.name} (ID: {yosmari.id})")

    # Get contract (any state - might be 'close' for terminated employee)
    contract = Contract.search([
        ('employee_id', '=', yosmari.id)
    ], limit=1)

    if contract:
        print(f"   Contract: {contract.name} (ID: {contract.id})")
        print(f"   Current prepaid amount: ${contract.ueipab_vacation_prepaid_amount}")

        # Update prepaid amount
        contract.write({'ueipab_vacation_prepaid_amount': 88.98})
        env.cr.commit()  # Commit the change

        print(f"   ✅ Updated to: $88.98")
    else:
        print("   ❌ No active contract found")
else:
    print("   ❌ Employee not found")

# Test Case 2: VIRGINIA VERDE
# Liquidation: Sep 2023 - Jul 2025 (22.07 months)
# Prepaid: Aug 1, 2024 = $134.48 + Aug 1, 2025 = $122.34 = $256.82
print("\n2. VIRGINIA VERDE")
print("-" * 80)

virginia = Employee.search([('name', 'ilike', 'VIRGINIA VERDE')], limit=1)
if virginia:
    print(f"   Employee: {virginia.name} (ID: {virginia.id})")

    # Get contract (any state)
    contract = Contract.search([
        ('employee_id', '=', virginia.id)
    ], limit=1)

    if contract:
        print(f"   Contract: {contract.name} (ID: {contract.id})")
        print(f"   Current prepaid amount: ${contract.ueipab_vacation_prepaid_amount}")

        # Update prepaid amount
        contract.write({'ueipab_vacation_prepaid_amount': 256.82})
        env.cr.commit()  # Commit the change

        print(f"   ✅ Updated to: $256.82 ($134.48 + $122.34)")
    else:
        print("   ❌ No active contract found")
else:
    print("   ❌ Employee not found")

print("\n" + "="*80)
print("UPDATE COMPLETE!")
print("="*80)
print("\nNext step: Test liquidations to verify NET amounts")
print("- YOSMARI: Expected NET $15.01")
print("- VIRGINIA: Expected NET $27.26")
print("="*80)
