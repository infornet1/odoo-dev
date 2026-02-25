# -*- coding: utf-8 -*-
"""
Production Salary Structure Creation Script
============================================
Creates Venezuelan V2 salary structures in production database.

Structures to create:
1. VE_PAYROLL_V2 - Regular payroll with V2 fields (11 rules)
2. LIQUID_VE_V2 - Liquidation with V2 fields (14 rules)
3. AGUINALDOS_2025 - Christmas bonus with V2 formula (1 rule)

Usage: Run via Odoo shell in production container
  docker exec -i ueipab17 odoo shell -d DB_UEIPAB --no-http < script.py

Author: Technical Team
Date: 2025-11-24
"""

print("="*80)
print("PRODUCTION SALARY STRUCTURE CREATION")
print("="*80)

# Get models
Structure = env['hr.payroll.structure']
SalaryRule = env['hr.salary.rule']
Category = env['hr.salary.rule.category']

# Get or create categories
def get_or_create_category(code, name):
    cat = Category.search([('code', '=', code)], limit=1)
    if not cat:
        cat = Category.create({'code': code, 'name': name})
        print(f"  Created category: {code}")
    return cat

print("\n[1/4] Setting up categories...")
cat_basic = get_or_create_category('BASIC', 'Basic')
cat_alw = get_or_create_category('ALW', 'Allowance')
cat_gross = get_or_create_category('GROSS', 'Gross')
cat_ded = get_or_create_category('DED', 'Deduction')
cat_net = get_or_create_category('NET', 'Net')
print("  ✅ Categories ready")

# =============================================================================
# SALARY RULES DATA
# =============================================================================

