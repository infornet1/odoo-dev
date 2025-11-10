#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script: Consolidate UEIPAB Payroll Modules
Uninstalls old modules and installs new unified ueipab_hr_payroll module
"""

import psycopg2
import sys

# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = 5433
DB_NAME = 'testing'
DB_USER = 'odoo'
DB_PASS = 'odoo'

def execute_query(cursor, query, description):
    """Execute query and print results"""
    print(f"\n{description}")
    print("=" * 60)
    cursor.execute(query)
    if cursor.description:
        results = cursor.fetchall()
        for row in results:
            print(row)
    return results

def main():
    print("=" * 60)
    print("UEIPAB PAYROLL MODULE MIGRATION")
    print("=" * 60)
    print("\nThis script will:")
    print("1. Check current module status")
    print("2. Uninstall old modules (ueipab_hr_contract, ueipab_payroll_enhancements)")
    print("3. Install new unified module (ueipab_hr_payroll)")
    print("\n⚠️  WARNING: This will modify the database.")
    print("    Ensure you have a backup before proceeding!")

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)

    try:
        # Connect to database
        print("\nConnecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.autocommit = False
        cursor = conn.cursor()

        # Step 1: Check current status
        execute_query(
            cursor,
            """
            SELECT name, state, latest_version
            FROM ir_module_module
            WHERE name LIKE 'ueipab%'
            ORDER BY name
            """,
            "Step 1: Current Module Status"
        )

        # Step 2: Mark old modules for uninstallation
        print("\nStep 2: Marking old modules for uninstallation...")

        cursor.execute("""
            UPDATE ir_module_module
            SET state = 'to remove'
            WHERE name IN ('ueipab_hr_contract', 'ueipab_payroll_enhancements')
            AND state = 'installed'
        """)
        print(f"  Marked {cursor.rowcount} modules for removal")

        # Step 3: Mark new module for installation
        print("\nStep 3: Marking new module for installation...")

        cursor.execute("""
            UPDATE ir_module_module
            SET state = 'to install'
            WHERE name = 'ueipab_hr_payroll'
            AND state = 'uninstalled'
        """)

        if cursor.rowcount == 0:
            print("  Module not found in database. Will be detected on module update.")
        else:
            print(f"  Marked {cursor.rowcount} module for installation")

        # Commit changes
        conn.commit()
        print("\n✅ Database changes committed successfully!")

        # Step 4: Show final status
        execute_query(
            cursor,
            """
            SELECT name, state, latest_version
            FROM ir_module_module
            WHERE name LIKE 'ueipab%'
            ORDER BY name
            """,
            "Step 4: Updated Module Status"
        )

        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("\n1. Update module list:")
        print("   docker exec odoo-dev-web odoo -c /etc/odoo/odoo.conf -d testing -u base --stop-after-init")
        print("\n2. Restart Odoo:")
        print("   docker restart odoo-dev-web")
        print("\n3. Access Odoo UI and go to Apps")
        print("   - Remove 'Apps' filter")
        print("   - Old modules should show as 'To Remove'")
        print("   - New module should show as 'To Install' or ready to install")
        print("\n4. Clear browser cache:")
        print("   - Debug mode → Regenerate Assets Bundles")
        print("   - Hard refresh: Ctrl+Shift+R")
        print("\n5. Verify functionality:")
        print("   - Check contract fields")
        print("   - Test payslip generation wizard")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

if __name__ == '__main__':
    main()
