# AR-I Portal Feature Research

**Date:** 2025-11-26
**Status:** Research Complete
**Module:** `ueipab_payroll_enhancements` (planned enhancement)

---

## Executive Summary

The AR-I (Agente de Retención - Impuesto sobre la Renta) is a Venezuelan tax form where employees declare their estimated annual income and deductions to calculate their ISLR (Income Tax) withholding percentage. This document outlines the research for implementing an employee self-service portal to manage AR-I submissions.

---

## AR-I Form Structure (Official SENIAT Format)

Based on analysis of the official SENIAT Excel form (`ARI SENIAT FORMATO.xlsx`):

### Section 1-3: Personal Information (Auto-filled)

| Field | Cell | Description | Portal Handling |
|-------|------|-------------|-----------------|
| Apellidos y Nombres | A14 | Full name | Auto from `hr.employee.name` |
| Cédula Tipo | I14 | V/E/P | Auto from `hr.employee.identification_id` |
| Cédula Número | K14 | ID number | Auto from `hr.employee.identification_id` |
| RIF Tipo | S14 | V/E/J/G/P/C | Auto from `hr.employee.rif` or derived |
| RIF Número | T14 | RIF number | Auto from `hr.employee.rif` |

### Section 4: Employers (Up to 4)

| Field | Cell | Description |
|-------|------|-------------|
| Empresa a | A18 | Primary employer (UEIPAB) |
| Empresa b | A20 | Secondary employer |
| Empresa c | G18 | Third employer |
| Empresa d | G20 | Fourth employer |

**Portal Note:** UEIPAB is auto-filled as primary. Employee can add other employers if they have multiple jobs.

### Section 5: Variation Months

| Month | Cell | Deadline |
|-------|------|----------|
| Marzo | P19 | Before March 15 |
| Junio | Q19 | Before June 15 |
| Septiembre | R19 | Before September 15 |
| Diciembre | S19 | Before December 15 |

**Portal Note:** Auto-selected based on current date when submitting variation.

### Section 6: Tax Year

Auto-filled with current fiscal year.

---

## Section A: Estimated Remuneration

Employee estimates annual income from all sources:

| Field | Cell | Description | Portal Source |
|-------|------|-------------|---------------|
| Cantidad empresa a | C26 | Income from employer A | Auto from contract × 12 |
| Cantidad empresa b | C28 | Income from employer B | Manual entry |
| Cantidad empresa c | L26 | Income from employer C | Manual entry |
| Cantidad empresa d | L28 | Income from employer D | Manual entry |
| **TOTAL A** | T29 | Sum of all income | Auto-calculated |

**Income Components to Include:**
- Salario base mensual × 12
- Bono vacacional
- Utilidades (Aguinaldos)
- Horas extras estimadas
- Comisiones
- Otros bonos
- Pensiones

---

## Section B: Conversion to UT (Tax Units)

| Field | Cell | Formula |
|-------|------|---------|
| Total Remuneraciones | D32 | = A |
| Valor UT año gravable | I32 | Current UT value (Bs. 9.00 for 2024) |
| **TOTAL B** | T32 | = A ÷ UT Value |

---

## Section C: Itemized Deductions (Desgravámenes Detallados)

**Option 2 - If employee chooses itemized deductions:**

| # | Field | Cell | Max Limit | Requires Proof |
|---|-------|------|-----------|----------------|
| 1 | Institutos Docentes (Educación) | T36 | Unlimited | Yes |
| 2 | Primas Seguros (HCM, Vida, Maternidad) | T37 | Unlimited | Yes |
| 3 | Servicios Médicos/Odontológicos | T38 | Unlimited | Yes |
| 4 | Intereses Vivienda Principal | T39 | 1,000 UT (mortgage) / 800 UT (rent) | Yes |
| **TOTAL C** | T40 | Sum of 1-4 | - | - |

---

## Section D: Conversion of Deductions to UT

| Field | Cell | Formula |
|-------|------|---------|
| Total Desgravámenes | D43 | = C |
| Valor UT | I43 | Same as B |
| **TOTAL D** | T43 | = C ÷ UT Value |

---

## Section E: Unique Deduction (Desgravamen Único)

**Option 1 - Fixed deduction (no proof required):**

| Field | Cell | Value |
|-------|------|-------|
| Desgravamen Único (Art. 61 LISLR) | T45 | **774 UT** |

**Portal Note:** Employee selects ONE option:
- Option 1: Desgravamen Único (774 UT) - No documentation needed
- Option 2: Desgravámenes Detallados (Section C) - Must provide receipts

---

## Section F: Taxable Income (Enriquecimiento Gravable)

