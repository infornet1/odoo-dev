# Test the email sending functionality for a payslip

# Get a payslip
payslip = env['hr.payslip'].search([('state', 'in', ['done', 'paid'])], limit=1)

if not payslip:
    print("❌ No confirmed payslips found")
    exit()

print(f"✅ Testing with payslip: {payslip.name}")
print(f"   Employee: {payslip.employee_id.name}")
print(f"   State: {payslip.state}")

# Check net_wage field
try:
    net_wage = payslip.net_wage
    print(f"   Net Wage: {net_wage}")
    print("   ✅ net_wage field is accessible")
except Exception as e:
    print(f"   ❌ Error accessing net_wage: {e}")

# Check currency_id field
try:
    currency = payslip.currency_id
    print(f"   Currency: {currency.name if currency else 'None'}")
    print("   ✅ currency_id field is accessible")
except Exception as e:
    print(f"   ❌ Error accessing currency_id: {e}")

# Try to call the email composition method
try:
    result = payslip.action_compose_payslip_email()
    print(f"\n✅ Email composition method executed successfully!")
    print(f"   Result type: {result.get('type')}")
    print(f"   Target model: {result.get('res_model')}")
    print(f"   View mode: {result.get('view_mode')}")
except Exception as e:
    print(f"\n❌ Error calling action_compose_payslip_email(): {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
