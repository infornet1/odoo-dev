- "Always remember that we should works locally never in production env"
- "Always memorize this script for sync btw env scripts/sync-veb-rates-from-production.sql and also keep in mind NEVER TOUCH DB_UEIPAB without proper authorization from me"

## Payroll Disbursement Detail Report - Recent Improvements (2025-11-12)

### Report Enhancements
The Payroll Pending Disbursement Detail report has been significantly improved with the following fixes and features:

#### Fixed Issues
1. **ARI TAX Column**: Fixed salary rule code from `VE_ARI` to `VE_ARI_DED` - now displays correct income tax withholding values
2. **Social Security Column**: Fixed salary rule codes to use actual codes (`VE_SSO_DED`, `VE_FAOV_DED`, `VE_PARO_DED`, `LIQUID_INCES`) instead of non-existent codes
3. **Data Duplication**: Removed double document iteration that caused data to display twice
4. **Header/Footer Margins**: Improved multi-page layout using proper Odoo QWeb patterns with `web.external_layout`
5. **Period Display**: Now shows actual payslip batch period dates (min/max from payslips) instead of wizard filter dates

#### Layout Reorganization
- **Column Order**: VAT ID moved to first position (after #), Department column removed
- **Deduction Breakdown**: Added individual columns for detailed transparency:
  - ARI (Income Tax - SENIAT)
  - SSO 4% (Seguro Social Obligatorio)
  - FAOV 1% (Fondo de Ahorro Obligatorio para la Vivienda)
  - PARO 0.5% (Paro Forzoso)
  - Other Deductions
- **Totals Consolidation**: Removed duplicate totals row from table footer, consolidated all totals at report end
- **9% Tax Calculation**: Added automatic 9% tax calculation on Net Payable (USD and VEB) in summary section

#### Technical Details
- Report File: `addons/ueipab_payroll_enhancements/reports/payroll_disbursement_detail_report.xml`
- Model: `hr.payslip`
- Paper Format: Landscape Letter (custom margins: top=40mm, bottom=25mm, header_spacing=35mm)
- Layout Pattern: Single-page aggregate report (all payslips in one table, one page for entire batch)

#### Key Features
- Real-time period calculation from actual payslip dates
- Color-coded financial totals (blue for Net Payable, orange for Tax)
- Comprehensive deduction transparency
- Enhanced notes explaining each deduction type
- Optimized font sizes for landscape layout (7pt data, headers remain readable)

---

## Liquidation Salary Structure - Formula Fix (2025-11-12)

### Critical Issue Fixed
The "Liquidación Venezolana" (Venezuelan Liquidation) salary structure had ALL formulas hardcoded with test values, causing every employee to receive identical liquidation amounts regardless of actual salary or service time.

### Root Cause
After tuning the regular Venezuelan payroll structure (`[VE] UEIPAB Venezuelan Payroll`) to use custom contract fields, the liquidation structure was never updated and continued using hardcoded test data.

### Key Contract Fields
```
contract.wage = $354.95                    (Total compensation package)
contract.ueipab_deduction_base = $151.56   (Base salary for liquidation)
```

The `ueipab_deduction_base` field represents the "Original K" base salary used for:
- Social security deductions in regular payroll (SSO, FAOV, PARO, ARI)
- Liquidation benefit calculations per Venezuelan law (LOTTT)
- Calculated as: Total wage minus bonuses/allowances ($354.95 - $203.39 = $151.56)

### Formulas Fixed (13 Salary Rules)

#### Before Fix (ALL Hardcoded):
- `LIQUID_SERVICE_MONTHS = 11.0` ❌
- `LIQUID_DAILY_SALARY = 11.83` ❌ Used wrong wage
- `LIQUID_INTEGRAL_DAILY = 100.0` ❌
- `LIQUID_PRESTACIONES = 582.30` ❌
- `LIQUID_ANTIGUEDAD = 176.48` ❌
- `LIQUID_UTILIDADES = 256.71` ❌
- `LIQUID_BONO_VACACIONAL = 128.33` ❌
- `LIQUID_VACACIONES = 0.0` ❌
- `LIQUID_INTERESES = 180.0` ❌
- `LIQUID_FAOV = -2.57` ❌
- `LIQUID_INCES = -1.28` ❌
- `LIQUID_NET = 1319.97` ❌

#### After Fix (Dynamic Calculations):
All formulas now calculate based on:
- `contract.ueipab_deduction_base` ($151.56 base salary)
- Service time from `contract.date_start` to `payslip.date_to`
- Venezuelan Labor Law (LOTTT) Articles 104, 108, 141, 142, 190-192
- Integral salary includes base + proportional benefits (utilidades + bono vacacional)

### Test Case Results (Gabriel España - 10.97 months service)

**Before:** NET = $1,319.97 (hardcoded - WRONG!)
**After:** NET = $491.05 (calculated correctly)
**Savings:** $828.92 per liquidation

### Implementation

**Script Created:** `/opt/odoo-dev/scripts/fix_liquidation_formulas.py`
- Contains all 13 formula definitions
- Includes detailed Venezuelan law compliance notes
- Self-documenting with examples

**Execution:**
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/fix_liquidation_formulas.py
```

**Status:** ✅ All 13 salary rules successfully updated in database

### Key Formula Examples

**Service Months:**
```python
from dateutil.relativedelta import relativedelta
delta = relativedelta(payslip.date_to, contract.date_start)
result = delta.years * 12 + delta.months + (delta.days / 30.0)
```

**Daily Salary:**
```python
result = (contract.ueipab_deduction_base or 0.0) / 30.0
# Example: $151.56 / 30 = $5.05/day
```

**Prestaciones (Severance):**
```python
# First 3 months: 5 days/month, then 2 days/month
# Calculated on integral daily salary (base + benefits)
```

### How to Use

1. **Delete old liquidation payslips** (they have wrong calculations)
2. **Create new liquidation** via Odoo HR → Liquidation wizard
3. **New payslips will automatically use corrected formulas**
4. **Verify calculations** match employee's actual service time and salary

### Documentation
Complete technical documentation: `/opt/odoo-dev/documentation/LIQUIDATION_FORMULA_FIX_2025-11-12.md`

### Legal Compliance
✅ Complies with Venezuelan Labor Law (LOTTT)
✅ Uses base salary (excluding bonuses) per regulations
✅ Prestaciones calculated on integral salary
✅ Service time from actual contract dates
✅ Proportional benefits for partial years

### Important Notes
- Regular payroll structure (`[VE] UEIPAB Venezuelan Payroll`) continues working correctly
- NO changes needed to `contract.wage` field
- Liquidation now independent and correctly calculated
- Test with Gabriel España validated all formulas work correctly