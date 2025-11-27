# -*- coding: utf-8 -*-
"""
Smart Invoice Confirmation Script with Credit Application & Discount Pricing

Business Rules:
- Regular fee: $197.38 per student
- Discount fee: $162.39 per student (for customers with outstanding credits >= $34.99)
- Process:
  1. Check if customer has outstanding credits
  2. If credits >= $34.99, apply discount by changing unit price to $162.39
  3. Confirm the invoice
  4. Apply available credits to the confirmed invoice

Usage:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http < scripts/smart_invoice_confirmation.py

Author: Claude Code Assistant
Date: 2025-11-27
"""

from datetime import date, datetime

# Configuration
REGULAR_FEE = 197.38
DISCOUNT_FEE = 162.39
DISCOUNT_THRESHOLD = 34.99  # Minimum credit to qualify for discount
DRY_RUN = True  # Set to False to actually apply changes

print("=" * 70)
print("SMART INVOICE CONFIRMATION SCRIPT")
print("=" * 70)
print(f"\nConfiguration:")
print(f"  Regular Fee: ${REGULAR_FEE}")
print(f"  Discount Fee: ${DISCOUNT_FEE}")
print(f"  Discount Threshold: ${DISCOUNT_THRESHOLD}")
print(f"  DRY RUN MODE: {DRY_RUN}")
print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def get_partner_credits(partner_id):
    """Get total outstanding credits for a partner."""
    credit_lines = env['account.move.line'].search([
        ('partner_id', '=', partner_id),
        ('account_id.account_type', '=', 'asset_receivable'),
        ('reconciled', '=', False),
        ('amount_residual', '<', 0),  # Negative = credit
        ('parent_state', '=', 'posted'),
    ])
    return {
        'total': sum(abs(line.amount_residual) for line in credit_lines),
        'lines': credit_lines,
    }


def apply_discount_to_invoice(invoice):
    """Change invoice line prices from regular to discount fee."""
    modified = False
    for line in invoice.invoice_line_ids:
        # Check if line has regular fee (allow small tolerance)
        if abs(line.price_unit - REGULAR_FEE) < 0.01:
            if not DRY_RUN:
                line.with_context(check_move_validity=False).write({
                    'price_unit': DISCOUNT_FEE
                })
            modified = True
    return modified


def apply_credits_to_invoice(invoice, credit_lines):
    """Apply available credits to the invoice after confirmation."""
    if invoice.state != 'posted':
        return 0.0

    # Get the receivable line from the invoice
    receivable_lines = invoice.line_ids.filtered(
        lambda l: l.account_id.account_type == 'asset_receivable'
        and l.amount_residual > 0
    )

    if not receivable_lines:
        return 0.0

    total_applied = 0.0

    for credit_line in credit_lines:
        if credit_line.amount_residual >= 0:  # Skip if already fully reconciled
            continue

        for recv_line in receivable_lines:
            if recv_line.amount_residual <= 0:
                continue

            # Calculate amount to reconcile
            amount_to_apply = min(
                recv_line.amount_residual,
                abs(credit_line.amount_residual)
            )

            if amount_to_apply > 0:
                if not DRY_RUN:
                    # Reconcile the lines
                    (recv_line + credit_line).reconcile()
                total_applied += amount_to_apply

    return total_applied


# Main Processing
print("\n" + "=" * 70)
print("STEP 1: Finding Draft Invoices")
print("=" * 70)

draft_invoices = env['account.move'].search([
    ('state', '=', 'draft'),
    ('move_type', '=', 'out_invoice'),
], order='partner_id, invoice_date')

print(f"\nFound {len(draft_invoices)} draft customer invoices")

if not draft_invoices:
    print("\nNo draft invoices to process. Exiting.")
