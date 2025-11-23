# Check if report_name field exists on mail.template

model = env['ir.model'].search([('model', '=', 'mail.template')])
field = env['ir.model.fields'].search([
    ('model_id', '=', model.id),
    ('name', '=', 'report_name')
])

if field:
    print(f"✅ report_name field exists")
    print(f"   Type: {field.ttype}")
    print(f"   Description: {field.field_description}")
else:
    print("❌ report_name field does NOT exist on mail.template")
    print("\n💡 Checking for similar fields:")
    similar = env['ir.model.fields'].search([
        ('model_id', '=', model.id),
        ('name', 'like', 'name')
    ])
    for f in similar:
        print(f"   - {f.name} ({f.ttype}): {f.field_description}")
