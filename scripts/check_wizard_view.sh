#!/bin/bash
# Check if wizard view has our fields

echo "==================================="
echo "Diagnostic: Payslip Wizard View"
echo "==================================="

echo -e "\n1. Checking if view exists:"
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT id, name, active, mode, priority
FROM ir_ui_view
WHERE model='hr.payslip.employees'
ORDER BY priority, id;
"

echo -e "\n2. Checking if fields exist on model:"
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT name, field_description, ttype
FROM ir_model_fields
WHERE model='hr.payslip.employees'
  AND name IN ('structure_id', 'use_contract_structure', 'employee_ids')
ORDER BY name;
"

echo -e "\n3. Checking view inheritance content:"
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT
    substring(arch_db::text from 1 for 200) as arch_preview
FROM ir_ui_view
WHERE id=2872;
"

echo -e "\n4. Module installation status:"
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name='ueipab_payroll_enhancements';
"

echo -e "\n==================================="
echo "If all checks pass, issue is likely:"
echo "- Browser cache"
echo "- Assets not reloaded  "
echo "- Debug mode needed"
echo "==================================="
