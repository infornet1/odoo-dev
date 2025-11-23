import sys
import odoo

# Initialize odoo with database
db_name = 'testing'
odoo.tools.config.parse_config(['-d', db_name])

with odoo.api.Environment.manage():
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        # Check module status
        module = env['ir.module.module'].search([
            ('name', '=', 'ueipab_payroll_enhancements')
        ])
        
        print("=" * 60)
        print("📦 Module: ueipab_payroll_enhancements")
        print(f"   State: {module.state}")
        
        if module.state == 'to upgrade':
            print("   ⚠️  Module needs upgrade to apply net_wage field!")
        elif module.state == 'installed':
            # Check if net_wage field exists
            try:
                payslip = env['hr.payslip'].search([], limit=1)
                if payslip:
                    # Try to access net_wage field
                    value = payslip.net_wage
                    print(f"   ✅ net_wage field exists and is accessible")
                    print(f"      Sample value: {value}")
                else:
                    print("   ℹ️  No payslips found to test net_wage field")
            except Exception as e:
                print(f"   ❌ Error accessing net_wage field: {e}")
                print("   Module may need upgrade!")
        
        print("=" * 60)
