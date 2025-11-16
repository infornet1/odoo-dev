from odoo import api, fields, models


class HrContract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    # Venezuelan Compensation Fields
    ueipab_salary_base = fields.Monetary(
        'Salary (70%)',
        help="70% of total compensation - Base salary component"
    )
    ueipab_bonus_regular = fields.Monetary(
        'Bonus (25%)',
        help="25% of total compensation - Regular bonus including benefits"
    )
    ueipab_extra_bonus = fields.Monetary(
        'Extra Bonus (5%)',
        help="5% of total compensation - Extra performance bonus"
    )
    cesta_ticket_usd = fields.Monetary(
        'Cesta Ticket (USD)',
        default=40.0,
        help="Monthly food allowance in USD"
    )
    wage_ves = fields.Monetary(
        'Wage (VES)',
        help="Total wage amount in Venezuelan Bolivars"
    )

    # Venezuelan Deduction Base
    ueipab_deduction_base = fields.Monetary(
        'Deduction Base (K+L)',
        help="Original Column K + L value used for calculating monthly deductions. "
             "This is the base amount BEFORE 70/25/5 distribution and BEFORE extracting Cesta Ticket. "
             "Deductions (IVSS, FAOV, INCES, ARI) are calculated on this amount per spreadsheet logic. "
             "Formula: deduction_base = Column K + Column L (from payroll spreadsheet)"
    )

    # ==========================================================================
    # V2 COMPENSATION BREAKDOWN - VENEZUELAN PAYROLL
    # ==========================================================================
    # Purpose: Transparent salary structure with clear deduction base
    # Replaces: Confusing V1 percentage calculations (70%, 25%, 5%)
    # Legal: CEO confirmed full compliance with Venezuelan labor law (2025-11-16)
    # Strategy: Parallel V1/V2 operation (V1 fields remain untouched)
    # Data Source: Google Spreadsheet columns K, L, M (100% validated)
    # ==========================================================================

    ueipab_salary_v2 = fields.Monetary(
        string='Salary V2 (Deductible)',
        currency_field='currency_id',
        tracking=True,              # Track field changes in chatter
        copy=False,                 # Don't copy when duplicating contract
        groups='hr.group_hr_user',  # Require HR user access
        index=True,                 # Database index for faster queries
        required=False,             # Optional (supports V1/V2 parallel operation)
        help='Monthly base salary subject to mandatory Venezuelan social security '
             'deductions (SSO 4%%, FAOV 1%%, PARO 0.5%%, ARI variable%%).\n\n'
             'This is the ONLY component subject to payroll deductions per Venezuelan labor law.\n\n'
             '🔹 SOURCE: Imported from Google Spreadsheet Column K (SALARIO MENSUAL MAS BONO)\n'
             '🔹 SPREADSHEET: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s, Tab "15nov2025"\n'
             '🔹 APPLIES TO: Salary Structure "Salarios Venezuela UEIPAB V2"\n'
             '🔹 DEDUCTIONS: SSO, FAOV, PARO, ARI (prorated by actual payslip period days/30)\n'
             '🔹 LEGAL BASIS: LOTTT, IVSS, BANAVIH, INCES regulations\n'
             '🔹 CEO APPROVED: 2025-11-16 (Option A deduction approach with proration)\n\n'
             'PRORATION FORMULA:\n'
             '  Monthly deduction = salary_v2 × rate (e.g., 4%% SSO)\n'
             '  Payslip deduction = monthly_deduction × (period_days / 30.0)\n\n'
             'EXAMPLE (Rafael Perez, 15-day payslip):\n'
             '  salary_v2 = $119.09 monthly\n'
             '  SSO = $119.09 × 4%% × (15/30) = $2.38'
    )

    ueipab_extrabonus_v2 = fields.Monetary(
        string='Extra Bonus V2 (Non-Deductible)',
        currency_field='currency_id',
        tracking=True,
        copy=False,
        groups='hr.group_hr_user',
        index=True,
        required=False,
        help='Monthly extra bonus NOT subject to mandatory social security deductions.\n\n'
             'This component is exempt from SSO, FAOV, PARO, and ARI deductions per Venezuelan labor law.\n\n'
             '🔹 SOURCE: Imported from Google Spreadsheet Column L (OTROS BONOS)\n'
             '🔹 SPREADSHEET: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s, Tab "15nov2025"\n'
             '🔹 APPLIES TO: Salary Structure "Salarios Venezuela UEIPAB V2"\n'
             '🔹 DEDUCTIONS: None (exempt from all mandatory deductions)\n'
             '🔹 PRORATION: Yes (by actual payslip period days/30)\n'
             '🔹 CEO APPROVED: 2025-11-16\n\n'
             'NOTE: Only 4 employees have ExtraBonus values:\n'
             '  - SERGIO MANEIRO, ANDRES MORALES, PABLO NAVARRO, RAFAEL PEREZ\n'
             '  All other employees have $0.00 in this field.'
    )

    ueipab_bonus_v2 = fields.Monetary(
        string='Bonus V2 (Non-Deductible)',
        currency_field='currency_id',
        tracking=True,
        copy=False,
        groups='hr.group_hr_user',
        index=True,
        required=False,
        help='Monthly regular bonus NOT subject to mandatory social security deductions.\n\n'
             'This component is exempt from SSO, FAOV, PARO, and ARI deductions per Venezuelan labor law.\n\n'
             '🔹 SOURCE: Imported from Google Spreadsheet Column M (CESTA TICKET MENSUAL PTR) minus Cesta Ticket ($40)\n'
             '🔹 SPREADSHEET: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s, Tab "15nov2025"\n'
             '🔹 APPLIES TO: Salary Structure "Salarios Venezuela UEIPAB V2"\n'
             '🔹 DEDUCTIONS: None (exempt from all mandatory deductions)\n'
             '🔹 PRORATION: Yes (by actual payslip period days/30)\n'
             '🔹 FORMULA: Column M value - $40.00 Cesta Ticket = Bonus V2\n'
             '🔹 CEO APPROVED: 2025-11-16\n\n'
             'CALCULATION EXAMPLE (Rafael Perez):\n'
             '  Column M (VEB): 54,095.99 VEB\n'
             '  Column M (USD): 54,095.99 / 234.8715 = $230.32\n'
             '  Cesta Ticket: $40.00 (fixed)\n'
             '  Bonus V2: $230.32 - $40.00 = $190.32\n\n'
             'WAGE FORMULA:\n'
             '  wage = salary_v2 + extrabonus_v2 + bonus_v2 + cesta_ticket_usd'
    )

    # Venezuelan Payroll Schedule
    bimonthly_payroll = fields.Boolean(
        'Bi-monthly Payroll',
        default=True,
        help="Enable bi-monthly payroll (15th and 31st of each month)"
    )
    first_payment_day = fields.Integer(
        '1st Payment Day',
        default=15,
        help="First payment day of the month"
    )
    second_payment_day = fields.Integer(
        '2nd Payment Day',
        default=31,
        help="Second payment day of the month (or last day)"
    )

    # Venezuelan Prestaciones Sociales
    prestaciones_reset_date = fields.Date(
        'Prestaciones Reset Date',
        help="Date when prestaciones calculation was reset"
    )
    prestaciones_last_paid_date = fields.Date(
        'Last Prestaciones Payment',
        help="Date of last prestaciones payment made"
    )

    # Venezuelan Aguinaldos (Christmas Bonus)
    ueipab_monthly_salary = fields.Monetary(
        'Monthly Salary (Spreadsheet)',
        help="Total monthly salary from payroll spreadsheet (Column K in USD). "
             "Used for Aguinaldos, year-end bonuses, and other special calculations. "
             "This field tracks the official salary independent of the 70/25/5 distribution "
             "used for regular payroll. Synced from Google Sheets using "
             "sync-monthly-salary-from-spreadsheet.py script.",
        currency_field='currency_id',
    )
    ueipab_salary_notes = fields.Text(
        'Salary Notes (Audit Trail)',
        help="Complete audit trail for ueipab_monthly_salary including:\n"
             "- Source spreadsheet and date\n"
             "- Column reference\n"
             "- Original VEB amount\n"
             "- Exchange rate used\n\n"
             "Format: 'From payroll sheet {date}, Column K ({veb} VEB) @ {rate} VEB/USD'\n\n"
             "Example: 'From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD'\n\n"
             "This provides complete traceability and allows verification of calculations at any time.",
    )

    # Venezuelan Withhold Income Tax (ARI)
    ueipab_ari_withholding_rate = fields.Float(
        'ARI Withholding Rate (%)',
        default=1.0,
        help="Venezuelan Income Tax Withholding Rate (ARI - Anticipos de Retenciones del Impuesto sobre la Renta).\n\n"
             "This is the mandatory income tax withholding percentage applied to the base salary (K component). "
             "The rate varies by employee based on their tax bracket and salary level.\n\n"
             "This field stores the BI-WEEKLY rate that is applied directly to each bi-weekly payslip:\n"
             "- 1% (lower tax bracket)\n"
             "- 2% (higher tax bracket)\n\n"
             "This rate is reviewed and updated approximately every 90 days (quarterly) by Venezuelan tax authorities. "
             "Synced from payroll spreadsheet Column AA.",
    )
    ueipab_ari_last_update = fields.Date(
        'ARI Rate Last Updated',
        help="Date when the ARI withholding rate was last reviewed/updated. "
             "Should be updated approximately every 90 days per Venezuelan tax regulations."
    )

    # Liquidation Historical Tracking Fields (Added 2025-11-12)
    ueipab_original_hire_date = fields.Date(
        'Original Hire Date',
        help="Original employment start date - first day employee began labor relationship.\n\n"
             "Used for Antiguedad (seniority) calculation with continuity per Venezuelan law. "
             "This date represents when the employee's total seniority period began, even if "
             "there were gaps, rehires, or previous liquidations.\n\n"
             "Example: Virginia Verde hired Oct 1, 2019, liquidated Jul 31, 2023, rehired Sep 1, 2023.\n"
             "- contract.date_start = Sep 1, 2023 (company liability start)\n"
             "- ueipab_original_hire_date = Oct 1, 2019 (for antiguedad continuity)\n\n"
             "Data source: Spreadsheet 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s, "
             "Sheet 'Incremento2526', Range C5:D48 (44 employees)",
    )
    ueipab_previous_liquidation_date = fields.Date(
        'Previous Liquidation Date',
        help="Date of last full liquidation settlement (if any).\n\n"
             "Used to subtract already-paid antiguedad from total owed. When an employee is rehired "
             "after receiving full liquidation, we must not pay the same antiguedad twice.\n\n"
             "Calculation Logic:\n"
             "- Total antiguedad period: ueipab_original_hire_date to liquidation_date\n"
             "- Already paid period: ueipab_original_hire_date to ueipab_previous_liquidation_date\n"
             "- Net antiguedad owed: Total period - Already paid period\n\n"
             "Example: Virginia Verde\n"
             "- Original hire: Oct 1, 2019\n"
             "- Previous liquidation: Jul 31, 2023 (this field)\n"
             "- Current liquidation: Jul 31, 2025\n"
             "- Total seniority: 71 months (Oct 2019 - Jul 2025)\n"
             "- Already paid: 46 months (Oct 2019 - Jul 2023)\n"
             "- Net owed: 25 months\n\n"
             "Leave blank for employees who have never been liquidated.",
    )
    ueipab_vacation_paid_until = fields.Date(
        'Vacation Paid Until',
        help="Last date through which vacation and bono vacacional benefits were paid.\n\n"
             "Used to calculate accrued but unpaid vacation benefits at liquidation. The school "
             "pays all employees vacation/bono vacacional on August 1st each year for the previous "
             "12-month period (Sep 1 - Aug 31 fiscal year).\n\n"
             "Typical values:\n"
             "- Aug 1, 2024: For most employees (last annual vacation payment)\n"
             "- Aug 1, 2023: For employees who missed 2024 payment\n"
             "- Blank: For new employees hired after last Aug 1 payment\n\n"
             "Liquidation calculation:\n"
             "- Period owed: (ueipab_vacation_paid_until + 1 day) to liquidation_date\n"
             "- Days owed: (period_days / 365) * 15 days vacation + bono days based on seniority\n\n"
             "Example: Employee liquidated Jul 31, 2025, last paid Aug 1, 2024\n"
             "- Period: Aug 2, 2024 to Jul 31, 2025 = 364 days ≈ 1 year\n"
             "- Vacation owed: 15 days (1 year * 15 days/year)\n"
             "- Bono owed: 14 days (1 year * 14 days/year for 5+ years seniority)",
    )

    # ==========================================================================
    # V2 COMPENSATION METHODS
    # ==========================================================================

    @api.onchange('ueipab_salary_v2', 'ueipab_extrabonus_v2', 'ueipab_bonus_v2', 'cesta_ticket_usd')
    def _onchange_salary_breakdown_v2(self):
        """Auto-calculate total wage from V2 compensation components

        FORMULA:
            wage = salary_v2 + extrabonus_v2 + bonus_v2 + cesta_ticket_usd

        DEDUCTION RULES (CEO Approved 2025-11-16):
            - salary_v2: Subject to SSO 4%, FAOV 1%, PARO 0.5%, ARI variable%
            - extrabonus_v2: Exempt from all deductions
            - bonus_v2: Exempt from all deductions
            - cesta_ticket_usd: Exempt from all deductions (mandatory benefit)

        LEGAL BASIS:
            CEO confirmed full compliance with Venezuelan labor law (2025-11-16)

        PRORATION (Option A - CEO Approved):
            All components prorated by actual payslip period (days / 30)
            Handles standard bi-weekly (15 days), terminations, and partial periods

        EXAMPLE (Rafael Perez):
            salary_v2 = $119.09
            extrabonus_v2 = $51.21
            bonus_v2 = $190.32
            cesta_ticket_usd = $40.00
            ────────────────────
            wage = $400.62

        PARALLEL V1/V2 OPERATION:
            This method ONLY updates wage if V2 fields are populated.
            V1 fields (ueipab_deduction_base, etc.) remain untouched.
            Both structures can coexist during migration period.
        """
        # Only calculate if at least one V2 field is populated
        if self.ueipab_salary_v2 or self.ueipab_extrabonus_v2 or self.ueipab_bonus_v2:
            self.wage = (
                (self.ueipab_salary_v2 or 0.0) +
                (self.ueipab_extrabonus_v2 or 0.0) +
                (self.ueipab_bonus_v2 or 0.0) +
                (self.cesta_ticket_usd or 0.0)
            )