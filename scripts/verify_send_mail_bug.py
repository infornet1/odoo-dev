#!/usr/bin/env python3
# Verify the Send Mail button bug

print("=" * 90)
print("SEND MAIL BUTTON BUG - VERIFICATION")
print("=" * 90)

# Find a payslip that was clicked but not sent
print("\nSearching for evidence of the bug...")
print("-" * 90)

# Get payslips marked as sent
payslips_marked_sent = env['hr.payslip'].search([('is_send_mail', '=', True)])

print(f"\nFound {len(payslips_marked_sent)} payslips with is_send_mail = True")
print("\nChecking if emails were actually sent for each...\n")

print(f"{'ID':<8} {'Number':<15} {'is_send_mail':<15} {'Actual Emails':<15} {'Status'}")
print("-" * 90)

bug_count = 0
for slip in payslips_marked_sent[:20]:  # Check first 20
    # Check actual emails sent
    emails = env['mail.mail'].search([
        ('model', '=', 'hr.payslip'),
        ('res_id', '=', slip.id)
    ])

    # Also check mail messages
    messages = env['mail.message'].search([
        ('model', '=', 'hr.payslip'),
        ('res_id', '=', slip.id),
        ('message_type', '=', 'email')
    ])

    total_evidence = len(emails) + len(messages)

    if slip.is_send_mail and total_evidence == 0:
        status = "🔴 BUG!"
        bug_count += 1
    else:
        status = "✅ OK"

    print(f"{slip.id:<8} {slip.number or 'Draft':<15} {str(slip.is_send_mail):<15} {total_evidence:<15} {status}")

print("-" * 90)
print(f"\n🔴 POTENTIAL BUG CASES: {bug_count}")

if bug_count > 0:
    print("\nThese payslips are marked as 'email sent' but have no email records.")
    print("This likely happened when user clicked 'Send Mail' but cancelled the wizard.")

print("\n" + "=" * 90)
print("BUG EXPLANATION")
print("=" * 90)

print("""
The bug occurs in: /addons/hr_payslip_monthly_report/models/hr_payslip.py

Line 59 in action_payslip_send() method:
    self.write({'is_send_mail': True})  # 🔴 TOO EARLY!

EXECUTION FLOW:
--------------
1. User clicks "Send Mail" button
2. Method runs: is_send_mail = True (SAVED TO DATABASE)
3. Button becomes invisible (because invisible="is_send_mail == True")
4. Email wizard opens
5. User clicks CANCEL or DISCARD
6. is_send_mail stays True (but email never sent!)
7. Button never comes back

CORRECT FLOW SHOULD BE:
----------------------
1. User clicks "Send Mail" button
2. Open email wizard (is_send_mail still False)
3. User SENDS email
4. THEN set is_send_mail = True
5. Button hides (correctly - email was actually sent)

THE FIX:
--------
Remove line 59 or move the flag update to AFTER successful send.
The flag should only be set when email is ACTUALLY sent, not when
opening the compose window.
""")

print("\n" + "=" * 90)
print("TO REPRODUCE THE BUG:")
print("=" * 90)
print("""
1. Find a payslip with is_send_mail = False
2. Click the "Send Mail" button
3. Notice the button disappears IMMEDIATELY
4. Cancel/Discard the email wizard
5. Button does not come back!
6. Check is_send_mail field → it's True (even though no email sent)
""")

print("\n" + "=" * 90)
