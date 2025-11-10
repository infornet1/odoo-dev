#!/bin/bash
# Check for zero-amount Aguinaldos payslips

echo "Checking for zero-amount Aguinaldos payslips..."
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT
    p.number,
    e.name as employee,
    SUM(l.total) as aguinaldos_amount
FROM hr_payslip p
JOIN hr_employee e ON p.employee_id = e.id
JOIN hr_payslip_run pr ON p.payslip_run_id = pr.id
LEFT JOIN hr_payslip_line l ON p.id = l.slip_id
WHERE pr.name = 'Aguinaldos31'
GROUP BY p.id, p.number, e.name
HAVING SUM(COALESCE(l.total, 0)) = 0
ORDER BY e.name;
"

echo ""
echo "If no rows returned, all payslips have amounts > 0 ✓"
