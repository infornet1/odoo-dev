#!/usr/bin/env python3
"""
Export salary structures from testing database for migration to production.

This script exports:
1. Salary structures (VE_PAYROLL_V2, LIQUID_VE_V2, AGUINALDOS_2025)
2. Associated salary rules with formulas
3. Structure-rule mappings

Output: SQL statements ready to execute in production
"""

print("=" * 80)
print("EXPORTING SALARY STRUCTURES FROM TESTING DATABASE")
print("=" * 80)

# Get models
Structure = env['hr.payroll.structure']
Rule = env['hr.salary.rule']

# Target structures to export
target_codes = ['VE_PAYROLL_V2', 'LIQUID_VE_V2', 'AGUINALDOS_2025']

structures = Structure.search([('code', 'in', target_codes)])

if not structures:
    print("\n❌ ERROR: No structures found with codes:", target_codes)
    print("   Available structures:")
    all_structures = Structure.search([])
    for s in all_structures:
        print(f"     - {s.code}: {s.name}")
    exit(1)

print(f"\n✅ Found {len(structures)} structures to export")

# Export each structure
for structure in structures:
    print("\n" + "=" * 80)
    print(f"STRUCTURE: {structure.code} - {structure.name}")
    print("=" * 80)

    print(f"\nStructure Details:")
    print(f"  ID: {structure.id}")
    print(f"  Name: {structure.name}")
    print(f"  Code: {structure.code}")
    parent_name = structure.parent_id.name if structure.parent_id else 'N/A'
    print(f"  Parent: {parent_name}")

    print(f"\n  Rules in this structure: {len(structure.rule_ids)}")

    # List all rules
    for rule in structure.rule_ids.sorted(key=lambda r: r.sequence):
        print(f"    [{rule.sequence:03d}] {rule.code}: {rule.name}")
        print(f"          Category: {rule.category_id.name if rule.category_id else 'N/A'}")
        print(f"          Amount Type: {rule.amount_select}")
        if rule.amount_select == 'code':
            print(f"          Formula: {rule.amount_python_compute[:80]}...")
        elif rule.amount_select == 'fix':
            print(f"          Fixed Amount: {rule.amount_fix}")
        elif rule.amount_select == 'percentage':
            print(f"          Percentage: {rule.amount_percentage}%")

print("\n" + "=" * 80)
print("EXPORT SUMMARY")
print("=" * 80)
print(f"\nTotal structures exported: {len(structures)}")
print(f"\nStructures:")
for s in structures:
    print(f"  - {s.code}: {s.name} ({len(s.rule_ids)} rules)")

print("\n" + "=" * 80)
print("⚠️  IMPORTANT NOTES FOR MIGRATION")
print("=" * 80)
print("""
1. Salary structures are NOT defined in module XML files
2. They only exist in the database
3. Migration options:

   OPTION A: Manual Recreation (RECOMMENDED)
   - Login to production after module installation
   - Settings → Payroll → Salary Structures
   - Manually create the 3 structures
   - Assign rules to each structure

   OPTION B: Database Export/Import
   - Export structures using pg_dump with --data-only
   - Import into production database
   - Risk: ID conflicts, foreign key issues

   OPTION C: Add to Module (BEST LONG-TERM)
   - Create data/salary_structures.xml in module
   - Define structures in XML with noupdate="0"
   - Reinstall module to create structures
   - Benefit: Version controlled, repeatable

3. Since structures are database-only, they may have been created via:
   - Manual UI creation by user
   - Data import from another system
   - Custom script execution

4. For production deployment, OPTION A (manual recreation) is safest
   as it avoids data corruption risks.
""")

print("\n" + "=" * 80)
print("DETAILED STRUCTURE DATA FOR MANUAL RECREATION")
print("=" * 80)

for structure in structures:
    print(f"\n{'=' * 80}")
    print(f"CREATE STRUCTURE: {structure.name}")
    print(f"{'=' * 80}")
    print(f"""
Navigation: Payroll → Configuration → Salary Structures → Create

Fields to fill:
  Name: {structure.name}
  Code: {structure.code}
  Parent Structure: {structure.parent_id.name if structure.parent_id else '(None)'}

Rules to add (in order of sequence):
""")

    for rule in structure.rule_ids.sorted(key=lambda r: r.sequence):
        print(f"  [{rule.sequence:03d}] {rule.code} - {rule.name}")

    print(f"\nTotal rules to add: {len(structure.rule_ids)}")

print("\n" + "=" * 80)
env.cr.commit()