| Field | Cell | Formula |
|-------|------|---------|
| Remuneraciones (B) | B47 | = B |
| Desgravámenes (D or E) | G47 | = IF(D=0, E, D) |
| **TOTAL F** | T47 | = B - Desgravámenes |

---

## Section G: Estimated Tax Calculation

Uses progressive tax rates table:

| Range (UT) | Rate | Sustraendo |
|------------|------|------------|
| 0 - 1,000 | 6% | 0 |
| 1,000 - 1,500 | 9% | 30 UT |
| 1,500 - 2,000 | 12% | 75 UT |
| 2,000 - 2,500 | 16% | 155 UT |
| 2,500 - 3,000 | 20% | 255 UT |
| 3,000 - 4,000 | 24% | 375 UT |
| 4,000 - 6,000 | 29% | 575 UT |
| > 6,000 | 34% | 875 UT |

**Formula (Cell T52):**
```
IF(F <= 1000, F × 6%,
IF(F <= 1500, F × 9% - 30,
IF(F <= 2000, F × 12% - 75,
IF(F <= 2500, F × 16% - 155,
IF(F <= 3000, F × 20% - 255,
IF(F <= 4000, F × 24% - 375,
IF(F <= 6000, F × 29% - 575,
              F × 34% - 875)))))))
```

---

## Section H: Tax Reductions (Rebajas)

| # | Field | Cell | Value (UT) | Description |
|---|-------|------|------------|-------------|
| 1 | Rebaja Personal | K54 | **10 UT** | All residents (automatic) |
| 2 | Carga Familiar | K55 | **10 UT × count** | Dependents (see below) |
| 3 | Impuestos retenidos de más | K57 | Variable | Prior year excess withholding |
| **TOTAL H** | T58 | Sum | = 1 + 2 + 3 |

### Cargas Familiares (Dependents) - 10 UT each:

| Type | Requirements |
|------|--------------|
| Cónyuge | Legally married, not separated |
| Hijos menores de 25 años | Under 25, studying or unemployed |
| Hijos discapacitados | Any age, with disability certificate |
| Ascendientes (padres) | Financially dependent on employee |

**Portal Note:** Employee enters count of each dependent type. Must maintain documentation.

---

## Section I: Tax to Withhold

| Field | Cell | Formula |
|-------|------|---------|
| **TOTAL I** | T59 | = MAX(0, G - H) |

If G (tax) is less than H (reductions), result is 0 (no withholding).

---

## Section J: Initial Withholding Percentage

| Field | Cell | Formula |
|-------|------|---------|
| **Porcentaje J** | Q62 | = (I ÷ B) × 100 |

**This is the final result** - the percentage employer must withhold from each paycheck.

---

## Section K: Variation Calculation (If Updating)

Only completed when submitting a variation (March, June, September, December):

| # | Field | Cell | Description |
|---|-------|------|-------------|
| 1 | Total retenido hasta la fecha | T68 | YTD withholdings |
| 2 | Total remuneraciones percibidas | T69 | YTD income received |

**Variation Percentage Formula:**
```
K% = ((I × UT) - K1) / (A - K2) × 100
```

---

## Sections L & M: Signatures

| Section | Party | Fields |
|---------|-------|--------|
| L | Contribuyente (Employee) | Lugar, Fecha, Firma |
| M | Agente de Retención (HR) | Lugar, Fecha, Firma |

---

## Proposed Odoo Implementation

### New Model: `hr.employee.ari`

