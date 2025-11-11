# Cesta Ticket Rebalancing Plan
**Date:** 2025-11-11
**Database:** Local Testing → Production
**Objective:** Separate Cesta Ticket as distinct benefit per Venezuelan labor law

---

## Executive Summary

Implement mandatory Venezuelan labor law requirement to separate Cesta Ticket (food allowance) as a distinct benefit while maintaining total compensation unchanged.

### Business Requirement:
- **Venezuelan Labor Law**: Cesta Ticket must be reported separately
- **Current Issue**: Column M (Cesta Ticket) included in total but not separated in Odoo
- **Solution**: Rebalance 70/25/5 distribution to (K+L) only, add separate Cesta Ticket field

### Key Metrics:
- **Total Employees**: 45
- **Total Cesta Ticket**: $8,578.81 USD (57% of total compensation!)
- **Range**: $95.69 - $332.25 USD per employee
- **Average**: $190.64 USD per employee

---

## Current vs Proposed System

### Current System (Incorrect):
```
Spreadsheet Column K (Salary+Bonus) → Odoo 70/25/5 distribution
Spreadsheet Column L (Other Bonuses) → NOT USED
Spreadsheet Column M (Cesta Ticket)  → NOT SEPARATED (rule returns 0.0)

Total in Odoo = K × 70% + K × 25% + K × 5% = K
Missing: L + M components!
```

### Proposed System (Correct):
```
Spreadsheet K+L → Odoo 70/25/5 distribution
Spreadsheet M   → contract.cesta_ticket_usd

New ueipab_salary_base = (K+L) × 70%
New ueipab_bonus_regular = (K+L) × 25%
New ueipab_extra_bonus = (K+L) × 5%
New cesta_ticket_usd = M

Total in Odoo = (K+L) × 70% + (K+L) × 25% + (K+L) × 5% + M
              = (K+L) + M
              = K + L + M ✓ CORRECT
```

---

## Rebalancing Formula

### Mathematical Proof:
```
Old Total = K + L + M

New Total = [(K+L) × 70%] + [(K+L) × 25%] + [(K+L) × 5%] + M
          = (K+L) × (70% + 25% + 5%) + M
          = (K+L) × 100% + M
          = (K+L) + M
          = K + L + M

∴ New Total = Old Total ✓
```

### Contract Field Updates:
```python
new_base = column_k_usd + column_l_usd

contract.ueipab_salary_base = new_base × 0.70   # 70%
contract.ueipab_bonus_regular = new_base × 0.25  # 25%
contract.ueipab_extra_bonus = new_base × 0.05    # 5%
contract.cesta_ticket_usd = column_m_usd         # Separate benefit
```

---

## Analysis Results

### Compensation Breakdown (Current Spreadsheet):

| Component | Total USD | % of Total | Description |
|-----------|-----------|------------|-------------|
| **Column K** (Salary+Bonus) | $6,376.70 | 42.38% | Currently used for 70/25/5 |
| **Column L** (Other Bonuses) | $91.12 | 0.61% | Currently NOT used |
| **Column M** (Cesta Ticket) | $8,578.81 | 57.01% | Currently NOT separated |
| **TOTAL** | **$15,046.63** | **100.00%** | True compensation |

### Cesta Ticket Value Distribution:

- **Minimum**: $95.69 USD (1 employee)
- **Maximum**: $332.25 USD (1 employee)
- **Average**: $190.64 USD
- **Most Common**: $179.67 USD (8 employees)
- **Unique Values**: 34 different amounts

**Key Finding**: Cesta Ticket is NOT a flat amount - it varies by employee and represents the LARGEST component of compensation (57%)!

---

## Example Employee: ARCIDES ARZOLA

### Current Spreadsheet:
```
K (Salary+Bonus):  $285.39 USD
L (Other Bonuses): $  0.00 USD
M (Cesta Ticket):  $289.52 USD
TOTAL:             $574.92 USD
```