VE_PAYROLL_V2_RULES = [
    {
        'code': 'VE_SALARY_V2',
        'name': 'VE_SALARY_V2 - Salary V2 (Deductible)',
        'sequence': 1,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
multiplier = 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_salary / 2.0) * multiplier'''
    },
    {
        'code': 'VE_EXTRABONUS_V2',
        'name': 'VE_EXTRABONUS_V2 - Extra Bonus V2',
        'sequence': 2,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_extrabonus = contract.ueipab_extrabonus_v2 or 0.0
multiplier = 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_extrabonus / 2.0) * multiplier'''
    },
    {
        'code': 'VE_BONUS_V2',
        'name': 'VE_BONUS_V2 - Bonus V2',
        'sequence': 3,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_bonus = contract.ueipab_bonus_v2 or 0.0
multiplier = 1.0
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
    multiplier = (payslip.payslip_run_id.advance_percentage or 100.0) / 100.0
result = (monthly_bonus / 2.0) * multiplier'''
    },
    {
        'code': 'VE_CESTA_TICKET_V2',
        'name': 'VE_CESTA_TICKET_V2 - Cesta Ticket',
        'sequence': 4,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_cesta = contract.cesta_ticket_usd or 0.0
result = monthly_cesta / 2.0'''
    },
    {
        'code': 'VE_GROSS_V2',
        'name': 'VE_GROSS_V2 - Total Gross',
        'sequence': 5,
        'category_id': cat_gross.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''result = VE_SALARY_V2 + VE_EXTRABONUS_V2 + VE_BONUS_V2 + VE_CESTA_TICKET_V2'''
    },
    {
        'code': 'VE_SSO_DED_V2',
        'name': 'VE_SSO_DED_V2 - SSO 4.5%',
        'sequence': 101,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Venezuela SSO monthly ceiling in Bolivares
sso_ceiling_bs = 1300.0

# Use the bi-weekly exchange rate already captured on this payslip
# Fallback to 236.4601 (recent rate) if rate is missing
exchange_rate = payslip.exchange_rate_used or 236.4601

# Convert Bs 1300 ceiling to USD using bi-weekly rate
sso_ceiling_usd = sso_ceiling_bs / exchange_rate

# Get employee's monthly salary in USD
employee_salary_usd = contract.ueipab_salary_v2 or 0.0

# Apply ceiling: use lower of employee salary or Bs 1300 (in USD)
sso_base = min(employee_salary_usd, sso_ceiling_usd)

# Calculate monthly deduction at 4% then halve for quincena
monthly_deduction = sso_base * 0.04
result = -(monthly_deduction / 2.0)'''
    },
    {
        'code': 'VE_PARO_DED_V2',
        'name': 'VE_PARO_DED_V2 - PARO 0.5%',
        'sequence': 102,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.005
result = -(monthly_deduction / 2.0)'''
    },
    {
        'code': 'VE_FAOV_DED_V2',
        'name': 'VE_FAOV_DED_V2 - FAOV 1%',
        'sequence': 103,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.01
result = -(monthly_deduction / 2.0)'''
    },
    {
        'code': 'VE_ARI_DED_V2',
        'name': 'VE_ARI_DED_V2 - ARI Variable %',
        'sequence': 104,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
ari_rate = (contract.ueipab_ari_withholding_rate or 0.0) / 100.0
monthly_deduction = monthly_salary * ari_rate
result = -(monthly_deduction / 2.0)'''
    },
    {
        'code': 'VE_TOTAL_DED_V2',
        'name': 'VE_TOTAL_DED_V2 - Total Deductions',
        'sequence': 105,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''result = VE_SSO_DED_V2 + VE_FAOV_DED_V2 + VE_PARO_DED_V2 + VE_ARI_DED_V2'''
    },
    {
        'code': 'VE_NET_V2',
        'name': 'VE_NET_V2 - Net Salary',
        'sequence': 200,
        'category_id': cat_net.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''result = VE_GROSS_V2 + VE_TOTAL_DED_V2'''
    },
]

LIQUID_VE_V2_RULES = [
    {
        'code': 'LIQUID_SERVICE_MONTHS_V2',
        'name': 'Meses de Servicio Liquidacion V2',
        'sequence': 1,
        'category_id': cat_basic.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Calculate service months from contract start to termination
start_date = contract.date_start
end_date = payslip.date_to

# Calculate total days
days_diff = (end_date - start_date).days

# Convert to months (30 days per month)
result = days_diff / 30.0'''
    },
    {
        'code': 'LIQUID_DAILY_SALARY_V2',
        'name': 'Salario Diario Base V2',
        'sequence': 2,
        'category_id': cat_basic.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Daily salary based on V2 salary field
base_salary = contract.ueipab_salary_v2 or 0.0
result = base_salary / 30.0'''
    },
    {
        'code': 'LIQUID_INTEGRAL_DAILY_V2',
        'name': 'Salario Diario Integral V2',
        'sequence': 3,
        'category_id': cat_basic.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Venezuelan "Salario Integral" per LOTTT Article 104
base_daily = (contract.ueipab_salary_v2 or 0.0) / 30.0

# Utilidades proportion: 60 days per year / 360 days
utilidades_daily = base_daily * (60.0 / 360.0)

# Bono Vacacional proportion: 15 days per year / 360 days
bono_vac_daily = base_daily * (15.0 / 360.0)

# Integral = Base + Benefits
result = base_daily + utilidades_daily + bono_vac_daily'''
    },
    {
        'code': 'LIQUID_ANTIGUEDAD_DAILY_V2',
        'name': 'Tasa Diaria Antiguedad V2',
        'sequence': 4,
        'category_id': cat_basic.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Same as integral daily salary for antiguedad calculations
base_daily = (contract.ueipab_salary_v2 or 0.0) / 30.0
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily'''
    },
    {
        'code': 'LIQUID_VACACIONES_V2',
        'name': 'Vacaciones V2',
        'sequence': 11,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Vacaciones: Progressive rate based on seniority (LOTTT Article 190)
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for progressive rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual vacation days based on total seniority (PROGRESSIVE)
if total_seniority_years >= 16:
    annual_vacation_days = 30.0  # Maximum per LOTTT
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year (Year 1=15, Year 2=16, Year 3=17, etc.)
    annual_vacation_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_vacation_days = 15.0  # Minimum

# Calculate for FULL liquidation period (no exclusions)
vacation_days = (service_months / 12.0) * annual_vacation_days

result = vacation_days * daily_salary'''
    },
    {
        'code': 'LIQUID_BONO_VACACIONAL_V2',
        'name': 'Bono Vacacional V2',
        'sequence': 12,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Bono Vacacional: Progressive rate based on seniority
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual bonus days based on total seniority
if total_seniority_years >= 16:
    annual_bonus_days = 30.0  # Maximum
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year
    annual_bonus_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_bonus_days = 15.0  # Minimum

# Calculate for FULL liquidation period (no exclusions)
bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary'''
    },
    {
        'code': 'LIQUID_UTILIDADES_V2',
        'name': 'Utilidades V2',
        'sequence': 13,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Utilidades: 15 days per year (UEIPAB company policy)
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# UEIPAB policy: 15 days per year
if service_months < 12:
    # First year: proportional
    utilidades_days = (service_months / 12.0) * 15.0
else:
    # Full year: 15 days
    utilidades_days = 15.0

result = utilidades_days * daily_salary'''
    },
    {
        'code': 'LIQUID_PRESTACIONES_V2',
        'name': 'Prestaciones V2',
        'sequence': 14,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Prestaciones: 15 days per quarter (LOTTT Article 142 System A)
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
integral_daily = LIQUID_INTEGRAL_DAILY_V2 or 0.0

# LOTTT Article 142 System A: 15 days per quarter
quarters = service_months / 3.0
prestaciones_days = quarters * 15.0

result = prestaciones_days * integral_daily'''
    },
    {
        'code': 'LIQUID_ANTIGUEDAD_V2',
        'name': 'Antigüedad V2',
        'sequence': 15,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Antigüedad: 2 days per month with historical tracking support
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY_V2 or 0.0

# Threshold: 1 month + 1 day = approximately 1.03 months
if service_months < 1.03:
    antiguedad_days = 0.0
else:
    # Try to get historical tracking fields safely
    try:
        original_hire = contract.ueipab_original_hire_date
        if not original_hire:
            original_hire = False
    except:
        original_hire = False

    try:
        previous_liquidation = contract.ueipab_previous_liquidation_date
        if not previous_liquidation:
            previous_liquidation = False
    except:
        previous_liquidation = False

    if original_hire:
        # Calculate total seniority from original hire date
        total_days = (payslip.date_to - original_hire).days
        total_months = total_days / 30.0

        # Validate previous_liquidation is after contract start
        if previous_liquidation and previous_liquidation >= contract.date_start:
            # Valid previous liquidation - deduct already-paid antiguedad period
            paid_days = (previous_liquidation - original_hire).days
            paid_months = paid_days / 30.0

            # Net antiguedad owed = Total - Already paid
            net_months = total_months - paid_months
            antiguedad_days = net_months * 2
        else:
            # No valid previous liquidation - calculate for total seniority
            antiguedad_days = total_months * 2
    else:
        # No historical tracking, use standard calculation
        antiguedad_days = service_months * 2

result = antiguedad_days * antiguedad_daily'''
    },
    {
        'code': 'LIQUID_INTERESES_V2',
        'name': 'Intereses V2',
        'sequence': 16,
        'category_id': cat_alw.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Interest on accumulated prestaciones
# Annual rate: 13%
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
prestaciones = LIQUID_PRESTACIONES_V2 or 0.0

# Average balance (prestaciones accrue over time)
average_balance = prestaciones * 0.5

# Annual interest rate = 13%
annual_rate = 0.13

# Interest for period worked
interest_fraction = service_months / 12.0
result = average_balance * annual_rate * interest_fraction'''
    },
    {
        'code': 'LIQUID_FAOV_V2',
        'name': 'FAOV V2',
        'sequence': 21,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# FAOV: 1% deduction on salary components only
# Calculate deduction base (only salary-like components)
deduction_base = ((LIQUID_VACACIONES_V2 or 0) +
                  (LIQUID_BONO_VACACIONAL_V2 or 0) +
                  (LIQUID_UTILIDADES_V2 or 0))

result = -1 * (deduction_base * 0.01)'''
    },
    {
        'code': 'LIQUID_INCES_V2',
        'name': 'INCES V2',
        'sequence': 22,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# INCES: 0.5% deduction on Utilidades ONLY
# Calculate deduction base (ONLY Utilidades)
deduction_base = (LIQUID_UTILIDADES_V2 or 0)

result = -1 * (deduction_base * 0.005)'''
    },
    {
        'code': 'LIQUID_VACATION_PREPAID_V2',
        'name': 'Vacaciones/Bono Prepagadas (Deducción) V2',
        'sequence': 195,
        'category_id': cat_ded.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Deduct prepaid vacation/bono amount from contract field
# Try to get prepaid amount from contract field
try:
    prepaid_amount = contract.ueipab_vacation_prepaid_amount
    if not prepaid_amount:
        prepaid_amount = 0.0
except:
    prepaid_amount = 0.0

if prepaid_amount > 0:
    # Deduct the actual prepaid amount
    result = -1 * prepaid_amount
else:
    # No prepayment - no deduction
    result = 0.0'''
    },
    {
        'code': 'LIQUID_NET_V2',
        'name': 'Liquidación Neta V2',
        'sequence': 200,
        'category_id': cat_net.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': '''# Net Liquidation = All benefits - Deductions - Prepaid vacation/bono
# Safely get prepaid deduction (may not exist)
try:
    prepaid_deduction = LIQUID_VACATION_PREPAID_V2 or 0
except:
    prepaid_deduction = 0

result = (
    (LIQUID_VACACIONES_V2 or 0) +
    (LIQUID_BONO_VACACIONAL_V2 or 0) +
    (LIQUID_UTILIDADES_V2 or 0) +
    (LIQUID_PRESTACIONES_V2 or 0) +
    (LIQUID_ANTIGUEDAD_V2 or 0) +
    (LIQUID_INTERESES_V2 or 0) +
    (LIQUID_FAOV_V2 or 0) +
    (LIQUID_INCES_V2 or 0) +
    prepaid_deduction
)'''
    },
]

AGUINALDOS_RULE = {
    'code': 'AGUINALDOS',
    'name': 'Aguinaldos (Christmas Bonus)',
    'sequence': 100,
    'category_id': cat_gross.id,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''# Aguinaldos (Christmas Bonus) - V2 FORMULA
# Venezuelan law: Aguinaldos = 2x monthly salary (paid bi-monthly at 50% each)
# V2 Migration: Uses ueipab_salary_v2 (direct salary subject to deductions)

# Get payslip period
period_days = (payslip.date_to - payslip.date_from).days + 1

# Venezuelan bi-monthly logic:
# Period 1-15: 50% of annual Aguinaldos
# Period 16-31: 50% of annual Aguinaldos
if period_days <= 16:
    proportion = 0.5  # Fixed 50% for first half
else:
    # For periods starting after 15th, also use 50%
    day_from = payslip.date_from.day
    if day_from >= 15:
        proportion = 0.5  # Fixed 50% for second half
    else:
        proportion = period_days / 30.0  # Proportional for unusual periods

# V2: Calculate Aguinaldos based on ueipab_salary_v2 (direct salary amount)
# Annual Aguinaldos = 2x monthly salary
# For bi-monthly: split into two payments of 50% each
monthly_salary_v2 = contract.ueipab_salary_v2 or 0.0
base_annual_aguinaldos = monthly_salary_v2 * 2
result = base_annual_aguinaldos * proportion'''
}

