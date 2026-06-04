NEW_FORMULA = """# Service months: start from previous_liquidation_date if set (net period), otherwise contract.date_start
end_date = payslip.date_to

try:
    prev_liq = contract.ueipab_previous_liquidation_date
    if not prev_liq:
        prev_liq = False
except:
    prev_liq = False

if prev_liq and prev_liq > contract.date_start:
    start_date = prev_liq
else:
    start_date = contract.date_start

days_diff = (end_date - start_date).days
result = days_diff / 30.0"""

rule = env['hr.salary.rule'].browse(51)
print(f"Rule: {rule.code} (id={rule.id})")
rule.write({'amount_python_compute': NEW_FORMULA})
print(f"  -> formula updated")

contract = env['hr.contract'].browse(127)
print(f"Contract: {contract.name}, vacation_prepaid was={contract.ueipab_vacation_prepaid_amount}")
contract.write({'ueipab_vacation_prepaid_amount': 0.0})
print(f"  -> vacation_prepaid cleared to 0")

env.cr.commit()
print("Done — testing env committed.")