```python
class HrEmployeeARI(models.Model):
    _name = 'hr.employee.ari'
    _description = 'Employee AR-I Tax Declaration'
    _order = 'fiscal_year desc, submission_date desc'

    # Header
    employee_id = fields.Many2one('hr.employee', required=True)
    fiscal_year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
    submission_date = fields.Date(default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved by HR'),
        ('rejected', 'Rejected')
    ], default='draft')

    # Variation
    is_variation = fields.Boolean(default=False)
    variation_month = fields.Selection([
        ('january', 'Enero (Inicial)'),
        ('march', 'Marzo'),
        ('june', 'Junio'),
        ('september', 'Septiembre'),
        ('december', 'Diciembre')
    ])

    # Section A - Income Estimation
    income_employer_primary = fields.Float(string="Ingreso UEIPAB Anual")
    income_employer_b = fields.Float(string="Ingreso Empleador B")
    income_employer_c = fields.Float(string="Ingreso Empleador C")
    income_employer_d = fields.Float(string="Ingreso Empleador D")
    income_total = fields.Float(compute='_compute_income_total', store=True)

    # Section B - UT Conversion
    ut_value = fields.Float(string="Valor UT", default=9.00)  # Current UT
    income_in_ut = fields.Float(compute='_compute_income_ut', store=True)

    # Section C/E - Deductions Selection
    deduction_type = fields.Selection([
        ('unique', 'Desgravamen Único (774 UT)'),
        ('itemized', 'Desgravámenes Detallados')
    ], default='unique', required=True)

    # Section C - Itemized Deductions (if selected)
    deduction_education = fields.Float(string="1. Educación")
    deduction_insurance = fields.Float(string="2. Seguros (HCM, Vida)")
    deduction_medical = fields.Float(string="3. Gastos Médicos")
    deduction_housing = fields.Float(string="4. Vivienda Principal")
    deduction_housing_type = fields.Selection([
        ('mortgage', 'Hipoteca (máx 1,000 UT)'),
        ('rent', 'Alquiler (máx 800 UT)')
    ])
    deductions_total = fields.Float(compute='_compute_deductions', store=True)
    deductions_in_ut = fields.Float(compute='_compute_deductions_ut', store=True)

    # Section H - Rebajas (Tax Reductions)
    rebaja_personal = fields.Float(default=10.0, readonly=True)  # Always 10 UT
    rebaja_spouse = fields.Boolean(string="Cónyuge")
    rebaja_children_under_25 = fields.Integer(string="Hijos < 25 años")
    rebaja_children_disabled = fields.Integer(string="Hijos discapacitados")
    rebaja_parents = fields.Integer(string="Ascendientes")
    rebaja_prior_excess = fields.Float(string="Retención exceso año anterior")
    rebajas_total_ut = fields.Float(compute='_compute_rebajas', store=True)

    # Section K - Variation Data (if applicable)
    ytd_withholding = fields.Float(string="Total retenido hasta la fecha")
    ytd_income = fields.Float(string="Total remuneraciones percibidas")

    # Calculated Results
    taxable_income_ut = fields.Float(compute='_compute_tax', store=True)
    estimated_tax_ut = fields.Float(compute='_compute_tax', store=True)
    tax_after_rebajas = fields.Float(compute='_compute_tax', store=True)
    withholding_percentage = fields.Float(compute='_compute_percentage', store=True,
                                          string="Porcentaje Retención (%)")

    # Attachments (for itemized deductions)
    attachment_ids = fields.Many2many('ir.attachment', string="Documentos Soporte")

    # HR Review
    reviewed_by = fields.Many2one('res.users')
    review_date = fields.Date()
    review_notes = fields.Text()
```

### Portal View Features

1. **Dashboard Widget:**
   - Current withholding percentage
   - Next update deadline with countdown
   - Alert if update overdue

2. **AR-I Form Wizard:**
   - Step 1: Review personal info (auto-filled)
   - Step 2: Income estimation (auto-calculated from contract + manual other income)
   - Step 3: Deduction selection (unique vs itemized)
   - Step 4: Family dependents declaration
   - Step 5: Review & submit
   - Step 6: PDF generation for signature

3. **History View:**
   - All past AR-I submissions
   - Current active declaration
   - Status tracking

### Automatic Notifications

```python
# Cron job: Check AR-I deadlines
def _cron_ari_deadline_reminder(self):
    deadlines = {
        3: 1,   # March 15 - remind March 1
        6: 1,   # June 15 - remind June 1
        9: 1,   # September 15 - remind September 1
        12: 1,  # December 15 - remind December 1
    }
    today = fields.Date.today()
    if today.month in deadlines and today.day == deadlines[today.month]:
        # Send reminder to all employees
        employees = self.env['hr.employee'].search([('active', '=', True)])
        for emp in employees:
            # Check if they have submitted for this quarter
            # Send email reminder if not
            pass
```

---

## Implementation Phases

### Phase 1: Core Model & Backend
- Create `hr.employee.ari` model
- Implement calculation logic
- Add fields to `hr.contract` for integration

### Phase 2: Portal Interface
- Employee self-service form
- PDF generation matching SENIAT format
- File upload for itemized deductions

### Phase 3: HR Management
- Approval workflow
- Bulk review interface
- Integration with payroll deductions

### Phase 4: Automation
- Deadline reminders (cron)
- Auto-calculation from contract data
- Historical tracking

---

## Legal References

- **Decreto Nº 1.808** (Gaceta Oficial 36.203, May 12, 1997)
- **Ley de ISLR** - Artículos 57 (desgravámenes), 59 (rebajas), 61 (desgravamen único)
- **Reglamento Parcial LISLR** - Articles 5-7 (withholding procedures)

---

## Current UEIPAB Integration

The module already has:
- `ueipab_ari_withholding_rate` field on `hr.contract`
- AR-I percentage used in `VE_ARI_DED_V2` salary rule
- Display in "Comprobante de Pago (Compacto)" report

**Next Step:** Connect the new AR-I portal to update `ueipab_ari_withholding_rate` when HR approves a submission.
