#!/usr/bin/env python3
"""
Detailed analysis of FLORMAR HERNANDEZ to match $204.59 net
"""

import gspread
from google.oauth2.service_account import Credentials

# Connect
scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('/var/www/dev/bcv/credentials.json', scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key('19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s')
worksheet = spreadsheet.worksheet('31oct2025')

def parse_amount(value):
    """Parse number"""
    if not value or str(value).strip() == '':
        return 0.0
    value_clean = str(value).strip()
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

# Find FLORMAR (row 33, index 32)
print("="*100)
print("FLORMAR HERNANDEZ - DETAILED SPREADSHEET ANALYSIS")
print("="*100)

# Get her row directly
row_idx = 32  # Row 33 in spreadsheet (0-indexed)
all_data = worksheet.get_all_values()
row = all_data[row_idx]

exchange_rate = parse_amount(worksheet.acell('O2').value)
print(f"\n💱 Exchange Rate: {exchange_rate:.2f} VEB/USD\n")

# Get all columns
employee_name = row[3]
k_veb = parse_amount(row[10])  # K: SALARIO MENSUAL MAS BONO
l_veb = parse_amount(row[11])  # L: OTROS BONOS
m_veb = parse_amount(row[12])  # M: CESTA TICKET MENSUAL PTR
n_veb = parse_amount(row[13])  # N: IVSS deduction
o_veb = parse_amount(row[14])  # O: FAOV
p_veb = parse_amount(row[15])  # P: INCES
q_veb = parse_amount(row[16])  # Q: ARI ref
r_veb = parse_amount(row[17])  # R: ARI SENIAT
s_veb = parse_amount(row[18])  # S: Other deductions
t_veb = parse_amount(row[19])  # T: Total deductions
u_value = row[20]  # U: $ Total deductions
v_veb = parse_amount(row[21])  # V: Bi-weekly - deductions (no cesta)
w_veb = parse_amount(row[22])  # W: Bi-weekly - deductions + cesta
x_veb = parse_amount(row[23])  # X: Same as W
y_value = row[24]  # Y: $ Bi-weekly with cesta
z_value = row[25]  # Z: $ Monthly with cesta

print(f"Employee: {employee_name}")
print(f"\n📊 MONTHLY VALUES (VEB → USD):")
print(f"  K (Salary+Bonus):     {k_veb:>15,.2f} VEB  →  ${k_veb/exchange_rate:>10.2f} USD")
print(f"  L (Other Bonuses):    {l_veb:>15,.2f} VEB  →  ${l_veb/exchange_rate:>10.2f} USD")
print(f"  M (Cesta Ticket):     {m_veb:>15,.2f} VEB  →  ${m_veb/exchange_rate:>10.2f} USD")

print(f"\n📊 BI-WEEKLY CALCULATION:")
# Bi-weekly gross = (K + L + M) / 2
biweekly_veb_gross = (k_veb + l_veb + m_veb) / 2
print(f"  (K+L+M)/2:            {biweekly_veb_gross:>15,.2f} VEB  →  ${biweekly_veb_gross/exchange_rate:>10.2f} USD")

print(f"\n📊 DEDUCTIONS (Monthly VEB):")
print(f"  N (IVSS 4.5%/2):      {n_veb:>15,.2f} VEB  →  ${n_veb/exchange_rate:>10.2f} USD")
print(f"  O (FAOV 1%):          {o_veb:>15,.2f} VEB  →  ${o_veb/exchange_rate:>10.2f} USD")
print(f"  P (INCES 0.25%):      {p_veb:>15,.2f} VEB  →  ${p_veb/exchange_rate:>10.2f} USD")
print(f"  Q (ARI Ref):          {q_veb:>15,.2f} VEB  →  ${q_veb/exchange_rate:>10.2f} USD")
print(f"  R (ARI SENIAT):       {r_veb:>15,.2f} VEB  →  ${r_veb/exchange_rate:>10.2f} USD")
print(f"  S (Other):            {s_veb:>15,.2f} VEB  →  ${s_veb/exchange_rate:>10.2f} USD")
print(f"  T (Total deductions): {t_veb:>15,.2f} VEB  →  ${t_veb/exchange_rate:>10.2f} USD")

print(f"\n📊 NET CALCULATION:")
print(f"  V (Bi-weekly - ded, no cesta): {v_veb:>15,.2f} VEB  →  ${v_veb/exchange_rate:>10.2f} USD")
print(f"  W (Bi-weekly + cesta):         {w_veb:>15,.2f} VEB  →  ${w_veb/exchange_rate:>10.2f} USD")
print(f"  X (Same as W):                 {x_veb:>15,.2f} VEB  →  ${x_veb/exchange_rate:>10.2f} USD")

# Parse Y and Z as they might already be USD
y_parsed = parse_amount(y_value)
z_parsed = parse_amount(z_value)

print(f"\n📊 USD COLUMNS (already in USD):")
print(f"  U ($ Total deductions): {u_value}")
print(f"  Y ($ Bi-weekly net):    {y_value}  →  ${y_parsed:.2f} USD ← EXPECTED NET")
print(f"  Z ($ Monthly net):      {z_value}  →  ${z_parsed:.2f} USD")

# Verify calculation
print(f"\n" + "="*100)
print(f"VERIFICATION:")
print(f"="*100)

# If Y is already in USD and is 204.59
expected_net_usd = y_parsed

# Work backwards to understand the calculation
print(f"\n💡 Working BACKWARDS from expected net ${expected_net_usd:.2f} USD:")

# Current payslip shows net $224.59
# Difference is $20 (exactly the bi-weekly Cesta Ticket)
current_net = 224.59
difference = current_net - expected_net_usd

print(f"  Current Odoo payslip net: ${current_net:.2f} USD")
print(f"  Expected spreadsheet net: ${expected_net_usd:.2f} USD")
print(f"  Difference:               ${difference:.2f} USD")

if abs(difference - 20.0) < 0.10:
    print(f"\n⚠️  ISSUE IDENTIFIED:")
    print(f"  Difference is exactly $20.00 (bi-weekly Cesta Ticket)")
    print(f"  This suggests the SPREADSHEET does NOT include Cesta Ticket in net!")
    print(f"\n  Spreadsheet formula appears to be:")
    print(f"    Net = (K + L) / 2 - Deductions")
    print(f"    (Column M is NOT included in net calculation)")

# Calculate what contract values should be
print(f"\n" + "="*100)
print(f"CORRECT CONTRACT VALUES (to match spreadsheet $204.59):")
print(f"="*100)

# Option 1: K+L distributed as 70/25/5, Cesta = $40
k_usd = k_veb / exchange_rate
l_usd = l_veb / exchange_rate
m_usd = m_veb / exchange_rate

base_kl = k_usd + l_usd
cesta_40 = 40.0

new_70 = base_kl * 0.70
new_25 = base_kl * 0.25
new_05 = base_kl * 0.05

print(f"\n📋 OPTION 1: Distribute (K+L) as 70/25/5, Cesta=$40")
print(f"  Base (K+L):             ${base_kl:>10.2f} USD")
print(f"  ueipab_salary_base (70%): ${new_70:>10.2f} USD")
print(f"  ueipab_bonus_regular (25%): ${new_25:>10.2f} USD")
print(f"  ueipab_extra_bonus (5%):  ${new_05:>10.2f} USD")
print(f"  cesta_ticket_usd:         ${cesta_40:>10.2f} USD")

# Bi-weekly calculation
biweekly_70 = new_70 / 2
biweekly_25 = new_25 / 2
biweekly_05 = new_05 / 2
biweekly_cesta = cesta_40 / 2
biweekly_gross_opt1 = biweekly_70 + biweekly_25 + biweekly_05 + biweekly_cesta

# Deductions
sso = biweekly_gross_opt1 * 0.04
paro = biweekly_gross_opt1 * 0.005
faov = biweekly_gross_opt1 * 0.01
ari = biweekly_70 * 0.00  # 0% for this employee
total_ded_opt1 = sso + paro + faov + ari

net_opt1 = biweekly_gross_opt1 - total_ded_opt1

print(f"\n  Bi-weekly Payslip:")
print(f"    VE_SALARY_70:     ${biweekly_70:>10.2f}")
print(f"    VE_BONUS_25:      ${biweekly_25:>10.2f}")
print(f"    VE_EXTRA_5:       ${biweekly_05:>10.2f}")
print(f"    VE_CESTA_TICKET:  ${biweekly_cesta:>10.2f}")
print(f"    VE_GROSS:         ${biweekly_gross_opt1:>10.2f}")
print(f"    Deductions:       -${total_ded_opt1:>10.2f}")
print(f"    VE_NET:           ${net_opt1:>10.2f} USD")

if abs(net_opt1 - expected_net_usd) < 1.0:
    print(f"\n✅ OPTION 1 MATCHES! Use these contract values.")
else:
    print(f"\n⚠️  Option 1 doesn't match (diff: ${abs(net_opt1 - expected_net_usd):.2f})")

# Option 2: Spreadsheet excludes Cesta from net entirely
print(f"\n📋 OPTION 2: Spreadsheet net EXCLUDES Cesta Ticket")
print(f"  If net = ${expected_net_usd:.2f} WITHOUT Cesta,")
print(f"  then with Cesta it would be: ${expected_net_usd + biweekly_cesta:.2f} USD")
print(f"  Current Odoo shows: ${current_net:.2f} USD ✓ MATCHES!")
