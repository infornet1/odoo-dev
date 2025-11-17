# Relación de Liquidación Report - Implementation Plan

**Date:** 2025-11-17
**Purpose:** Create detailed liquidation breakdown report showing all formula calculations
**Based on:** Google Spreadsheet manual layout (Dixia Bellorin tab)

---

## Report Specifications

**Report Name:** Relación de Liquidación (Liquidation Breakdown Report)
**Location:** Reporting menu (above "Prestaciones Soc. Intereses")
**Page Format:**
- Size: Letter (8.5" x 11")
- Orientation: Portrait
- Target: Fit on 1 page
- Font: 8-10pt data, 12-14pt headers

---

## Report Structure

### HEADER SECTION
```
UNIVERSIDAD EXPERIMENTAL POLITECNICA ANTONIO JOSÉ DE SUCRE
RELACIÓN DE LIQUIDACIÓN

Employee: DIXIA BELLORIN
ID Number: [employee_id]
Department: Docentes
Position: [job_position]

Contract Start: 2023-09-01
Liquidation Date: 2025-07-31
Service Period: 23 months (1 year, 11 months)
```

---

### SECTION 1: PRESTACIONES SOCIALES (BENEFITS)

| # | Concept | Formula / Description | Calculation | Amount USD |
|---|---------|----------------------|-------------|-----------|
| 1 | **Vacaciones** | 15 días/año × salario diario | (23.30/12) × 15 × $4.26 = 20.0 días × $4.26 | $85.20 |
| 2 | **Bono Vacacional** | Progresivo según antigüedad (26.9 días/año) × salario diario | (23.30/12) × 26.9 × $4.26 = 35.9 días × $4.26 | $152.97 |
| 3 | **Utilidades** | 30 días/año × salario diario | (23.30/12) × 30 × $4.26 = 58.3 días × $4.26 | $248.36 |
| 4 | **Prestaciones Sociales** | 15 días/trimestre × salario integral | (23.30/3) × 15 × $5.89 = 116.5 días × $5.89 | $686.19 |
| 5 | **Antigüedad** | 2 días/mes (desde fecha original) - ya pagados | Total: 155.0 meses × 2 = 310.0 días<br>Ya pagados: 265.7 días<br>Neto: 44.3 días × $5.89 | $260.95 |
| 6 | **Intereses Prestaciones** | 13% anual × saldo promedio prestaciones | $686.19 × 0.5 × 0.13 × (23.30/12) | $86.62 |
| | | | **SUBTOTAL PRESTACIONES:** | **$1,520.29** |

**Key Calculations:**
- **Salario Diario:** $127.66 ÷ 30 = **$4.26/día**
- **Salario Integral Diario:** $4.26 + ($248.36 ÷ 58.3) + ($152.97 ÷ 35.9) = **$5.89/día**
- **Antigüedad Original Hire:** 2012-09-01 (155 meses de antigüedad total)
- **Antigüedad Ya Pagada:** Hasta 2023-07-31 (265.7 días)
- **Bono Vacacional Rate:** 13.25 años → 15 + (13.25 - 1) = **26.9 días/año**

---

### SECTION 2: DEDUCCIONES (DEDUCTIONS)

| # | Concept | Formula / Description | Calculation | Amount USD |
|---|---------|----------------------|-------------|-----------|
| 1 | **FAOV** | 1% sobre (Vacaciones + Bono + Utilidades) | ($85.20 + $152.97 + $248.36) × 1% | -$4.87 |
| 2 | **INCES (PARO)** | 0.5% sobre (Vacaciones + Bono + Utilidades) | ($85.20 + $152.97 + $248.36) × 0.5% | -$2.43 |
| 3 | **Vacaciones/Bono Prepagadas** | Deducción por pago adelantado (Aug 1, 2024) | Período prepagado desde 2024-08-01 | -$238.17 |
| | | | **SUBTOTAL DEDUCCIONES:** | **-$245.47** |

**Deduction Notes:**
- FAOV and INCES apply only to Vacaciones, Bono Vacacional, and Utilidades
- Prestaciones, Antigüedad, and Intereses are **exempt** from FAOV/INCES
- Prepaid deduction applies if employee received Aug 1 annual vacation payment

---

### FOOTER: NET AMOUNT

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  TOTAL PRESTACIONES SOCIALES:        $1,520.29     │
│  TOTAL DEDUCCIONES:                   ($245.47)    │
│  ─────────────────────────────────────────────     │
│  NETO A RECLAMAR:                    $1,274.82     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### 1. Wizard Model
**File:** `addons/ueipab_payroll_enhancements/wizard/liquidation_breakdown_wizard.py`

```python
class LiquidacionBreakdownWizard(models.TransientModel):
    _name = 'liquidacion.breakdown.wizard'
    _description = 'Relación de Liquidación Wizard'

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Liquidation Payslips',
        domain="[('struct_id.name', 'in', ['Liquidación Venezolana', 'Liquidación Venezolana V2']), ('state', 'in', ['done', 'paid'])]",
    )
```

