# Enhancement Plan: Show "Pagado" for Prepaid Vacaciones/Bono in Relación de Liquidación

**Status:** 📋 In Review (Updated with "Ya han sido pagadas" approach)
**Target Version:** v1.26.0
**Created:** 2025-11-19
**Last Updated:** 2025-11-20
**Author:** Development Team

---

## 🔄 IMPORTANT UPDATE (2025-11-20)

**Approach Changed from "Hide Rows" to "Show Paid Status"**

### Original Approach (Discarded)
- ❌ Remove Vacaciones/Bono rows entirely when prepaid
- ❌ Renumber remaining benefits (1-4 instead of 1-6)
- ❌ Variable layout structure across reports

### NEW Approach (Current) ✅
- ✅ **KEEP all rows** (consistent 1-6 structure)
- ✅ Show **"Ya han sido pagadas"** instead of amounts
- ✅ Same layout for ALL reports (easy comparison)
- ✅ Professional accounting standard

**Rationale:** Consistent layout is more important than hiding information. The "Ya han sido pagadas" status is clear, professional, and maintains report structure integrity.

---

## Table of Contents
1. [Business Problem](#1-business-problem)
2. [Current Behavior](#2-current-behavior)
3. [Proposed Solution](#3-proposed-solution)
4. [Technical Implementation](#4-technical-implementation)
5. [Critical Constraints](#5-critical-constraints)
6. [Implementation Phases](#6-implementation-phases)
7. [Test Scenarios](#7-test-scenarios)
8. [Risks & Mitigations](#8-risks--mitigations)
9. [Open Questions](#9-open-questions)

---

## 1. Business Problem

### The Confusion Scenario

When employees receive their **Relación de Liquidación** report and Vacaciones/Bono Vacacional have been **fully prepaid** (paid monthly throughout employment), the current report shows:

```
PRESTACIONES SOCIALES (BENEFICIOS)
1. Vacaciones                         Bs. 291,234.56
2. Bono Vacacional                    Bs. 387,645.08
...

DEDUCCIONES
- Vacaciones y Bono Prepagadas       Bs. -678,879.64

NET EFFECT FROM VACACIONES/BONO:      Bs. 0.00
```

### Why This Is Problematic

**Employee reaction:**
> "I see Bs. 678,879.64 in benefits and the same amount deducted. Did I already get this money? Am I getting it twice? Why show it if the net is zero?"

**Accounting perspective:**
- Company pays Vacaciones/Bono **monthly** as part of regular payroll
- At liquidation time, these amounts are **fully accounted for** (net = $0)
- Displaying large offsetting amounts creates **unnecessary confusion**
- Leads to repeated clarification requests and potential disputes

### Desired Outcome

**✅ REVISED APPROACH (2025-11-20): Keep Layout Consistent, Show Status**

**When Vacaciones + Bono net = $0 (fully prepaid):**
- ✅ **KEEP** Vacaciones line in benefits → Show "Ya han sido pagadas"
- ✅ **KEEP** Bono Vacacional line in benefits → Show "Ya han sido pagadas"
- ✅ **KEEP** row structure (consistent numbering across all reports)
- ❌ **HIDE** Prepaid deduction line (already reflected as "Ya han sido pagadas")
- ✅ **ADD** explanatory note with total amount paid

**When net ≠ $0 (partially prepaid or not prepaid):**
- ✅ Show all lines with monetary amounts (current behavior)

**Why This Approach Is Better:**
1. **Consistent Layout:** All liquidation reports have identical structure
2. **Clear Status:** "Ya han sido pagadas" is explicit and unambiguous
3. **Easy Comparison:** Employee can compare different liquidations
4. **Transparent:** Shows vacation benefit exists (not hidden)
5. **Professional:** Standard accounting practice to show $0 items with status

---

## 2. Current Behavior

### Salary Structure (LIQUID_VE_V2)

**Calculation Rules:**
```python
# Benefits
LIQUID_VACACIONES_V2        → Calculates full vacation amount
LIQUID_BONO_VACACIONAL_V2   → Calculates full bono amount

# Deductions
LIQUID_VACATION_PREPAID_V2  → Deducts prepaid amount from contract field
                               (contract.ueipab_vacation_prepaid_amount)

# Net
LIQUID_NET_V2               → Total benefits - Total deductions
```

**Example Calculation:**
```
Employee: MAGYELYS MATA
Service: Sep 2023 - Jul 2025 (23 months)

Vacaciones (15 días/año):
  = (salary_monthly / 30) × 15 days × (23/12 years)
  = ($127.66 / 30) × 15 × 1.92
  = $122.57

Bono Vacacional (18.28 días/año progressive):
  = (salary_monthly / 30) × 18.28 days × (23/12 years)
  = ($127.66 / 30) × 18.28 × 1.92
  = $149.27

Prepaid Deduction:
  = -contract.ueipab_vacation_prepaid_amount
  = -$271.84

Net Impact: $122.57 + $149.27 - $271.84 = $0.00 ✅
```

### Report Display (Current)

**PDF/XLSX Output:**
```
PRESTACIONES SOCIALES (BENEFICIOS)
1. Vacaciones                         $122.57
2. Bono Vacacional                    $149.27
3. Utilidades                         $XXX.XX
4. Prestaciones Sociales              $XXX.XX
5. Antigüedad                         $XXX.XX
6. Intereses sobre Prestaciones       $XXX.XX

Subtotal Prestaciones:                $XXX.XX

DEDUCCIONES
- FAOV (1%)                          -$XX.XX
- INCES (0.5%)                       -$XX.XX
- Vacaciones y Bono Prepagadas       -$271.84

Total Deducciones:                   -$XXX.XX

NETO A RECLAMAR:                      $XXX.XX
```

**Problem:** Big numbers shown with net zero effect → confusion

---

## 3. Proposed Solution

### Wizard Enhancement

Add **optional boolean field** to `liquidacion.breakdown.wizard`:

```python
hide_prepaid_vacation = fields.Boolean(
    string='Mostrar "Ya han sido pagadas" en Vacaciones/Bono (si prepagadas)',
    default=False,
    help='Muestra "Ya han sido pagadas" en lugar de montos cuando Vacaciones y Bono\n'
         'están completamente prepagadas (neto $0). Mantiene estructura consistente\n'
         'del reporte y clarifica que ya fueron pagados mensualmente.'
)
```

**UI Placement:** After `rate_date` field in wizard form

**UI Label Update:** Changed from "Ocultar" (Hide) to "Mostrar Pagado" (Show Paid) to reflect new approach

### Report Behavior Decision Tree

```
┌─────────────────────────────────────┐
│ Wizard Toggle: hide_prepaid_vacation│
└───────────┬─────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
   OFF              ON
    │                │
    v                v
Show All     Check Net Amount
  Lines      ┌──────────────┐
             │ Net = $0 ?   │
             └──┬─────────┬─┘
                │         │
               YES       NO
                │         │
                v         v
           HIDE LINES  SHOW ALL
           + Add Note    LINES
```

### Scenario A: **Toggle ON + Fully Prepaid (Net = $0)** ✅ REVISED

**Detection Logic:**
```python
vac = LIQUID_VACACIONES_V2
bono = LIQUID_BONO_VACACIONAL_V2
prepaid = LIQUID_VACATION_PREPAID_V2

net = vac + bono + prepaid
is_fully_prepaid = abs(net) < 0.01  # Tolerance for rounding

if hide_prepaid_vacation and is_fully_prepaid:
    # SHOW rows with "Ya han sido pagadas" instead of amount
    # HIDE prepaid deduction (implied by "Ya han sido pagadas" status)
```

**PDF/XLSX Output:**
```
PRESTACIONES SOCIALES (BENEFICIOS)
1. Vacaciones                         Ya han sido pagadas
2. Bono Vacacional                    Ya han sido pagadas
3. Utilidades                         $XXX.XX
4. Prestaciones Sociales              $XXX.XX
5. Antigüedad                         $XXX.XX
6. Intereses sobre Prestaciones       $XXX.XX

Subtotal Prestaciones:                $XXX.XX

DEDUCCIONES
- FAOV (1%)                          -$XX.XX
- INCES (0.5%)                       -$XX.XX

[NO Prepaid deduction line - already shown as "Ya han sido pagadas" above]

Total Deducciones:                   -$XX.XX

NETO A RECLAMAR:                      $XXX.XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 NOTA:
• Vacaciones y Bono Vacacional pagados mensualmente
  durante período de empleo
  Monto total: $271.84 (Bs. 67,890.12 al 19/11/2025)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Key Changes from Original:**
- ✅ Rows remain (consistent layout)
- ✅ Show "Ya han sido pagadas" instead of blank/hiding
- ✅ Numbering stays 1-6 (same across all reports)
- ✅ Clear status visible at a glance

### Scenario B: **Toggle ON + Partially Prepaid (Net ≠ $0)**

**Detection Logic:**
```python
net = vac + bono + prepaid
is_fully_prepaid = abs(net) < 0.01

if not is_fully_prepaid:
    # SHOW all lines normally (employee owes/is owed money)
```

**Example:**
```
Vacaciones:      $500.00
Bono:            $650.00
Prepaid:        -$800.00
Net:             $350.00  → SHOW ALL (not fully prepaid)
```

### Scenario C: **Toggle OFF**

Show all lines regardless of amounts (current behavior preserved).

---

## 4. Technical Implementation

### 4.1 Database Schema

**No database changes required** - This is a display-only feature.

### 4.2 Wizard Model Changes

**File:** `addons/ueipab_payroll_enhancements/models/liquidacion_breakdown_wizard.py`

```python
class LiquidacionBreakdownWizard(models.TransientModel):
    _name = 'liquidacion.breakdown.wizard'

    # ... existing fields ...

    hide_prepaid_vacation = fields.Boolean(
        string='Ocultar Vacaciones/Bono (si prepagadas)',
        default=False,
        help='Oculta Vacaciones y Bono Vacacional cuando están completamente '
             'prepagadas (neto $0)\nÚtil para evitar confusión cuando estos '
             'beneficios ya fueron pagados mensualmente'
    )

    def action_print_pdf(self):
        """Generate and print PDF reports."""
        self.ensure_one()

        data = {
            'wizard_id': self.id,
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
            'payslip_ids': self.payslip_ids.ids,
            'use_custom_rate': self.use_custom_rate,
            'custom_exchange_rate': self.custom_exchange_rate if self.use_custom_rate else None,
            'rate_date': self.rate_date,
            'hide_prepaid_vacation': self.hide_prepaid_vacation,  # ✅ NEW
        }

        report = self.env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
        return report.report_action(docids=self.payslip_ids.ids, data=data)

    def action_export_xlsx(self):
        """Export report to Excel format."""
        # Same change - pass hide_prepaid_vacation in URL or session
```

### 4.3 Wizard View Changes

**File:** `addons/ueipab_payroll_enhancements/wizard/liquidacion_breakdown_wizard_view.xml`

```xml
<field name="rate_date"/>

<!-- ✅ NEW FIELD -->
<field name="hide_prepaid_vacation"/>
<div invisible="not hide_prepaid_vacation" class="alert alert-info" role="alert">
    <i class="fa fa-info-circle"/>
    <strong>Nota:</strong> Las líneas de Vacaciones y Bono Vacacional se ocultarán
    automáticamente si el monto neto es $0.00 (ya pagadas mensualmente).
    Se incluirá una nota explicativa en el reporte.
</div>
```

### 4.4 Report Model Changes

**File:** `addons/ueipab_payroll_enhancements/models/liquidacion_breakdown_report.py`

**Key Changes:**

```python
def _generate_breakdown(self, payslip, currency, data=None):
    """Generate complete breakdown for a payslip.

    Args:
        payslip: hr.payslip record
        currency: res.currency record
        data: Optional wizard data (includes hide_prepaid_vacation)

    Returns:
        dict: Breakdown data with conditional hiding
    """
    # ... existing setup code ...

    # Get hide flag from wizard data
    hide_prepaid = data.get('hide_prepaid_vacation', False) if data else False

    # Get vacation/bono amounts (V2 with V1 fallback)
    vacaciones_usd = self._get_line_value(payslip, 'LIQUID_VACACIONES_V2') or \
                     self._get_line_value(payslip, 'LIQUID_VACACIONES')
    bono_usd = self._get_line_value(payslip, 'LIQUID_BONO_VACACIONAL_V2') or \
               self._get_line_value(payslip, 'LIQUID_BONO_VACACIONAL')
    prepaid_usd = self._get_line_value(payslip, 'LIQUID_VACATION_PREPAID_V2') or \
                  self._get_line_value(payslip, 'LIQUID_VACATION_PREPAID')

    # Convert to report currency
    vac_amt = self._convert_currency(vacaciones_usd, usd, currency, rate_date, ...)
    bono_amt = self._convert_currency(bono_usd, usd, currency, rate_date, ...)
    prepaid_amt = self._convert_currency(prepaid_usd, usd, currency, rate_date, ...)

    # Calculate net
    vac_bono_net = vac_amt + bono_amt + prepaid_amt

    # Determine if should hide
    is_fully_prepaid = abs(vac_bono_net) < 0.01
    should_hide_vacation = hide_prepaid and is_fully_prepaid

    # Build benefits list (ALWAYS include all rows, conditional display)
    benefits = []
    benefit_num = 1

    # Vacaciones (ALWAYS included, conditional amount vs "Ya han sido pagadas")
    benefits.append({
        'number': benefit_num,
        'name': 'Vacaciones',
        'formula': '...' if not should_hide_vacation else '',
        'calculation': '...' if not should_hide_vacation else '',
        'detail': '...' if not should_hide_vacation else '',
        'amount': vac_amt if not should_hide_vacation else None,
        'amount_formatted': self._format_amount(vac_amt, currency) if not should_hide_vacation else 'Ya han sido pagadas',
        'is_prepaid': should_hide_vacation,  # Flag for special rendering
    })
    benefit_num += 1

    # Bono Vacacional (ALWAYS included, conditional amount vs "Ya han sido pagadas")
    benefits.append({
        'number': benefit_num,
        'name': 'Bono Vacacional',
        'formula': '...' if not should_hide_vacation else '',
        'calculation': '...' if not should_hide_vacation else '',
        'detail': '...' if not should_hide_vacation else '',
        'amount': bono_amt if not should_hide_vacation else None,
        'amount_formatted': self._format_amount(bono_amt, currency) if not should_hide_vacation else 'Ya han sido pagadas',
        'is_prepaid': should_hide_vacation,  # Flag for special rendering
    })
    benefit_num += 1

    # Other benefits (always show)
    benefits.append({
        'number': benefit_num,
        'name': 'Utilidades',
        # ...
    })
    benefit_num += 1
    # ... (Prestaciones, Antigüedad, Intereses)

    # Build deductions list (conditional)
    deductions = []
    deduction_num = 1

    # Other deductions (always show)
    # ... (FAOV, INCES, etc.)

    # Prepaid deduction (conditional)
    if not should_hide_vacation and abs(prepaid_amt) > 0.01:
        deductions.append({
            'number': deduction_num,
            'name': 'Vacaciones y Bono Prepagadas',
            'formula': 'Deducción por pago adelantado',
            'calculation': '...',
            'amount': prepaid_amt,
            'amount_formatted': self._format_amount(prepaid_amt, currency),
        })

    # Calculate displayed totals (adjust if hidden)
    if should_hide_vacation:
        total_benefits_display = sum(...) - (vac_amt + bono_amt)
        total_deductions_display = sum(...) - abs(prepaid_amt)
    else:
        total_benefits_display = sum(...)
        total_deductions_display = sum(...)

    # Generate explanatory note
    hidden_note = None
    if should_hide_vacation:
        period_text = f"{payslip.contract_id.date_start.strftime('%b %Y')} - {payslip.date_to.strftime('%b %Y')}"
        hidden_note = (
            f"Vacaciones y Bono Vacacional ya pagados mensualmente\n"
            f"Período: {period_text}\n"
            f"Monto total pagado: {currency.symbol}{abs(prepaid_amt):,.2f}"
        )

    return {
        'employee': payslip.employee_id,
        'contract': payslip.contract_id,
        'payslip': payslip,
        'benefits': benefits,
        'deductions': deductions,
        'total_benefits': total_benefits_display,
        'total_deductions': total_deductions_display,
        'net_amount': total_benefits_display + total_deductions_display,
        'is_vacation_hidden': should_hide_vacation,
        'hidden_vacation_note': hidden_note,
        'hidden_vacation_amount': abs(prepaid_amt) if should_hide_vacation else 0,
        # ... other fields ...
    }
```

### 4.5 PDF Report Template Changes

**File:** `addons/ueipab_payroll_enhancements/reports/liquidacion_breakdown_report.xml`

```xml
<!-- After NET AMOUNT section -->
<div class="row mt-3">
    <div class="col-12">
        <t t-if="report['is_vacation_hidden']">
            <div class="alert alert-info"
                 style="border: 2px solid #0c5460;
                        background-color: #d1ecf1;
                        padding: 15px;
                        border-radius: 5px;">
                <p style="margin: 0; font-size: 11pt; color: #0c5460;">
                    <strong>📝 NOTA IMPORTANTE:</strong><br/>
                    <t t-esc="report['hidden_vacation_note']"/>
                </p>
            </div>
        </t>
    </div>
</div>
```

### 4.6 XLSX Controller Changes

**File:** `addons/ueipab_payroll_enhancements/controllers/liquidacion_breakdown_xlsx.py`

```python
# Prepare data dict
data = {
    'wizard_id': wizard.id,
    'currency_id': wizard.currency_id.id,
    'currency_name': wizard.currency_id.name,
    'payslip_ids': wizard.payslip_ids.ids,
    'use_custom_rate': wizard.use_custom_rate,
    'custom_exchange_rate': wizard.custom_exchange_rate if wizard.use_custom_rate else None,
    'rate_date': wizard.rate_date,
    'hide_prepaid_vacation': wizard.hide_prepaid_vacation,  # ✅ NEW
}

# ... generate breakdown ...

# Add note if vacation hidden
if breakdown['is_vacation_hidden']:
    row += 2

    # Note format
    note_format = workbook.add_format({
        'align': 'left',
        'text_wrap': True,
        'bg_color': '#D1ECF1',
        'border': 2,
        'border_color': '#0C5460',
        'font_color': '#0C5460',
        'bold': True,
    })

    # Write note
    worksheet.merge_range(row, 0, row + 2, 3,
        f"📝 NOTA IMPORTANTE:\n{breakdown['hidden_vacation_note']}",
        note_format)
    worksheet.set_row(row, 60)  # Increase row height
```

---

## 5. Critical Constraints

### ✅ What MUST NOT Change

| Component | Requirement |
|-----------|-------------|
| **Salary Structure** | ALL formulas in `LIQUID_VE_V2` remain **unchanged** |
| **Payslip Lines** | `line_ids` must contain ALL calculated lines (no deletion) |
| **Net Calculation** | `LIQUID_NET_V2` = correct total (all benefits - all deductions) |
| **Accounting** | Journal entries, ledger postings remain **identical** |
| **Contract Fields** | `ueipab_vacation_prepaid_amount` tracking **unchanged** |
| **Bank Transfers** | Payment amounts to employees **unchanged** |

### 🎯 What Changes (Display Only)

| Component | Change Type |
|-----------|-------------|
| **Report Model** | Filters benefits/deductions list for display |
| **PDF Template** | Conditionally renders lines + adds note |
| **XLSX Controller** | Conditionally writes rows + adds note |
| **User Experience** | Simplified view (when enabled + fully prepaid) |

**Key Principle:** This is a **presentation layer change only**. All backend business logic, calculations, and accounting remain 100% unchanged.

---

## 6. Implementation Phases

### Phase 1: Wizard Field (1 hour)
**Deliverables:**
- ✅ Add `hide_prepaid_vacation` boolean field to wizard model
- ✅ Add field to wizard view with help text and alert
- ✅ Update `action_print_pdf()` to pass field in data dict
- ✅ Update `action_export_xlsx()` to pass field in data dict

**Testing:**
- Wizard displays field correctly
- Field value passed to report (verify in logs)
- Toggle ON/OFF works in UI

### Phase 2: Report Model Logic (2 hours)
**Deliverables:**
- ✅ Implement `is_fully_prepaid` detection logic
- ✅ Implement conditional benefit/deduction list building
- ✅ Add `is_vacation_hidden` and `hidden_vacation_note` to return dict
- ✅ Calculate adjusted totals when hidden

**Testing:**
- Test with fully prepaid payslip (net = $0)
  - Toggle ON → benefits list excludes Vac/Bono
  - Toggle OFF → benefits list includes all
- Test with partially prepaid (net ≠ $0)
  - Toggle ON → all lines shown (not hidden)
- Test with no prepaid
  - Toggle ON → all lines shown
- Test V1 vs V2 compatibility
- Test USD vs VEB currency
- Test edge cases (net = $0.001, net = -$0.001)

### Phase 3: PDF Template (1 hour)
**Deliverables:**
- ✅ Add conditional note section to QWeb template
- ✅ Style note with border, background color, icon
- ✅ Test rendering in both hidden/visible scenarios

**Testing:**
- Generate PDF with hidden vacation → note displays
- Generate PDF with visible vacation → no note
- Verify note text formatting and readability
- Test in Spanish locale

### Phase 4: XLSX Controller (1 hour)
**Deliverables:**
- ✅ Add note row generation when vacation hidden
- ✅ Style note cell (border, background, merged)
- ✅ Adjust row heights for readability

**Testing:**
- Generate XLSX with hidden vacation → note row added
- Generate XLSX with visible vacation → no note row
- Verify Excel formatting matches PDF style
- Test note text wrapping in Excel

### Phase 5: Testing & Documentation (1 hour)
**Deliverables:**
- ✅ Run full test suite (see Test Scenarios section)
- ✅ Update CLAUDE.md with feature description
- ✅ Create this plan document
- ✅ Bump version to v1.26.0 in `__manifest__.py`

**Testing:**
- All test scenarios pass (see section 7)
- Both PDF and XLSX produce identical output
- Feature works with all wizard options (rate override, etc.)

**Total Estimated Time:** 5-6 hours

---

## 7. Test Scenarios

### Test Matrix

| ID | Scenario | Vac | Bono | Prepaid | Net | Toggle | Expected Result |
|----|----------|-----|------|---------|-----|--------|-----------------|
| T1 | Fully prepaid, toggle ON | $500 | $650 | -$1,150 | $0 | ✅ ON | ❌ Hidden + Note |
| T2 | Fully prepaid, toggle OFF | $500 | $650 | -$1,150 | $0 | ❌ OFF | ✅ Show all |
| T3 | Partially prepaid | $500 | $650 | -$800 | $350 | ✅ ON | ✅ Show all |
| T4 | Not prepaid | $500 | $650 | $0 | $1,150 | ✅ ON | ✅ Show all |
| T5 | Rounding edge case | $500 | $650 | -$1,150.01 | -$0.01 | ✅ ON | ✅ Show all (not within tolerance) |
| T6 | Tiny rounding difference | $500 | $650 | -$1,149.99 | $0.01 | ✅ ON | ❌ Hidden (within tolerance) |
| T7 | VEB currency | $500 | $650 | -$1,150 | $0 | ✅ ON | ❌ Hidden (VEB amounts) |
| T8 | V1 structure | $500 | $650 | -$1,150 | $0 | ✅ ON | ❌ Hidden (V1 codes) |
| T9 | Exchange rate override | $500 | $650 | -$1,150 | $0 | ✅ ON | ❌ Hidden (custom rate) |
| T10 | Multiple payslips | Mixed | Mixed | Mixed | Mixed | ✅ ON | Each handled independently |

### Detailed Test Cases

#### T1: Fully Prepaid, Toggle ON (Primary Use Case)
```
Setup:
  - Employee: MAGYELYS MATA
  - Payslip: SLIP/806 (LIQUID_VE_V2)
  - Vacaciones: $122.57
  - Bono: $149.27
  - Prepaid: -$271.84
  - Net: $0.00
  - Wizard: hide_prepaid_vacation = True
  - Currency: VEB (rate 236.46)

Expected PDF Output:
  BENEFITS:
    1. Utilidades
    2. Prestaciones Sociales
    3. Antigüedad
    4. Intereses
    [NO Vacaciones]
    [NO Bono Vacacional]

  DEDUCTIONS:
    - FAOV
    - INCES
    [NO Prepaid]

  NOTE:
    📝 Vacaciones y Bono Vacacional ya pagados mensualmente
       Período: Sep 2023 - Jul 2025
       Monto: Bs. 64,243.27

Expected XLSX Output:
  - Same structure as PDF
  - Note in merged cell with blue background
```

#### T3: Partially Prepaid (Edge Case)
```
Setup:
  - Vacaciones: $500.00
  - Bono: $650.00
  - Prepaid: -$800.00
  - Net: $350.00 (employee is still owed $350)
  - Wizard: hide_prepaid_vacation = True

Expected Result:
  - SHOW all lines (Vacaciones, Bono, Prepaid)
  - NO note added
  - Rationale: Net is not zero, employee has money coming
```

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Users confused by "missing" lines** | Medium | Medium | Clear note explains what happened and shows amount paid |
| **Accounting disputes** | Low | High | Toggle OFF by default (opt-in). When ON, note provides transparency |
| **Incorrect net calculation** | Very Low | Critical | Display-only change, NO formula modifications. Net = same as payslip |
| **V1/V2 compatibility issues** | Low | Medium | Code checks for both V2 and V1 rule codes, graceful fallback |
| **Currency conversion errors** | Very Low | Medium | Uses same `_convert_currency()` method as other lines |
| **Excel formatting issues** | Low | Low | Test XLSX output extensively, ensure note cell wraps properly |
| **Rounding errors cause incorrect hiding** | Low | Medium | Use 0.01 tolerance, test edge cases (T5, T6) |

---

## 9. Open Questions

### For Business Review

1. **Default Behavior**
   - ❓ Should `hide_prepaid_vacation` default to **OFF** (show all) or **ON** (hide if prepaid)?
   - 💡 Recommendation: **OFF** (conservative, opt-in feature)

2. **Note Text**
   - ❓ Current draft: *"Vacaciones y Bono Vacacional ya pagados mensualmente. Período: [dates]. Monto: $X,XXX"*
   - ❓ Should we add more explanation? Less?
   - 💡 Consider: "Estos montos ya fueron pagados mensualmente durante el período de empleo y no forman parte del monto neto a reclamar."

3. **Tolerance Threshold**
   - ❓ Use $0.01 USD tolerance for "fully prepaid" detection?
   - ❓ Or stricter (e.g., $0.001)?
   - 💡 Recommendation: $0.01 (accounts for typical rounding in payroll)

4. **V1 Compatibility**
   - ❓ Should this feature work for V1 liquidations (`LIQUID_VE`)?
   - ❓ Or V2 only (`LIQUID_VE_V2`)?
   - 💡 Recommendation: Both (code already checks both sets of rule codes)

5. **Accounting Sign-off**
   - ❓ Does accounting approve this approach?
   - ❓ Any legal concerns about "hiding" lines from reports?
   - 💡 Note provides full transparency and audit trail

### For Technical Review

6. **Performance Impact**
   - ❓ Any concerns about additional logic in report generation?
   - 💡 Impact: Negligible (just conditional list filtering)

7. **Future Enhancements**
   - ❓ Should we track which reports used this feature (audit log)?
   - ❓ Should we add a similar feature for other benefits?
   - 💡 Consider: Start simple, add if requested

---

## 10. Approval Checklist

- [ ] Business team approves concept
- [ ] Accounting team approves approach
- [ ] Default value decided (ON or OFF)
- [ ] Note text finalized
- [ ] Tolerance threshold approved
- [ ] V1 compatibility decided
- [ ] Development team ready to implement

---

## 11. Implementation Timeline

**Target Version:** v1.26.0
**Estimated Effort:** 5-6 hours
**Target Completion:** TBD (pending approval)

**Phase Breakdown:**
- Phase 1 (Wizard): 1 hour
- Phase 2 (Logic): 2 hours
- Phase 3 (PDF): 1 hour
- Phase 4 (XLSX): 1 hour
- Phase 5 (Testing): 1 hour

**Dependencies:**
- None (standalone feature)

**Blockers:**
- Awaiting business approval
- Awaiting answers to open questions

---

## Appendix A: Code Files to Modify

| File | Changes | LOC |
|------|---------|-----|
| `models/liquidacion_breakdown_wizard.py` | Add field, update actions | +10 |
| `wizard/liquidacion_breakdown_wizard_view.xml` | Add field to form | +8 |
| `models/liquidacion_breakdown_report.py` | Add hiding logic | +50 |
| `reports/liquidacion_breakdown_report.xml` | Add note section | +12 |
| `controllers/liquidacion_breakdown_xlsx.py` | Add note row | +20 |
| `__manifest__.py` | Bump version | +1 |
| `CLAUDE.md` | Document feature | +10 |

**Total:** ~111 lines of code

---

## Appendix B: Visual Mockups

### Before (Current Behavior)
```
┌────────────────────────────────────────┐
│ PRESTACIONES SOCIALES (BENEFICIOS)     │
├────────────────────────────────────────┤
│ 1. Vacaciones            Bs. 28,912.34 │
│ 2. Bono Vacacional       Bs. 35,330.93 │
│ 3. Utilidades            Bs. 37,450.12 │
│ 4. Prestaciones          Bs. 175,923.88│
│ 5. Antigüedad            Bs. 73,568.90 │
│ 6. Intereses             Bs. 8,704.47  │
│────────────────────────────────────────│
│ SUBTOTAL:                Bs. 359,890.64│
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ DEDUCCIONES                            │
├────────────────────────────────────────┤
│ - FAOV (1%)              Bs. -1,465.03 │
│ - INCES (0.5%)           Bs. -187.87   │
│ - Vac/Bono Prepagadas    Bs.-64,243.27 │
│────────────────────────────────────────│
│ TOTAL DEDUCCIONES:       Bs.-65,896.17 │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ NETO A RECLAMAR:         Bs. 293,994.47│
└────────────────────────────────────────┘

❓ Employee confused: "Why Bs. 64K benefit then -64K deduction?"
```

### After (With "Ya han sido pagadas" Feature Enabled) ✅ REVISED
```
┌────────────────────────────────────────┐
│ PRESTACIONES SOCIALES (BENEFICIOS)     │
├────────────────────────────────────────┤
│ 1. Vacaciones            Ya han sido pagadas │
│ 2. Bono Vacacional       Ya han sido pagadas │
│ 3. Utilidades            Bs. 37,450.12 │
│ 4. Prestaciones          Bs. 175,923.88│
│ 5. Antigüedad            Bs. 73,568.90 │
│ 6. Intereses             Bs. 8,704.47  │
│────────────────────────────────────────│
│ SUBTOTAL:                Bs. 295,647.37│
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ DEDUCCIONES                            │
├────────────────────────────────────────┤
│ - FAOV (1%)              Bs. -1,465.03 │
│ - INCES (0.5%)           Bs. -187.87   │
│────────────────────────────────────────│
│ TOTAL DEDUCCIONES:       Bs. -1,652.90 │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ NETO A RECLAMAR:         Bs. 293,994.47│
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ 📝 NOTA:                               │
│ • Vacaciones y Bono Vacacional pagados │
│   mensualmente durante período de      │
│   empleo (Sep 2023 - Jul 2025)        │
│   Monto total: Bs. 64,243.27          │
└────────────────────────────────────────┘

✅ BENEFITS:
   • Consistent layout (all reports have 1-6 structure)
   • Clear status ("Ya han sido pagadas")
   • Easy to compare across different employees
   • Professional appearance (standard accounting)
   • No confusion about "missing" lines
```

---

**Document Status:** 📋 Draft - Awaiting Review
**Next Action:** Business team review and answer open questions
**Contact:** Development Team