else:
    # Analyze and process invoices
    print("\n" + "=" * 70)
    print("STEP 2: Analyzing Invoices & Credits")
    print("=" * 70)

    results = {
        'discount_applied': [],
        'credits_applied': [],
        'confirmed': [],
        'skipped': [],
        'errors': [],
    }

    for invoice in draft_invoices:
        partner = invoice.partner_id
        if not partner:
            results['skipped'].append({
                'invoice': invoice.name or 'New',
                'reason': 'No partner assigned'
            })
            continue

        print(f"\n--- Processing: {invoice.name or 'New'} ---")
        print(f"  Partner: {partner.name}")
        print(f"  Amount: ${invoice.amount_total:.2f}")

        # Get partner's outstanding credits
        credit_info = get_partner_credits(partner.id)
        print(f"  Outstanding Credits: ${credit_info['total']:.2f}")

        # Check if invoice has lines with regular fee
        has_regular_fee = any(
            abs(line.price_unit - REGULAR_FEE) < 0.01
            for line in invoice.invoice_line_ids
        )

        discount_applied = False

        # Apply discount if customer has sufficient credits
        if has_regular_fee and credit_info['total'] >= DISCOUNT_THRESHOLD:
            print(f"  → Applying DISCOUNT (${REGULAR_FEE} → ${DISCOUNT_FEE})")
            discount_applied = apply_discount_to_invoice(invoice)
            if discount_applied:
                results['discount_applied'].append({
                    'invoice': invoice.name or 'New',
                    'partner': partner.name,
                    'credit_available': credit_info['total'],
                })
                # Recompute invoice totals
                if not DRY_RUN:
                    invoice._compute_amount()
        elif has_regular_fee:
            print(f"  → No discount (credit ${credit_info['total']:.2f} < threshold ${DISCOUNT_THRESHOLD})")
        else:
            print(f"  → No regular fee lines found (may already have discount)")

        # Confirm the invoice
        try:
            if not DRY_RUN:
                invoice.action_post()
            print(f"  → Invoice CONFIRMED")
            results['confirmed'].append({
                'invoice': invoice.name or 'New',
                'partner': partner.name,
                'amount': invoice.amount_total,
                'discount_applied': discount_applied,
            })
        except Exception as e:
            print(f"  → ERROR confirming: {str(e)}")
            results['errors'].append({
                'invoice': invoice.name or 'New',
                'partner': partner.name,
                'error': str(e),
            })
            continue

        # Apply credits to the confirmed invoice
        if credit_info['total'] > 0 and not DRY_RUN:
            # Refresh credit lines after discount may have changed things
            credit_info = get_partner_credits(partner.id)
            credits_applied = apply_credits_to_invoice(invoice, credit_info['lines'])
            if credits_applied > 0:
                print(f"  → Credits Applied: ${credits_applied:.2f}")
                results['credits_applied'].append({
                    'invoice': invoice.name or 'New',
                    'partner': partner.name,
                    'amount': credits_applied,
                })

    # Summary Report
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)

    print(f"\n📊 STATISTICS:")
    print(f"  Total invoices processed: {len(draft_invoices)}")
    print(f"  Invoices confirmed: {len(results['confirmed'])}")
    print(f"  Discounts applied: {len(results['discount_applied'])}")
    print(f"  Credit applications: {len(results['credits_applied'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")

    if results['discount_applied']:
        print(f"\n💰 DISCOUNTS APPLIED ({len(results['discount_applied'])}):")
        total_discount_savings = len(results['discount_applied']) * (REGULAR_FEE - DISCOUNT_FEE)
        for item in results['discount_applied']:
            print(f"  - {item['partner']}: Credit ${item['credit_available']:.2f}")
        print(f"  TOTAL DISCOUNT VALUE: ${total_discount_savings:.2f}")

    if results['credits_applied']:
        print(f"\n✅ CREDITS APPLIED ({len(results['credits_applied'])}):")
        total_credits = sum(item['amount'] for item in results['credits_applied'])
        for item in results['credits_applied']:
            print(f"  - {item['partner']}: ${item['amount']:.2f}")
        print(f"  TOTAL CREDITS APPLIED: ${total_credits:.2f}")

    if results['skipped']:
        print(f"\n⚠️ SKIPPED ({len(results['skipped'])}):")
        for item in results['skipped']:
            print(f"  - {item['invoice']}: {item['reason']}")

    if results['errors']:
        print(f"\n❌ ERRORS ({len(results['errors'])}):")
        for item in results['errors']:
            print(f"  - {item['invoice']} ({item['partner']}): {item['error']}")

    if DRY_RUN:
        print("\n" + "=" * 70)
        print("⚠️  DRY RUN MODE - No changes were made!")
        print("    Set DRY_RUN = False to apply changes")
        print("=" * 70)
    else:
        # Commit the transaction
        env.cr.commit()
        print("\n" + "=" * 70)
        print("✅ All changes committed successfully!")
        print("=" * 70)

print("\nScript completed.")