# =============================================================================
# CREATE STRUCTURES AND RULES
# =============================================================================

def create_structure_with_rules(code, name, rules_data):
    """Create a salary structure with all its rules."""
    print(f"\nCreating structure: {code}...")

    # Check if structure exists
    structure = Structure.search([('code', '=', code)], limit=1)
    if structure:
        print(f"  ⚠️  Structure {code} already exists (ID: {structure.id})")
        print(f"  Current rules: {len(structure.rule_ids)}")
        # Don't recreate, just update rules if needed
        if len(structure.rule_ids) > 0:
            print(f"  ✅ Skipping - structure has rules")
            return structure
    else:
        structure = Structure.create({
            'name': name,
            'code': code,
        })
        print(f"  ✅ Created structure: {code} (ID: {structure.id})")

    # Create rules and link to structure
    rule_ids = []
    for rule_data in rules_data:
        existing_rule = SalaryRule.search([('code', '=', rule_data['code'])], limit=1)
        if existing_rule:
            print(f"    ⚠️  Rule {rule_data['code']} exists (ID: {existing_rule.id})")
            rule_ids.append(existing_rule.id)
        else:
            rule = SalaryRule.create(rule_data)
            print(f"    ✅ Created rule: {rule_data['code']} (ID: {rule.id})")
            rule_ids.append(rule.id)

    # Link rules to structure
    structure.write({'rule_ids': [(6, 0, rule_ids)]})
    print(f"  ✅ Linked {len(rule_ids)} rules to {code}")

    return structure

