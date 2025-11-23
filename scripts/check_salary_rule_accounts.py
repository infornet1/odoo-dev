# Check salary rules and their accounting configuration

print("=" * 80)
print("SALARY RULES - ACCOUNTING CONFIGURATION STATUS")
print("=" * 80)

# Get all active salary rules
SalaryRule = env['hr.salary.rule']
rules = SalaryRule.search([])

print(f"\nTotal salary rules found: {len(rules)}")
print("\nRules WITHOUT accounting configuration:")
print("-" * 80)

missing_config = []
for rule in rules:
    if not rule.account_debit_id or not rule.account_credit_id:
        missing_config.append(rule)
        debit = f"{rule.account_debit_id.code} - {rule.account_debit_id.name}" if rule.account_debit_id else "NOT SET"
        credit = f"{rule.account_credit_id.code} - {rule.account_credit_id.name}" if rule.account_credit_id else "NOT SET"
        print(f"  [{rule.code}] {rule.name}")
        print(f"    Debit:  {debit}")
        print(f"    Credit: {credit}")
        print()

print(f"\nTotal rules missing config: {len(missing_config)}")

print("\n" + "=" * 80)
print("Rules WITH accounting configuration:")
print("-" * 80)

configured = 0
for rule in rules:
    if rule.account_debit_id and rule.account_credit_id:
        configured += 1
        print(f"  [{rule.code}] {rule.name}")
        print(f"    Debit:  {rule.account_debit_id.code} - {rule.account_debit_id.name}")
        print(f"    Credit: {rule.account_credit_id.code} - {rule.account_credit_id.name}")
        print()

print(f"Total rules with config: {configured}")
print("=" * 80)