### Current Odoo (INCORRECT):
```
ueipab_salary_base (70%):   $199.77 USD  (from K only)
ueipab_bonus_regular (25%): $ 71.35 USD  (from K only)
ueipab_extra_bonus (5%):    $ 14.27 USD  (from K only)
cesta_ticket_usd:           $  0.00 USD  ← NOT USED
TOTAL:                      $285.39 USD  ← MISSING $289.52!
```

### After Rebalancing (CORRECT):
```
New Base = K + L = $285.39 + $0.00 = $285.39 USD

ueipab_salary_base (70%):   $199.77 USD  (from K+L)
ueipab_bonus_regular (25%): $ 71.35 USD  (from K+L)
ueipab_extra_bonus (5%):    $ 14.27 USD  (from K+L)
cesta_ticket_usd:           $289.52 USD  ← NOW INCLUDED
TOTAL:                      $574.92 USD  ← CORRECT! ✓
```

### Verification:
```
Old Total:  $285.39 + $0.00 + $289.52 = $574.92 USD
New Total:  $199.77 + $71.35 + $14.27 + $289.52 = $574.92 USD
Difference: $0.00 ✓ PERFECT MATCH
```

---

## Implementation Steps

### Phase 1: Preparation (COMPLETED ✅)

1. ✅ **Analysis Script Created**
   - `/opt/odoo-dev/scripts/analyze-cesta-ticket-column-m.py`
   - Analyzes Column M values
   - Validates rebalancing formula
   - Shows preview of changes

2. ✅ **Rebalancing Script Created**
   - `/opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py`
   - Test mode: 1 employee
   - Production mode: All employees
   - Automatic backup before changes
   - Transaction-based with rollback

3. ✅ **VE_CESTA_TICKET Rule Updated**
   - Database: Local testing
   - Formula: Uses `contract.cesta_ticket_usd`
   - Bi-monthly logic: 50% per period (consistent with other rules)

---

### Phase 2: Testing (PENDING ⬜)

1. ⬜ **Run Analysis Script**
   ```bash
   python3 /opt/odoo-dev/scripts/analyze-cesta-ticket-column-m.py
   ```
   - Review Column M values
   - Verify rebalancing calculations
   - Confirm totals match

2. ⬜ **Run Rebalancing Script (TEST MODE)**
   ```bash
   python3 /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py test
   ```
   - Updates 1 employee only
   - Auto-commits for review
   - Verify contract values

3. ⬜ **Generate Test Payslip**
   - Create test batch for Dec 1-15, 2025
   - Generate payslip for test employee
   - Verify calculation:
     - VE_SALARY_70 = (New Base × 70%) × 50%
     - VE_BONUS_25 = (New Base × 25%) × 50%
     - VE_EXTRA_5 = (New Base × 5%) × 50%
     - VE_CESTA_TICKET = Column M × 50%
     - VE_GROSS = Sum of above
   - Compare with spreadsheet bi-weekly gross

4. ⬜ **Verify Accounting**
   - Check journal entries
   - Verify account balances
   - Confirm Cesta Ticket posted correctly

---

### Phase 3: Production Deployment (PENDING ⬜)

#### Step 1: Update Production Database Salary Rule

```bash
# Connect to production database
docker exec ueipab17_postgres_1 psql -U odoo -d ueipab17_postgres_1

# Update VE_CESTA_TICKET rule
UPDATE hr_salary_rule
SET amount_python_compute = '# Venezuelan Cesta Ticket (Food Allowance) - Bi-monthly calculation
# Uses contract.cesta_ticket_usd field (monthly amount from spreadsheet Column M)
# Venezuelan bi-monthly payroll: Split 50% per period

# Get payslip period
period_days = (payslip.date_to - payslip.date_from).days + 1

# Venezuelan bi-monthly logic:
# Period 1-15: 50% of monthly amount
# Period 16-31: 50% of monthly amount (FIXED, not proportional)
if period_days <= 16:
    proportion = 0.5  # Fixed 50% for bi-monthly
else:
    # For periods starting after 15th, also use 50%
    day_from = payslip.date_from.day
    if day_from >= 15:
        proportion = 0.5  # Fixed 50% for second half
    else:
        proportion = period_days / 30.0  # Proportional for unusual periods

# Calculate Cesta Ticket (bi-monthly)
monthly_cesta_ticket = contract.cesta_ticket_usd or 0.0
result = monthly_cesta_ticket * proportion'
WHERE code = 'VE_CESTA_TICKET';

# Verify update
SELECT code, amount_python_compute FROM hr_salary_rule WHERE code = 'VE_CESTA_TICKET';
```

