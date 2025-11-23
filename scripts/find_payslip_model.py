# Find the correct external ID for hr.payslip model

# Search for the model
model = env['ir.model'].search([('model', '=', 'hr.payslip')])
if model:
    print(f"✅ Found model: {model.name}")
    print(f"   Model ID: {model.id}")
    print(f"   Model: {model.model}")
    
    # Find external ID
    external_id = env['ir.model.data'].search([
        ('model', '=', 'ir.model'),
        ('res_id', '=', model.id)
    ])
    
    if external_id:
        print(f"\n✅ External ID found:")
        for ext in external_id:
            print(f"   {ext.module}.{ext.name}")
    else:
        print("\n❌ No external ID found for this model")
        print(f"   You can reference it directly by ID: {model.id}")
else:
    print("❌ Model hr.payslip not found")