# Create VE_PAYROLL_V2
print("\n[2/4] Creating VE_PAYROLL_V2 structure...")
ve_payroll = create_structure_with_rules(
    'VE_PAYROLL_V2',
    'Salarios Venezuela UEIPAB V2',
    VE_PAYROLL_V2_RULES
)

# Create LIQUID_VE_V2
print("\n[3/4] Creating LIQUID_VE_V2 structure...")
liquid_ve = create_structure_with_rules(
    'LIQUID_VE_V2',
    'Liquidación Venezolana V2',
    LIQUID_VE_V2_RULES
)

# Create AGUINALDOS_2025
print("\n[4/4] Creating AGUINALDOS_2025 structure...")
aguinaldos_struct = Structure.search([('code', '=', 'AGUINALDOS_2025')], limit=1)
if not aguinaldos_struct:
    aguinaldos_struct = Structure.create({
        'name': 'Aguinaldos Diciembre 2025',
        'code': 'AGUINALDOS_2025',
    })
    print(f"  ✅ Created structure: AGUINALDOS_2025 (ID: {aguinaldos_struct.id})")
else:
    print(f"  ⚠️  Structure AGUINALDOS_2025 exists (ID: {aguinaldos_struct.id})")

# Create or update AGUINALDOS rule
existing_aguinaldo = SalaryRule.search([('code', '=', 'AGUINALDOS')], limit=1)
if existing_aguinaldo:
    print(f"  ⚠️  AGUINALDOS rule exists (ID: {existing_aguinaldo.id})")
    aguinaldo_rule = existing_aguinaldo