#### Step 2: Update Rebalancing Script for Production

Edit `/opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py`:
```python
# Change database configuration to production
self.db_config = {
    'host': '10.124.0.3',
    'port': 5432,
    'database': 'ueipab17_postgres_1',
    'user': 'odoo',
    'password': 'odoo'
}
```

#### Step 3: Run Production Rebalancing

```bash
# Run in production mode
python3 /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py production

# Review changes
# Confirm with "yes" to commit
```

#### Step 4: Verify Production

1. ⬜ Check 5-10 random employee contracts
2. ⬜ Verify totals match spreadsheet
3. ⬜ Generate test payslip for Dec 1-15
4. ⬜ Compare with spreadsheet values
5. ⬜ Confirm accounting entries

---

### Phase 4: Documentation Update (PENDING ⬜)

1. ⬜ Update payroll procedure documentation
2. ⬜ Document Cesta Ticket as separate benefit
3. ⬜ Update contract creation guidelines
4. ⬜ Train payroll staff on new structure

---

## Backup and Rollback Strategy

### Automatic Backup:
- Script creates timestamped backup table before any changes
- Format: `hr_contract_backup_cesta_rebalance_YYYYMMDD_HHMMSS`
- Includes all modified fields for open contracts

### Rollback Procedure (if needed):
```sql
-- Restore from backup
UPDATE hr_contract c SET
    ueipab_salary_base = b.ueipab_salary_base,
    ueipab_bonus_regular = b.ueipab_bonus_regular,
    ueipab_extra_bonus = b.ueipab_extra_bonus,
    cesta_ticket_usd = b.cesta_ticket_usd
FROM hr_contract_backup_cesta_rebalance_20251111_143000 b
WHERE c.id = b.id;

-- Verify restoration
SELECT COUNT(*) FROM hr_contract c
JOIN hr_contract_backup_cesta_rebalance_20251111_143000 b ON c.id = b.id
WHERE c.ueipab_salary_base = b.ueipab_salary_base;

-- Revert salary rule
UPDATE hr_salary_rule
SET amount_python_compute = 'result = 0.0'
WHERE code = 'VE_CESTA_TICKET';
```

---

## Validation Checklist

### Pre-Deployment Validation:
- [ ] Analysis script shows correct Column M values
- [ ] Rebalancing formula verified mathematically
- [ ] Test mode updates 1 employee correctly
- [ ] Test payslip calculations match spreadsheet
- [ ] Accounting entries are correct
- [ ] Backup created successfully

### Post-Deployment Validation:
- [ ] All 45 employee contracts updated
- [ ] Sample verification (5-10 employees) matches spreadsheet
- [ ] Test payslip generation successful
- [ ] VE_CESTA_TICKET rule shows non-zero values
- [ ] VE_GROSS includes Cesta Ticket component
- [ ] Accounting posts correctly
- [ ] Payslip PDF shows Cesta Ticket line

---

## Impact Analysis

### Financial Impact:
- **No change in total compensation**: Old Total = New Total
- **Proper breakdown**: Cesta Ticket now visible as separate line
- **Compliance**: Meets Venezuelan labor law requirements

### System Impact:
- **Contract fields**: 4 fields updated per contract (45 contracts)
- **Salary rules**: 1 rule updated (VE_CESTA_TICKET)
- **Payslips**: New line item appears (Cesta Ticket)
- **Reports**: Cesta Ticket now trackable separately

