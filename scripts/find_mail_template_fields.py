# Find available fields on mail.template model for reports

model = env['ir.model'].search([('model', '=', 'mail.template')])
if model:
    print("✅ Found mail.template model")
    
    # Get all fields
    fields = env['ir.model.fields'].search([
        ('model_id', '=', model.id),
        ('name', 'like', 'report')
    ])
    
    print("\n📋 Report-related fields:")
    for field in fields:
        print(f"   - {field.name} ({field.ttype}): {field.field_description}")
    
    # Also check for attachment fields
    att_fields = env['ir.model.fields'].search([
        ('model_id', '=', model.id),
        ('name', 'like', 'attach')
    ])
    
    print("\n📎 Attachment-related fields:")
    for field in att_fields:
        print(f"   - {field.name} ({field.ttype}): {field.field_description}")
else:
    print("❌ mail.template model not found")
