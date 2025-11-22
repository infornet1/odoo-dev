#!/usr/bin/env python3
"""
Create Payslip Email Templates Programmatically

This script creates email templates directly in the database,
bypassing XML data file validation issues.

Templates Created:
1. Regular Payslip Email - Employee Delivery
2. AGUINALDOS Email - Christmas Bonus Delivery

Date: 2025-11-21
"""

# Read HTML templates from XML files
import re
from pathlib import Path

print("=" * 80)
print("CREATING PAYSLIP EMAIL TEMPLATES")
print("=" * 80)

# Get template directory
# Note: Inside Docker container, addons are at /mnt/extra-addons/
template_dir = Path('/mnt/extra-addons/ueipab_payroll_enhancements/data/email_templates')

def extract_html_from_xml(xml_file):
    """Extract HTML content from XML CDATA section."""
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract content between <![CDATA[ and ]]>
    match = re.search(r'<!\[CDATA\[(.*?)\]\]>', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

# Extract HTML templates
print("\n📄 Reading template files...")
payslip_html = extract_html_from_xml(template_dir / 'payslip_email_template.xml.bak')
aguinaldos_html = extract_html_from_xml(template_dir / 'aguinaldos_email_template.xml.bak')

if not payslip_html:
    print("❌ Failed to extract regular payslip template")
    exit(1)

if not aguinaldos_html:
    print("❌ Failed to extract AGUINALDOS template")
    exit(1)

print(f"✅ Regular payslip template: {len(payslip_html)} characters")
print(f"✅ AGUINALDOS template: {len(aguinaldos_html)} characters")

# Get model reference
print("\n🔍 Looking up hr.payslip model...")
Model = env['ir.model']
payslip_model = Model.search([('model', '=', 'hr.payslip')], limit=1)

if not payslip_model:
    print("❌ hr.payslip model not found!")
    exit(1)

print(f"✅ Found model: {payslip_model.name} (ID: {payslip_model.id})")

# Check if templates already exist
print("\n🔍 Checking for existing templates...")
Template = env['mail.template']

existing_payslip = Template.search([
    ('name', '=', 'Payslip Email - Employee Delivery')
], limit=1)

existing_aguinaldos = Template.search([
    ('name', '=', 'Aguinaldos Email - Christmas Bonus Delivery')
], limit=1)

if existing_payslip:
    print(f"⚠️  Regular payslip template already exists (ID: {existing_payslip.id})")
    print("   Deleting old template...")
    existing_payslip.unlink()
    print("   ✅ Deleted")

if existing_aguinaldos:
    print(f"⚠️  AGUINALDOS template already exists (ID: {existing_aguinaldos.id})")
    print("   Deleting old template...")
    existing_aguinaldos.unlink()
    print("   ✅ Deleted")

# Create Template 1: Regular Payslip
print("\n📧 Creating Template 1: Regular Payslip Email...")

payslip_template_vals = {
    'name': 'Payslip Email - Employee Delivery',
    'model_id': payslip_model.id,
    'subject': '💰 Comprobante de Pago - ${object.employee_id.name} (${object.date_from.strftime("%B %Y") if object.date_from else "N/A"})',
    'email_from': 'recursoshumanos@ueipab.edu.ve',
    'email_to': '{{ object.employee_id.work_email }}',
    'body_html': payslip_html,
    'auto_delete': True,
    'lang': 'es_VE',
}

try:
    payslip_template = Template.create(payslip_template_vals)
    print(f"✅ Created: {payslip_template.name}")
    print(f"   ID: {payslip_template.id}")
    print(f"   Model: {payslip_template.model}")
except Exception as e:
    print(f"❌ Error creating regular payslip template: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Create Template 2: AGUINALDOS
print("\n🎄 Creating Template 2: AGUINALDOS Email...")

aguinaldos_template_vals = {
    'name': 'Aguinaldos Email - Christmas Bonus Delivery',
    'model_id': payslip_model.id,
    'subject': '🎄 Aguinaldos (Bono Navideño) - ${object.employee_id.name}',
    'email_from': 'recursoshumanos@ueipab.edu.ve',
    'email_to': '{{ object.employee_id.work_email }}',
    'body_html': aguinaldos_html,
    'auto_delete': True,
    'lang': 'es_VE',
}

try:
    aguinaldos_template = Template.create(aguinaldos_template_vals)
    print(f"✅ Created: {aguinaldos_template.name}")
    print(f"   ID: {aguinaldos_template.id}")
    print(f"   Model: {aguinaldos_template.model}")
except Exception as e:
    print(f"❌ Error creating AGUINALDOS template: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Verify templates
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

all_templates = Template.search([
    ('name', 'in', [
        'Payslip Email - Employee Delivery',
        'Aguinaldos Email - Christmas Bonus Delivery'
    ])
])

print(f"\n✅ Found {len(all_templates)} templates in database:")
for template in all_templates:
    print(f"\n   Template ID: {template.id}")
    print(f"   Name: {template.name}")
    print(f"   Model: {template.model}")
    print(f"   Subject: {template.subject[:60]}...")
    print(f"   Email From: {template.email_from}")
    print(f"   Auto Delete: {template.auto_delete}")
    print(f"   Body Length: {len(template.body_html)} characters")

# Commit the transaction
print("\n💾 Committing to database...")
env.cr.commit()
print("✅ Transaction committed")

print("\n" + "=" * 80)
print("✅ EMAIL TEMPLATES CREATED SUCCESSFULLY!")
print("=" * 80)

print("\n📋 Next Steps:")
print("   1. Navigate to Settings > Technical > Email > Templates")
print("   2. Verify templates appear in list")
print("   3. Test template rendering with a sample payslip")
print("   4. Proceed to Phase 2: Wizard Development")

print("\n🎯 Template Access:")
print(f"   - XML ID (regular): ueipab_payroll_enhancements.email_template_payslip_delivery")
print(f"   - Database ID (regular): {payslip_template.id}")
print(f"   - XML ID (aguinaldos): ueipab_payroll_enhancements.email_template_aguinaldos_delivery")
print(f"   - Database ID (aguinaldos): {aguinaldos_template.id}")

print("\n" + "=" * 80)
