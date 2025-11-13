#!/usr/bin/env python3
"""
Simulate Monica Mosqueda Liquidation Using Current Formulas
Compare with actual amounts paid to identify discrepancies
"""

from datetime import date

# Monica's data (from spreadsheet analysis)
MONICA_DATA = {
    'name': 'Monica del Valle Mosqueda Marcano',
    'hire_date': date(2024, 9, 1),
    'termination_date': date(2025, 7, 31),
    'monthly_salary_bs': 17011.01,
    'exchange_rate': 149.46,  # Bs per USD

    # Actual amounts paid (in USD)
    'actual_payments': {
        'vacaciones': 52.11,  # 13.75 days × $3.79
        'bono_vacacional': 52.11,  # 13.75 days × $3.79
        'utilidades': 104.23,  # 27.50 days × $3.79
        'prestaciones': 236.50,  # 55.00 days × $4.30
        'antiguedad': 0.00,  # Not paid in this case
        'intereses': 0.79,  # 117.89 Bs
        'faov_deduction': -1.04,  # -155.93 Bs
        'inces_deduction': -0.52,  # -77.97 Bs
        'net_total': 444.18,  # Total before subtracting pre-paid
        'pre_paid_deduction': -104.26,  # Vacaciones+Bono+Utilidades paid separately
        'final_net': 339.92
    }
}

def calculate_service_months(start_date, end_date):
    """Calculate service months"""
    days_diff = (end_date - start_date).days
    return days_diff / 30.0

def calculate_current_formula(contract_base_usd):
    """Simulate current formula calculations"""

    # Service calculation
    service_months = calculate_service_months(
        MONICA_DATA['hire_date'],
        MONICA_DATA['termination_date']
    )

    # Base calculations
    daily_salary = contract_base_usd / 30.0

    # Integral salary (base + utilidades proportion + bono proportion)
    utilidades_daily = daily_salary * (60.0 / 360.0)
    bono_vac_daily = daily_salary * (15.0 / 360.0)
    integral_daily = daily_salary + utilidades_daily + bono_vac_daily

    # Vacaciones (15 days/year proportional)
    if service_months < 12:
        vacation_days = (service_months / 12.0) * 15.0
    else:
        years = service_months / 12.0
        vacation_days = years * 15.0
    vacaciones = vacation_days * daily_salary

    # Bono Vacacional (7 days/year for first year - WRONG!)
    if service_months < 12:
        bonus_days = (service_months / 12.0) * 7.0  # ❌ Should be 15
    else:
        years = service_months / 12.0
        if years >= 5:
            bonus_days = 14.0
        else:
            bonus_days = 7.0 + (years * 1.4)
    bono_vacacional = bonus_days * daily_salary

    # Utilidades (15 days/year - WRONG, should be 30)
    if service_months < 12:
        utilidades_days = (service_months / 12.0) * 15.0  # ❌ Should be 30
    else:
        utilidades_days = 15.0
    utilidades = utilidades_days * daily_salary

    # Prestaciones (5 days first 3 months + 2 days/month - WRONG!)
    if service_months <= 3:
        prestaciones_days = service_months * 5
    else:
        first_period = 3 * 5  # 15 days
        remaining_months = service_months - 3
        second_period = remaining_months * 2
        prestaciones_days = first_period + second_period
    prestaciones = prestaciones_days * integral_daily

    # Antiguedad (2 days/month after 3 months)
    if service_months < 3:
        antiguedad_days = 0.0
    else:
        antiguedad_days = service_months * 2
    antiguedad = antiguedad_days * integral_daily

    # Intereses (simple average balance × 13% × months/12)
    average_balance = prestaciones * 0.5
    annual_rate = 0.13
    interest_fraction = service_months / 12.0
    intereses = average_balance * annual_rate * interest_fraction

    # Gross total
    gross_total = (vacaciones + bono_vacacional + utilidades +
                   prestaciones + antiguedad + intereses)

    # Deductions (WRONG - applied to gross, should be only to vac+bono+util)
    faov_deduction = -1 * (gross_total * 0.01)
    inces_deduction = -1 * (gross_total * 0.005)

    # Net total
    net_total = gross_total + faov_deduction + inces_deduction

    return {
        'service_months': service_months,
        'daily_salary': daily_salary,
        'integral_daily': integral_daily,
        'vacation_days': vacation_days,
        'vacaciones': vacaciones,
        'bonus_days': bonus_days,
        'bono_vacacional': bono_vacacional,
        'utilidades_days': utilidades_days,
        'utilidades': utilidades,
        'prestaciones_days': prestaciones_days,
        'prestaciones': prestaciones,
        'antiguedad_days': antiguedad_days,
        'antiguedad': antiguedad,
        'intereses': intereses,
        'gross_total': gross_total,
        'faov_deduction': faov_deduction,
        'inces_deduction': inces_deduction,
        'net_total': net_total
    }