else:
    aguinaldo_rule = SalaryRule.create(AGUINALDOS_RULE)
    print(f"  ✅ Created rule: AGUINALDOS (ID: {aguinaldo_rule.id})")

# Link rule to structure
aguinaldos_struct.write({'rule_ids': [(6, 0, [aguinaldo_rule.id])]})
print(f"  ✅ Linked AGUINALDOS rule to AGUINALDOS_2025 structure")

# =============================================================================
# VERIFICATION
# =============================================================================

print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

for code in ['VE_PAYROLL_V2', 'LIQUID_VE_V2', 'AGUINALDOS_2025']:
    struct = Structure.search([('code', '=', code)], limit=1)
    if struct:
        print(f"\n✅ {code}")
        print(f"   ID: {struct.id}")
        print(f"   Rules: {len(struct.rule_ids)}")
        for r in struct.rule_ids.sorted('sequence')[:3]:
            print(f"     - [{r.sequence:03d}] {r.code}")
        if len(struct.rule_ids) > 3:
            print(f"     ... and {len(struct.rule_ids) - 3} more")
    else:
        print(f"\n❌ {code} - NOT FOUND!")

env.cr.commit()

print("\n" + "="*80)
print("✅ SALARY STRUCTURE CREATION COMPLETE!")
print("="*80)
print("\nNext steps:")
print("1. Create test contracts for 5-10 employees")
print("2. Generate test payslips")
print("3. Validate calculations")
