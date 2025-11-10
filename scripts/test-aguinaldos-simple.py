"""Test Aguinaldos payslip confirmation via Odoo shell"""

# Find employee
employee = env['hr.employee'].search([('name', '=ilike', 'ARCIDES ARZOLA')], limit=1)
if not employee:
    print("ERROR: Employee not found")
else:
    print(f"Found employee: {employee.name} (ID: {employee.id})")

# Get contract
contract = env['hr.contract'].search([
    ('employee_id', '=', employee.id),
    ('state', '=', 'open')
], limit=1)

if not contract:
    print("ERROR: No open contract")
else:
    print(f"Contract: {contract.name}")
    print(f"Monthly Salary: ${contract.ueipab_monthly_salary:.2f}")
    print(f"Expected Aguinaldos: ${contract.ueipab_monthly_salary * 2:.2f}")

# Find structure
struct = env['hr.payroll.structure'].search([('code', '=', 'AGUINALDOS_2025')], limit=1)
print(f"Structure: {struct.name} (ID: {struct.id})")

# Find or create payslip
payslip = env['hr.payslip'].search([
    ('employee_id', '=', employee.id),
    ('struct_id', '=', struct.id),
    ('state', '=', 'draft')
], limit=1)

if not payslip:
    print("Creating new payslip...")
    payslip = env['hr.payslip'].create({
        'employee_id': employee.id,
        'contract_id': contract.id,
        'struct_id': struct.id,
        'name': f'Aguinaldos Test - {employee.name}',
        'date_from': '2025-12-01',
        'date_to': '2025-12-15',
    })
    env.cr.commit()

print(f"Payslip: {payslip.number} (ID: {payslip.id}, State: {payslip.state})")

# Test 1: Compute
print("\n=== TEST 1: Computing ===")
try:
    payslip.compute_sheet()
    env.cr.commit()
    print("✓ Compute successful")
    for line in payslip.line_ids:
        if line.code == 'AGUINALDOS':
            print(f"  {line.name}: ${line.total:.2f}")
except Exception as e:
    print(f"✗ Compute failed: {e}")

# Test 2: Confirm (CRITICAL)
print("\n=== TEST 2: Confirming (CRITICAL) ===")
try:
    payslip.action_payslip_done()
    env.cr.commit()
    print(f"✓ Confirmation successful! State: {payslip.state}")
    if payslip.move_id:
        print(f"  Journal entry: {payslip.move_id.name}")
        for line in payslip.move_id.line_ids:
            if line.debit > 0:
                print(f"    Dr {line.account_id.code}: ${line.debit:.2f}")
            if line.credit > 0:
                print(f"    Cr {line.account_id.code}: ${line.credit:.2f}")
except Exception as e:
    print(f"✗ Confirmation failed: {e}")
    import traceback
    traceback.print_exc()