### User Impact:
- **Payroll staff**: Will see Cesta Ticket as separate line
- **Employees**: Payslip now shows correct breakdown
- **Accounting**: Proper categorization for reporting
- **Compliance**: Meets legal reporting requirements

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Calculation errors | Low | High | Mathematical proof + test mode validation |
| Data loss | Very Low | Critical | Automatic backup + transaction-based |
| Production issues | Low | Medium | Test in development first + rollback plan |
| Accounting errors | Low | High | Verify journal entries before go-live |
| User confusion | Medium | Low | Documentation + training |

**Overall Risk Level**: **LOW** (with proper testing and validation)

---

## Success Criteria

### Technical Success:
- ✅ All contract fields updated correctly
- ✅ VE_CESTA_TICKET rule returns non-zero values
- ✅ Payslip calculations match spreadsheet
- ✅ Total compensation unchanged (difference < $0.01)
- ✅ Accounting entries post correctly

### Business Success:
- ✅ Venezuelan labor law compliance achieved
- ✅ Cesta Ticket visible as separate benefit
- ✅ Employees can see breakdown on payslip
- ✅ Accounting can track Cesta Ticket separately
- ✅ Audit trail maintained

---

## Timeline

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Phase 1: Preparation | 2 hours | 2025-11-11 | 2025-11-11 | ✅ COMPLETED |
| Phase 2: Testing | 1 day | 2025-11-12 | 2025-11-12 | ⬜ PENDING |
| Phase 3: Production | 2 hours | 2025-11-13 | 2025-11-13 | ⬜ PENDING |
| Phase 4: Documentation | 1 day | 2025-11-14 | 2025-11-14 | ⬜ PENDING |

**Estimated Total Time**: 2-3 days (with proper testing)

---

## Scripts Reference

### 1. Analysis Script
**Path**: `/opt/odoo-dev/scripts/analyze-cesta-ticket-column-m.py`

**Purpose**: Analyze Column M values and preview rebalancing

**Usage**:
```bash
python3 /opt/odoo-dev/scripts/analyze-cesta-ticket-column-m.py
```

**Output**:
- Cesta Ticket statistics (min, max, avg)
- Unique values distribution
- Current vs proposed breakdown
- Sample employee calculations

---

### 2. Rebalancing Script
**Path**: `/opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py`

**Purpose**: Update contract fields with rebalanced values

**Usage**:
```bash
# Test mode (1 employee)
python3 /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py test

# Production mode (all employees)
python3 /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py production
```

**Features**:
- Automatic backup creation
- Transaction-based updates
- Test mode for validation
- Production mode with confirmation
- Verification after updates

---

## Related Documentation

- `/opt/odoo-dev/documentation/CUSTOM_FIELDS_MODULES_ANALYSIS.md` - Custom fields analysis
- `/opt/odoo-dev/documentation/AGUINALDOS_ANALYSIS_2025.md` - Aguinaldos implementation
- `/opt/odoo-dev/documentation/CONTRACT_UPDATE_IMPACT_ANALYSIS.md` - Contract update analysis

---

## Support and Troubleshooting

### Common Issues:

1. **Employee not found in database**
   - Check employee name matches exactly (case-sensitive)
   - Verify employee has active contract (state='open')
   - Check department assignment

2. **Calculation mismatch**
   - Verify exchange rate (O2 cell)
   - Check Column K, L, M values in spreadsheet
   - Ensure proper number parsing (Venezuelan format)

3. **Payslip shows zero for Cesta Ticket**
   - Verify VE_CESTA_TICKET rule updated
   - Check contract.cesta_ticket_usd field has value
   - Regenerate payslip (don't recompute)

4. **Total doesn't match**
   - Verify all components sum correctly
   - Check for rounding differences (< $0.01 acceptable)
   - Review accounting entries

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Payroll Manager | _____________ | _____________ | ______ |
| IT Director | _____________ | _____________ | ______ |
| Finance Director | _____________ | _____________ | ______ |

---

**Prepared by:** Claude Code AI Assistant
**Review Date:** 2025-11-11
**Status:** Ready for Testing
**Risk Level:** Low (with proper testing and validation)
**Estimated Implementation Time:** 2-3 days
