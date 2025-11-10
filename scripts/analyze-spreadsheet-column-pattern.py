#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze spreadsheet column pattern to understand K, L, M, N relationship
Check multiple employees to determine correct mapping
"""

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'
TARGET_SHEET = '31oct2025'

def parse_veb(value_str):
    """Parse VEB value with thousands separator"""
    if not value_str or value_str.strip() == '':
        return 0.0
    # Remove comma (thousands separator), keep period (decimal point)
    clean = value_str.strip().replace(',', '')
    try:
        return float(clean)
    except:
        return 0.0

def main():
    print("=" * 80)
    print("ANALYZING SPREADSHEET COLUMN PATTERN")
    print("=" * 80)

    # Connect to Google Sheets
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(TARGET_SHEET)
        print(f"✓ Connected to: {spreadsheet.title}")
        print(f"✓ Worksheet: {TARGET_SHEET}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    # Get exchange rate from O2
    try:
        exchange_rate_str = worksheet.acell('O2').value
        exchange_rate = parse_veb(exchange_rate_str)
        print(f"\n✓ Exchange Rate (O2): {exchange_rate:.2f} VEB/USD")
    except Exception as e:
        print(f"✗ Could not get exchange rate: {e}")
        exchange_rate = 219.87

    # Get all data
    all_data = worksheet.get_all_values()

    # Print header row
    if len(all_data) > 4:
        header = all_data[4]  # Row 5 (index 4)
        print(f"\nColumn Headers (Row 5):")
        print(f"  K (10): {header[10] if len(header) > 10 else 'N/A'}")
        print(f"  L (11): {header[11] if len(header) > 11 else 'N/A'}")
        print(f"  M (12): {header[12] if len(header) > 12 else 'N/A'}")
        print(f"  N (13): {header[13] if len(header) > 13 else 'N/A'}")
        print(f"  Z (25): {header[25] if len(header) > 25 else 'N/A'}")

    print("\n" + "=" * 80)
    print("ANALYZING FIRST 10 EMPLOYEES")
    print("=" * 80)

    # Analyze first 10 employees (rows 5-14, indices 4-13)
    for row_idx in range(5, min(15, len(all_data))):
        row = all_data[row_idx]

        if len(row) < 26:
            continue

        emp_name = row[3].strip() if len(row) > 3 else "Unknown"

        # Parse values
        k_veb = parse_veb(row[10])
        l_veb = parse_veb(row[11])
        m_veb = parse_veb(row[12])
        n_veb = parse_veb(row[13])
        z_value = parse_veb(row[25])

        # Convert to USD
        k_usd = k_veb / exchange_rate if exchange_rate > 0 else 0
        l_usd = l_veb / exchange_rate if exchange_rate > 0 else 0
        m_usd = m_veb / exchange_rate if exchange_rate > 0 else 0
        n_usd = n_veb / exchange_rate if exchange_rate > 0 else 0

        # Calculate totals
        lmn_total_veb = l_veb + m_veb + n_veb
        lmn_total_usd = l_usd + m_usd + n_usd
        klmn_total_veb = k_veb + l_veb + m_veb + n_veb
        klmn_total_usd = k_usd + l_usd + m_usd + n_usd

        # Check relationships
        k_matches_lmn = abs(k_veb - lmn_total_veb) < 100  # Within 100 VEB

        print(f"\nEmployee: {emp_name}")
        print(f"  K: {k_veb:>12,.2f} VEB = ${k_usd:>8.2f} USD")
        print(f"  L: {l_veb:>12,.2f} VEB = ${l_usd:>8.2f} USD")
        print(f"  M: {m_veb:>12,.2f} VEB = ${m_usd:>8.2f} USD")
        print(f"  N: {n_veb:>12,.2f} VEB = ${n_usd:>8.2f} USD")
        print(f"  " + "-" * 50)
        print(f"  L+M+N:     {lmn_total_veb:>12,.2f} VEB = ${lmn_total_usd:>8.2f} USD")
        print(f"  K+L+M+N:   {klmn_total_veb:>12,.2f} VEB = ${klmn_total_usd:>8.2f} USD")
        print(f"  Z (NET):   {'':>12} USD = ${z_value:>8.2f} USD")

        # Analysis
        if k_matches_lmn:
            print(f"  ✓ K ≈ L+M+N (K is sum of components)")
        else:
            print(f"  ✗ K ≠ L+M+N (K: {k_veb:.2f}, L+M+N: {lmn_total_veb:.2f}, Diff: {abs(k_veb - lmn_total_veb):.2f})")

        # Check if L, M, N represent percentages of K
        if k_veb > 0:
            l_pct = (l_veb / k_veb) * 100 if k_veb > 0 else 0
            m_pct = (m_veb / k_veb) * 100 if k_veb > 0 else 0
            n_pct = (n_veb / k_veb) * 100 if k_veb > 0 else 0
            print(f"  Percentages of K: L={l_pct:.1f}%, M={m_pct:.1f}%, N={n_pct:.1f}%")

    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    print("\nChecking if K = L+M+N pattern holds for all employees...")
    matches = 0
    total_checked = 0

    for row_idx in range(5, min(50, len(all_data))):
        row = all_data[row_idx]
        if len(row) < 14:
            continue

        k_veb = parse_veb(row[10])
        l_veb = parse_veb(row[11])
        m_veb = parse_veb(row[12])
        n_veb = parse_veb(row[13])

        if k_veb == 0:
            continue

        total_checked += 1
        lmn_sum = l_veb + m_veb + n_veb

        if abs(k_veb - lmn_sum) < 100:
            matches += 1

    print(f"\nPattern Check: {matches}/{total_checked} employees have K ≈ L+M+N")

    if matches > total_checked * 0.8:
        print("\n✓ CONCLUSION: K appears to be the SUM of L+M+N")
        print("  Recommended mapping:")
        print("    ueipab_salary_base   = Column L / exchange_rate")
        print("    ueipab_bonus_regular = Column M / exchange_rate")
        print("    ueipab_extra_bonus   = Column N / exchange_rate")
    else:
        print("\n? CONCLUSION: Relationship unclear, needs manual review")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