def print_comparison():
    """Print comparison between current formula and actual payments"""

    # Calculate contract base in USD
    contract_base_usd = MONICA_DATA['monthly_salary_bs'] / MONICA_DATA['exchange_rate']

    print("="*80)
    print("MONICA MOSQUEDA LIQUIDATION - FORMULA SIMULATION vs ACTUAL")
    print("="*80)
    print()

    print(f"Employee: {MONICA_DATA['name']}")
    print(f"Hire Date: {MONICA_DATA['hire_date']}")
    print(f"Termination Date: {MONICA_DATA['termination_date']}")
    print(f"Monthly Salary: {MONICA_DATA['monthly_salary_bs']:,.2f} Bs")
    print(f"Exchange Rate: {MONICA_DATA['exchange_rate']:.2f} Bs/USD")
    print(f"Contract Base (USD): ${contract_base_usd:.2f}")
    print()

    # Calculate using current formulas
    calculated = calculate_current_formula(contract_base_usd)

    print("-"*80)
    print("COMPARISON TABLE")
    print("-"*80)
    print(f"{'Concept':<30} {'Days':<10} {'Our Formula':<15} {'Actual Paid':<15} {'Variance':<15}")
    print("-"*80)

    # Service months
    print(f"{'Service Months':<30} {'-':<10} {calculated['service_months']:<15.2f} "
          f"{10.93:<15.2f} {'✅':<15}")

    # Daily rates
    print(f"{'Daily Base Salary':<30} {'-':<10} ${calculated['daily_salary']:<14.2f} "
          f"${3.79:<14.2f} {'✅':<15}")
    print(f"{'Integral Daily Salary':<30} {'-':<10} ${calculated['integral_daily']:<14.2f} "
          f"${4.30:<14.2f} {'⚠️ -6%':<15}")

    print()

    # Vacaciones
    var = ((calculated['vacaciones'] / MONICA_DATA['actual_payments']['vacaciones']) - 1) * 100
    status = '✅' if abs(var) < 5 else '⚠️'
    print(f"{'Vacaciones':<30} {calculated['vacation_days']:<10.2f} "
          f"${calculated['vacaciones']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['vacaciones']:<14.2f} "
          f"{status} {var:+.1f}%")

    # Bono Vacacional
    var = ((calculated['bono_vacacional'] / MONICA_DATA['actual_payments']['bono_vacacional']) - 1) * 100
    print(f"{'Bono Vacacional':<30} {calculated['bonus_days']:<10.2f} "
          f"${calculated['bono_vacacional']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['bono_vacacional']:<14.2f} "
          f"🔴 {var:+.1f}%")

    # Utilidades
    var = ((calculated['utilidades'] / MONICA_DATA['actual_payments']['utilidades']) - 1) * 100
    print(f"{'Utilidades':<30} {calculated['utilidades_days']:<10.2f} "
          f"${calculated['utilidades']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['utilidades']:<14.2f} "
          f"🔴 {var:+.1f}%")

    # Prestaciones
    var = ((calculated['prestaciones'] / MONICA_DATA['actual_payments']['prestaciones']) - 1) * 100
    print(f"{'Prestaciones':<30} {calculated['prestaciones_days']:<10.2f} "
          f"${calculated['prestaciones']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['prestaciones']:<14.2f} "
          f"🔴 {var:+.1f}%")

    # Antiguedad
    if MONICA_DATA['actual_payments']['antiguedad'] > 0:
        var = ((calculated['antiguedad'] / MONICA_DATA['actual_payments']['antiguedad']) - 1) * 100
        status = f"{var:+.1f}%"
    else:
        status = "N/A (not paid)"
    print(f"{'Antiguedad':<30} {calculated['antiguedad_days']:<10.2f} "
          f"${calculated['antiguedad']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['antiguedad']:<14.2f} "
          f"{status}")

    # Intereses
    var = ((calculated['intereses'] / MONICA_DATA['actual_payments']['intereses']) - 1) * 100
    print(f"{'Intereses':<30} {'-':<10} "
          f"${calculated['intereses']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['intereses']:<14.2f} "
          f"⚠️ {var:+.1f}%")

    print("-"*80)
    print(f"{'GROSS TOTAL':<30} {'-':<10} ${calculated['gross_total']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['net_total']:<14.2f}")
    print()

    # Deductions
    print(f"{'FAOV (1%)':<30} {'-':<10} ${calculated['faov_deduction']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['faov_deduction']:<14.2f} 🔴 Wrong base")
    print(f"{'INCES (0.5%)':<30} {'-':<10} ${calculated['inces_deduction']:<14.2f} "
          f"${MONICA_DATA['actual_payments']['inces_deduction']:<14.2f} 🔴 Wrong base")

    print("-"*80)

    # Calculate correct deductions
    correct_deduction_base = (MONICA_DATA['actual_payments']['vacaciones'] +
                             MONICA_DATA['actual_payments']['bono_vacacional'] +
                             MONICA_DATA['actual_payments']['utilidades'])
    correct_faov = -1 * (correct_deduction_base * 0.01)
    correct_inces = -1 * (correct_deduction_base * 0.005)

    # Adjust net total with correct deductions
    adjusted_net = (calculated['vacaciones'] + calculated['bono_vacacional'] +
                   calculated['utilidades'] + calculated['prestaciones'] +
                   calculated['antiguedad'] + calculated['intereses'] +
                   correct_faov + correct_inces)

    print(f"{'NET TOTAL (our formula)':<30} {'-':<10} ${calculated['net_total']:<14.2f}")
    print(f"{'NET TOTAL (corrected deduc.)':<30} {'-':<10} ${adjusted_net:<14.2f}")
    print(f"{'NET TOTAL (actual paid)':<30} {'-':<10} "
          f"${MONICA_DATA['actual_payments']['final_net']:<14.2f}")

    underpayment = MONICA_DATA['actual_payments']['final_net'] - adjusted_net
    underpayment_pct = (underpayment / MONICA_DATA['actual_payments']['final_net']) * 100

    print()
    print("="*80)
    print(f"🔴 TOTAL UNDERPAYMENT BY OUR FORMULA: ${underpayment:.2f} USD ({underpayment_pct:.1f}%)")
    print("="*80)
    print()

    # Summary of issues
    print("CRITICAL ISSUES IDENTIFIED:")
    print()
    print("1. 🔴 Bono Vacacional: Using 7 days/year, should be 15 days minimum (-54%)")
    print("2. 🔴 Utilidades: Using 15 days/year, actual payment 30 days (-50%)")
    print("3. 🔴 Prestaciones: Using ~31 days, should be 55 days quarterly (-44%)")
    print("4. 🔴 Deductions: Applied to gross total, should only apply to vac+bono+util")
    print("5. ⚠️  Intereses: Simple calculation differs from quarterly compounding")
    print()

if __name__ == '__main__':
    print_comparison()
