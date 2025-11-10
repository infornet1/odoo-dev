#!/bin/bash
# Install ueipab_payroll_enhancements module

echo "Installing ueipab_payroll_enhancements module..."

# Stop Odoo
docker stop odoo-dev-web

# Install the module using Odoo CLI
docker start odoo-dev-web
sleep 5

docker exec odoo-dev-web odoo -d testing -i ueipab_payroll_enhancements --stop-after-init

# Restart Odoo normally
docker restart odoo-dev-web

echo "Module installation complete!"
echo "Waiting for Odoo to start..."
sleep 15

echo "Verifying installation..."
docker exec odoo-dev-postgres psql -U odoo -d testing -c "SELECT name, state FROM ir_module_module WHERE name = 'ueipab_payroll_enhancements';"
