#!/usr/bin/env python3
"""
Check FLORMAR HERNANDEZ data from spreadsheet
Verify expected net take home of $204.59
"""

import gspread
from google.oauth2.service_account import Credentials

# Connect to spreadsheet
scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('/var/www/dev/bcv/credentials.json', scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key('19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s')
worksheet = spreadsheet.worksheet('31oct2025')

# Get all data
all_data = worksheet.get_all_values()

# Find FLORMAR HERNANDEZ
print("="*100)
print("FLORMAR HERNANDEZ - SPREADSHEET ANALYSIS")
print("="*100)

def parse_amount(value):
    """Parse Venezuelan number format"""
    if not value or value.strip() == '':
        return 0.0
    value_clean = value.strip()
    dot_count = value_clean.count('.')
    comma_count = value_clean.count(',')

    if dot_count > 0 and comma_count > 0:
        last_dot_pos = value_clean.rfind('.')
        last_comma_pos = value_clean.rfind(',')
        if last_dot_pos > last_comma_pos:
            value_clean = value_clean.replace(',', '')
        else:
            value_clean = value_clean.replace('.', '').replace(',', '.')
    elif dot_count > 1:
        value_clean = value_clean.replace('.', '')
    elif comma_count > 1:
        value_clean = value_clean.replace(',', '')
    elif comma_count == 1 and dot_count == 0:
        value_clean = value_clean.replace(',', '.')

    try:
        return float(value_clean)
    except ValueError:
        return 0.0

# Get exchange rate from O2
exchange_rate = parse_amount(worksheet.acell('O2').value)
print(f"\n💱 Exchange Rate: {exchange_rate:.2f} VEB/USD\n")

# Get column headers
headers = all_data[3]
print(f"📋 Column Headers:")
for idx, header in enumerate(headers[:30]):
    col_letter = chr(65 + idx)
    if header:
        print(f"  {col_letter}: {header}")

# Find FLORMAR
for row_idx in range(4, len(all_data)):
    row = all_data[row_idx]
    employee_name = row[3].strip().upper() if len(row) > 3 else ""

    if 'FLORMAR' in employee_name:
        print(f"\n" + "="*100)
        print(f"FOUND: {employee_name} (Row {row_idx + 1})")
        print("="*100)

        # Get all relevant columns
        # K=10, L=11, M=12, N=13, O=14, P=15, Q=16, R=17, S=18, T=19, U=20, V=21, W=22, X=23, Y=24, Z=25
        k_veb = parse_amount(row[10]) if len(row) > 10 else 0.0  # K: SALARIO MENSUAL MAS BONO
        l_veb = parse_amount(row[11]) if len(row) > 11 else 0.0  # L: OTROS BONOS
        m_veb = parse_amount(row[12]) if len(row) > 12 else 0.0  # M: CESTA TICKET MENSUAL PTR
        n_veb = parse_amount(row[13]) if len(row) > 13 else 0.0  # N
        o_veb = parse_amount(row[14]) if len(row) > 14 else 0.0  # O
        p_veb = parse_amount(row[15]) if len(row) > 15 else 0.0  # P
        q_veb = parse_amount(row[16]) if len(row) > 16 else 0.0  # Q
        r_veb = parse_amount(row[17]) if len(row) > 17 else 0.0  # R
        s_veb = parse_amount(row[18]) if len(row) > 18 else 0.0  # S
        t_veb = parse_amount(row[19]) if len(row) > 19 else 0.0  # T
        u_veb = parse_amount(row[20]) if len(row) > 20 else 0.0  # U
        v_veb = parse_amount(row[21]) if len(row) > 21 else 0.0  # V
        w_veb = parse_amount(row[22]) if len(row) > 22 else 0.0  # W
        x_veb = parse_amount(row[23]) if len(row) > 23 else 0.0  # X
        y_veb = parse_amount(row[24]) if len(row) > 24 else 0.0  # Y
        z_veb = parse_amount(row[25]) if len(row) > 25 else 0.0  # Z
        aa_veb = parse_amount(row[26]) if len(row) > 26 else 0.0 # AA
        ab_veb = parse_amount(row[27]) if len(row) > 27 else 0.0 # AB
        ac_veb = parse_amount(row[28]) if len(row) > 28 else 0.0 # AC

        # Convert to USD
        k_usd = k_veb / exchange_rate
        l_usd = l_veb / exchange_rate
        m_usd = m_veb / exchange_rate
        y_usd = y_veb / exchange_rate

        print(f"\n📊 RAW SPREADSHEET VALUES (VEB):")
        print(f"  K (Salario Mensual):      {k_veb:>15,.2f} VEB = ${k_usd:>10.2f} USD")
        print(f"  L (Otros Bonos):          {l_veb:>15,.2f} VEB = ${l_usd:>10.2f} USD")
        print(f"  M (Cesta Ticket Mensual): {m_veb:>15,.2f} VEB = ${m_usd:>10.2f} USD")
        print(f"  N: {n_veb:>15,.2f} VEB")
        print(f"  O: {o_veb:>15,.2f} VEB")
        print(f"  P: {p_veb:>15,.2f} VEB")
        print(f"  Q: {q_veb:>15,.2f} VEB")
        print(f"  R: {r_veb:>15,.2f} VEB")
        print(f"  S: {s_veb:>15,.2f} VEB")
        print(f"  T: {t_veb:>15,.2f} VEB")
        print(f"  U: {u_veb:>15,.2f} VEB")
        print(f"  V: {v_veb:>15,.2f} VEB")
        print(f"  W: {w_veb:>15,.2f} VEB")
        print(f"  X: {x_veb:>15,.2f} VEB")
        print(f"  Y (Bi-weekly Gross?):     {y_veb:>15,.2f} VEB = ${y_usd:>10.2f} USD")
        print(f"  Z: {z_veb:>15,.2f} VEB")
        print(f"  AA: {aa_veb:>15,.2f} VEB")
        print(f"  AB: {ab_veb:>15,.2f} VEB")
        print(f"  AC: {ac_veb:>15,.2f} VEB")

        # Calculate bi-weekly amounts (50%)
        k_biweekly = k_usd / 2
        l_biweekly = l_usd / 2
        m_biweekly = m_usd / 2

        print(f"\n📊 BI-WEEKLY AMOUNTS (50% of monthly):")
        print(f"  K bi-weekly: ${k_biweekly:>10.2f} USD")
        print(f"  L bi-weekly: ${l_biweekly:>10.2f} USD")
        print(f"  M bi-weekly: ${m_biweekly:>10.2f} USD")

        # Current contract values
        print(f"\n📋 CURRENT CONTRACT VALUES (from SLIP/099):")
        print(f"  ueipab_salary_base:   $204.94 USD")
        print(f"  ueipab_bonus_regular: $216.03 USD")
        print(f"  ueipab_extra_bonus:   $  0.00 USD")
        print(f"  cesta_ticket_usd:     $ 40.00 USD")

        # Calculate what contract should be with $40 Cesta Ticket
        print(f"\n" + "="*100)
        print(f"REBALANCING SCENARIO: Cesta Ticket = $40 USD")
        print("="*100)

        # If Cesta Ticket should be $40, then:
        # The remaining compensation needs to be distributed as 70/25/5
        # Total compensation = K + L + M
        # New system: Base (70%/25%/5%) + $40 Cesta
        # Base = (K + L + M - $40)

        total_comp = k_usd + l_usd + m_usd
        cesta_fixed = 40.0
        new_base = total_comp - cesta_fixed

        new_70 = new_base * 0.70
        new_25 = new_base * 0.25
        new_05 = new_base * 0.05

        print(f"\n💡 Calculation:")
        print(f"  Total Monthly Compensation (K+L+M): ${total_comp:>10.2f} USD")
        print(f"  Fixed Cesta Ticket:                 ${cesta_fixed:>10.2f} USD")
        print(f"  New Base (Total - $40):             ${new_base:>10.2f} USD")
        print(f"\n  New Distribution:")
        print(f"    ueipab_salary_base (70%):   ${new_70:>10.2f} USD")
        print(f"    ueipab_bonus_regular (25%): ${new_25:>10.2f} USD")
        print(f"    ueipab_extra_bonus (5%):    ${new_05:>10.2f} USD")
        print(f"    cesta_ticket_usd:           ${cesta_fixed:>10.2f} USD")
        print(f"  TOTAL:                        ${new_70 + new_25 + new_05 + cesta_fixed:>10.2f} USD")

        # Bi-weekly calculation
        print(f"\n📊 BI-WEEKLY PAYSLIP (50% of monthly):")
        biweekly_70 = new_70 / 2
        biweekly_25 = new_25 / 2
        biweekly_05 = new_05 / 2
        biweekly_cesta = cesta_fixed / 2
        biweekly_gross = biweekly_70 + biweekly_25 + biweekly_05 + biweekly_cesta

        print(f"  VE_SALARY_70:     ${biweekly_70:>10.2f} USD")
        print(f"  VE_BONUS_25:      ${biweekly_25:>10.2f} USD")
        print(f"  VE_EXTRA_5:       ${biweekly_05:>10.2f} USD")
        print(f"  VE_CESTA_TICKET:  ${biweekly_cesta:>10.2f} USD")
        print(f"  VE_GROSS:         ${biweekly_gross:>10.2f} USD")

        # Deductions (standard rates)
        sso_ded = biweekly_gross * 0.04  # 4%
        paro_ded = biweekly_gross * 0.005  # 0.5%
        faov_ded = biweekly_gross * 0.01  # 1%
        ari_ded = biweekly_70 * 0.01  # 1% of base only (typical)
        total_ded = sso_ded + paro_ded + faov_ded + ari_ded

        print(f"\n  DEDUCTIONS:")
        print(f"    VE_SSO_DED (4%):    -${sso_ded:>10.2f} USD")
        print(f"    VE_PARO_DED (0.5%): -${paro_ded:>10.2f} USD")
        print(f"    VE_FAOV_DED (1%):   -${faov_ded:>10.2f} USD")
        print(f"    VE_ARI_DED (1% K):  -${ari_ded:>10.2f} USD")
        print(f"    TOTAL DEDUCTIONS:   -${total_ded:>10.2f} USD")

        net_take_home = biweekly_gross - total_ded
        print(f"\n  VE_NET (Take Home): ${net_take_home:>10.2f} USD")

        print(f"\n" + "="*100)
        print(f"EXPECTED vs ACTUAL:")
        print(f"  Expected Net (from spreadsheet): $204.59 USD")
        print(f"  Calculated Net:                  ${net_take_home:.2f} USD")
        print(f"  Difference:                      ${abs(204.59 - net_take_home):.2f} USD")

        if abs(204.59 - net_take_home) < 1.0:
            print(f"\n✅ MATCH! (within $1.00)")
        else:
            print(f"\n⚠️  MISMATCH - Need to check spreadsheet formula in Column Y")
            print(f"\n📋 Let me check Column Y formula...")
            print(f"   Y (Spreadsheet bi-weekly): ${y_usd:.2f} USD")
            print(f"   Our calculated gross:      ${biweekly_gross:.2f} USD")

        break
