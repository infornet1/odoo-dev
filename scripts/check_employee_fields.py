# Check employee fields for partner/address info
employee = env['hr.employee'].search([], limit=1)
print("Employee fields related to partner/address:")
print(f"- work_email: {hasattr(employee, 'work_email')}")
print(f"- address_home_id: {hasattr(employee, 'address_home_id')}")
print(f"- address_id: {hasattr(employee, 'address_id')}")  
print(f"- user_id: {hasattr(employee, 'user_id')}")
print(f"- user_partner_id: {hasattr(employee, 'user_partner_id')}")

if employee:
    print(f"\nActual employee: {employee.name}")
    if hasattr(employee, 'user_id') and employee.user_id:
        print(f"  user_id.partner_id: {employee.user_id.partner_id.name if employee.user_id.partner_id else 'None'}")
    if hasattr(employee, 'address_id') and employee.address_id:
        print(f"  address_id: {employee.address_id.name}")
