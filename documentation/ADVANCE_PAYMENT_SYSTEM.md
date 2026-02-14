# Advance Payment System (Pago Adelanto)

**Status:** Production | **Version:** 17.0.1.52.1 | **Deployed:** 2026-01-14

Allows partial salary disbursement when company needs to pay employees in installments due to financial constraints.

## Business Use Case

When company cannot pay full salary at once:
1. **Advance Batch (e.g., 50%)**: Pay partial salary now
2. **Remainder Batch (e.g., 50%)**: Pay remaining balance later

Each batch:
- Computes payslips with multiplied earnings
- Deductions recalculate on reduced amounts
- Posts with its own exchange rate
- Clean, independent journal entries

## Batch Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_advance_payment` | Boolean | Checkbox "Es Pago Adelanto" |
| `advance_percentage` | Float | Percentage to pay (e.g., 50.0) |
| `advance_total_amount` | Computed | Total advance amount |
| `is_remainder_batch` | Boolean | Marks as remainder payment |
| `advance_batch_id` | Many2one | Link to original advance batch |

## Payslip Fields

| Field | Type | Description |
|-------|------|-------------|
| `advance_amount` | Computed | Individual advance amount |

## Salary Rules Behavior

When `is_advance_payment = True` OR `is_remainder_batch = True`:
```python
# Earnings multiplied by advance_percentage
VE_SALARY_V2 = contract.salary * (batch.advance_percentage / 100)
VE_EXTRABONUS_V2 = contract.extrabonus * (batch.advance_percentage / 100)
VE_BONUS_V2 = contract.bonus * (batch.advance_percentage / 100)
# Deductions auto-recalculate on reduced gross
```

## Email Templates (Synced to Production 2026-01-08)

| Template | Purpose | Prod ID |
|----------|---------|---------|
| Payslip Email - Advance Payment - Employee Delivery | Full detailed advance notification | 44 |
| Payslip Email - Remainder Payment - Reconciliation | Shows advance + remainder + total | 45 |

## Accounting Treatment

Each batch posts independently with its exchange rate:
```
Advance Batch (50% at rate 298):
  DR 5.1.01.10.001  Bs. 14,900
     CR 1.1.01.02.001  Bs. 14,900

Remainder Batch (50% at rate 310):
  DR 5.1.01.10.001  Bs. 15,500
     CR 1.1.01.02.001  Bs. 15,500
```

No provisions or exchange difference accounts needed.