### 2. Report Model
**File:** `addons/ueipab_payroll_enhancements/models/liquidacion_breakdown_report.py`

```python
class LiquidacionBreakdownReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.liquidacion_breakdown'

    def _get_report_values(self, docids, data=None):
        # Get payslip data
        # Extract all V2 (or V1) rule values
        # Calculate derived values (daily rates, etc.)
        # Format formulas for display
        # Return structured data for template
```

### 3. QWeb Template
**File:** `addons/ueipab_payroll_enhancements/reports/liquidacion_breakdown_report.xml`

**Layout Features:**
- Portrait Letter format
- 2-column table for benefits (description | amount)
- Formula explanations in description column
- Clear section headers
- Highlighted net total at bottom
- Compact font (9-10pt) to fit on 1 page

---

## Data Sources (V2 Liquidation Rules)

From payslip.line_ids, we need:

**Service/Base Data:**
- `LIQUID_SERVICE_MONTHS_V2` → Service months
- `LIQUID_DAILY_SALARY_V2` → Daily salary ($4.26)
- `LIQUID_INTEGRAL_DAILY_V2` → Integral daily salary ($5.89)

**Benefits:**
- `LIQUID_VACACIONES_V2` → Vacation amount
- `LIQUID_BONO_VACACIONAL_V2` → Vacation bonus amount
- `LIQUID_UTILIDADES_V2` → Profit sharing amount
- `LIQUID_PRESTACIONES_V2` → Social benefits amount
- `LIQUID_ANTIGUEDAD_V2` → Seniority amount
- `LIQUID_INTERESES_V2` → Interest amount

**Deductions:**
- `LIQUID_FAOV_V2` → FAOV deduction
- `LIQUID_INCES_V2` → INCES deduction
- `LIQUID_VACATION_PREPAID_V2` → Prepaid vacation deduction

**Totals:**
- `LIQUID_NET_V2` → Net liquidation amount

---

## Formula Display Format

For each benefit line, show:

**Example - Vacaciones:**
```
Vacaciones
15 días por año × salario diario
Cálculo: (23.30 meses / 12) × 15 días × $4.26
Resultado: 20.0 días × $4.26 = $85.20
```

This gives transparency on:
1. What the benefit is
2. What the formula is
3. How it was calculated with actual numbers
4. Final amount

---

## Report Action (Menu Entry)

**File:** `addons/ueipab_payroll_enhancements/views/payroll_reports_menu.xml`

```xml
<record id="action_liquidacion_breakdown_wizard" model="ir.actions.act_window">
    <field name="name">Relación de Liquidación</field>
    <field name="res_model">liquidacion.breakdown.wizard</field>
    <field name="view_mode">form</field>
    <field name="target">new</field>
</record>

<menuitem id="menu_liquidacion_breakdown_report"
          name="Relación de Liquidación"
          parent="menu_payroll_reports"
          action="action_liquidacion_breakdown_wizard"
          sequence="15"/>
```

---

## Expected Output Example

**For DIXIA BELLORIN (SLIP/797):**

- Service: 23.30 months (Sep 2023 - Jul 2025)
- Original Hire: 2012-09-01 (13.25 years total)
- Salary V2: $127.66
- Daily Rate: $4.26
- Integral Daily: $5.89

**Benefits Breakdown:**
1. Vacaciones: $85.20
2. Bono Vacacional: $152.97 (26.9 days/year rate for 13 years)
3. Utilidades: $248.36
4. Prestaciones: $686.19
5. Antigüedad: $260.95 (net after 265.7 days already paid)
6. Intereses: $86.62

**Deductions:**
1. FAOV: -$4.87
2. INCES: -$2.43
3. Prepaid: -$238.17

**Net:** $1,274.82

---

## Implementation Checklist

- [ ] Create wizard model (`liquidacion_breakdown_wizard.py`)
- [ ] Create wizard view (`liquidacion_breakdown_wizard_view.xml`)
- [ ] Create report model (`liquidacion_breakdown_report.py`)
- [ ] Create QWeb template (`liquidacion_breakdown_report.xml`)
- [ ] Add report action to menu
- [ ] Test with SLIP/797 (DIXIA BELLORIN)
- [ ] Test with SLIP/795 (VIRGINIA VERDE)
- [ ] Test with SLIP/796 (GABRIEL ESPAÑA)
- [ ] Verify formulas display correctly
- [ ] Verify fits on 1 page (portrait letter)
- [ ] Add to module `__manifest__.py`
- [ ] Upgrade module
- [ ] Documentation

---

## Status

**Phase:** Planning Complete
**Ready to Implement:** ✅ Yes
**Estimated Time:** 60-90 minutes

**Awaiting user approval to proceed with implementation.**

---

**Last Updated:** 2025-11-17
