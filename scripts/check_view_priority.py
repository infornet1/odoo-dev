#!/usr/bin/env python3
# Check view priorities and inheritance order

views = env['ir.ui.view'].search([
    ('model', '=', 'hr.payslip'),
    ('type', '=', 'form'),
    ('active', '=', True)
], order='priority, id')

print("HR Payslip Form Views (in application order):\n")
print(f"{'Priority':<10} {'ID':<10} {'Name':<60} {'Mode'}")
print("=" * 110)

for view in views:
    mode = view.mode or 'primary'
    print(f"{view.priority:<10} {view.id:<10} {view.name:<60} {mode}")

# Check specifically our view
print("\n" + "=" * 110)
our_view = env['ir.ui.view'].browse(2917)
print(f"\nOur view details:")
print(f"  Name: {our_view.name}")
print(f"  Priority: {our_view.priority}")
print(f"  Sequence: {our_view.id}")
print(f"  Active: {our_view.active}")

# Check if xpath is finding the right button
print("\n" + "=" * 110)
print("\nChecking base view for action_compute_sheet button...")
base_view = env['ir.ui.view'].search([
    ('name', '=', 'hr.payslip.view.form'),
    ('model', '=', 'hr.payslip')
], limit=1)

if base_view:
    if 'action_compute_sheet' in base_view.arch:
        print("✅ Base view contains 'action_compute_sheet' button")
        # Extract the button section
        import re
        pattern = r'<button[^>]*name="action_compute_sheet"[^>]*>'
        matches = re.findall(pattern, base_view.arch)
        if matches:
            print(f"  Found button: {matches[0][:100]}...")
    else:
        print("❌ Base view does NOT contain 'action_compute_sheet' button")
        print("   This could explain why the xpath fails!")

# Try to get the final combined view
print("\n" + "=" * 110)
print("\nAttempting to render final view for a sample payslip...")
try:
    View = env['ir.ui.view']
    # Get view arch for the form
    result = View.with_context(check_view_ids=[2917]).get_view(
        view_id=None,
        view_type='form',
        model='hr.payslip'
    )
    if 'Send Mail' in str(result.get('arch', '')):
        print("✅ 'Send Mail' button IS in final rendered view!")
    else:
        print("❌ 'Send Mail' button NOT in final rendered view")
        print("   The xpath may not be matching correctly")
except Exception as e:
    print(f"Error rendering view: {e}")
