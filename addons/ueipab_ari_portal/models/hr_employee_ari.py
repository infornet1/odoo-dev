# -*- coding: utf-8 -*-
"""
HR Employee AR-I Declaration Model

Manages AR-I tax withholding declarations for Venezuelan employees.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class HrEmployeeARI(models.Model):
    _name = 'hr.employee.ari'
    _description = 'Employee AR-I Tax Declaration'
    _order = 'fiscal_year desc, submission_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # HEADER FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        index=True,
        default=lambda self: self._get_default_employee()
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        compute='_compute_contract',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='employee_id.company_id',
        store=True
    )
    fiscal_year = fields.Integer(
        string='Fiscal Year',
        required=True,
        default=lambda self: fields.Date.today().year,
        tracking=True
    )
    submission_date = fields.Date(
        string='Submission Date',
        default=fields.Date.today,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True, string='Status')

    # -------------------------------------------------------------------------
    # VARIATION FIELDS (Section 5)
    # -------------------------------------------------------------------------
    is_variation = fields.Boolean(
        string='Is Variation',
        default=False,
        help='Check if this is a variation update (not initial declaration)'
    )
    variation_month = fields.Selection([
        ('january', 'Enero (Inicial)'),
        ('march', 'Marzo'),
        ('june', 'Junio'),
        ('september', 'Septiembre'),
        ('december', 'Diciembre')
    ], string='Declaration Period', default='january')

    # -------------------------------------------------------------------------
    # SECTION A - INCOME ESTIMATION
    # -------------------------------------------------------------------------
    income_employer_primary = fields.Float(
        string='Income from UEIPAB (Annual)',
        digits=(16, 2),
        help='Estimated annual income from primary employer (UEIPAB)'
    )
    income_employer_b = fields.Float(
        string='Income Employer B (Annual)',
        digits=(16, 2),
        default=0.0,
        help='Income from second employer if applicable'
    )
    income_employer_c = fields.Float(
        string='Income Employer C (Annual)',
        digits=(16, 2),
        default=0.0,
        help='Income from third employer if applicable'
    )
    income_employer_d = fields.Float(
        string='Income Employer D (Annual)',
        digits=(16, 2),
        default=0.0,
        help='Income from fourth employer if applicable'
    )
    income_total = fields.Float(
        string='Total Annual Income (A)',
        compute='_compute_income_total',
        store=True,
        digits=(16, 2)
    )

    # Other employer names
    employer_b_name = fields.Char(string='Employer B Name')
    employer_c_name = fields.Char(string='Employer C Name')
    employer_d_name = fields.Char(string='Employer D Name')

    # -------------------------------------------------------------------------
    # SECTION B - UT CONVERSION
    # -------------------------------------------------------------------------
    ut_value = fields.Float(
        string='UT Value (Bs.)',
        digits=(16, 2),
        default=9.00,
        help='Current Tax Unit (Unidad Tributaria) value in Bolivares'
    )
    income_in_ut = fields.Float(
        string='Income in UT (B)',
        compute='_compute_income_ut',
        store=True,
        digits=(16, 2)
    )

    # -------------------------------------------------------------------------
    # SECTION C/E - DEDUCTIONS SELECTION
    # -------------------------------------------------------------------------
    deduction_type = fields.Selection([
        ('unique', 'Desgravamen Único (774 UT)'),
        ('itemized', 'Desgravámenes Detallados')
    ], string='Deduction Type', default='unique', required=True,
       help='Choose between fixed deduction (774 UT, no proof needed) or itemized deductions')

    # Section C - Itemized Deductions (if selected)
    deduction_education = fields.Float(
        string='1. Education Expenses',
        digits=(16, 2),
        default=0.0,
        help='Tuition at domestic educational institutions'
    )
    deduction_insurance = fields.Float(
        string='2. Insurance Premiums',
        digits=(16, 2),
        default=0.0,
        help='Life, hospitalization, maternity, surgery insurance premiums'
    )
    deduction_medical = fields.Float(
        string='3. Medical/Dental Expenses',
        digits=(16, 2),
        default=0.0,
        help='Medical and dental services provided domestically'
    )
    deduction_housing = fields.Float(
        string='4. Housing Expenses',
        digits=(16, 2),
        default=0.0,
        help='Mortgage interest (max 1000 UT) or rent (max 800 UT)'
    )
    deduction_housing_type = fields.Selection([
        ('mortgage', 'Mortgage (Hipoteca) - Max 1,000 UT'),
        ('rent', 'Rent (Alquiler) - Max 800 UT')
    ], string='Housing Type')
    deductions_total = fields.Float(
        string='Total Itemized Deductions (C)',
        compute='_compute_deductions',
        store=True,
        digits=(16, 2)
    )
    deductions_in_ut = fields.Float(
        string='Deductions in UT (D)',
        compute='_compute_deductions_ut',
        store=True,
        digits=(16, 2)
    )

    # Section E - Unique Deduction
    deduction_unique_ut = fields.Float(
        string='Unique Deduction (E)',
        compute='_compute_deduction_unique',
        store=True,
        digits=(16, 2),
        help='Fixed deduction of 774 UT (Art. 61 LISLR)'
    )

    # -------------------------------------------------------------------------
    # SECTION F - TAXABLE INCOME
    # -------------------------------------------------------------------------
    taxable_income_ut = fields.Float(
        string='Taxable Income (F)',
        compute='_compute_tax',
        store=True,
        digits=(16, 2),
        help='Income in UT minus deductions'
    )

    # -------------------------------------------------------------------------
    # SECTION G - TAX CALCULATION
    # -------------------------------------------------------------------------
    estimated_tax_ut = fields.Float(
        string='Estimated Tax (G)',
        compute='_compute_tax',
        store=True,
        digits=(16, 2)
    )

    # -------------------------------------------------------------------------
    # SECTION H - REBAJAS (TAX REDUCTIONS)
    # -------------------------------------------------------------------------
    rebaja_personal = fields.Float(
        string='Personal Rebate',
        default=10.0,
        readonly=True,
        help='Personal rebate: 10 UT (Art. 63 LISLR)'
    )
    rebaja_spouse = fields.Boolean(
        string='Spouse (Cónyuge)',
        default=False,
        help='Check if married (not legally separated)'
    )
    rebaja_children_under_25 = fields.Integer(
        string='Children under 25',
        default=0,
        help='Number of children under 25 years old'
    )
    rebaja_children_disabled = fields.Integer(
        string='Disabled Children',
        default=0,
        help='Number of disabled children (any age)'
    )
    rebaja_parents = fields.Integer(
        string='Dependent Parents',
        default=0,
        help='Number of financially dependent parents'
    )
    cargas_familiares_count = fields.Integer(
        string='Total Family Dependents',
        compute='_compute_cargas',
        store=True
    )
    rebaja_prior_excess = fields.Float(
        string='Prior Year Excess Withholding',
        digits=(16, 2),
        default=0.0,
        help='Income tax withheld in excess from prior years'
    )
    rebajas_total_ut = fields.Float(
        string='Total Rebajas (H)',
        compute='_compute_rebajas',
        store=True,
        digits=(16, 2)
    )

    # -------------------------------------------------------------------------
    # SECTION I - TAX TO WITHHOLD
    # -------------------------------------------------------------------------
    tax_to_withhold_ut = fields.Float(
        string='Tax to Withhold (I)',
        compute='_compute_tax_to_withhold',
        store=True,
        digits=(16, 2)
    )

    # -------------------------------------------------------------------------
    # SECTION J - WITHHOLDING PERCENTAGE (FINAL RESULT)
    # -------------------------------------------------------------------------
    withholding_percentage = fields.Float(
        string='Withholding % (J)',
        compute='_compute_percentage',
        store=True,
        digits=(16, 4),
        help='Final withholding percentage to apply on each paycheck'
    )

    # -------------------------------------------------------------------------
    # SECTION K - VARIATION DATA
    # -------------------------------------------------------------------------
    ytd_withholding = fields.Float(
        string='YTD Withholding (K1)',
        digits=(16, 2),
        default=0.0,
        help='Total tax withheld year-to-date'
    )
    ytd_income = fields.Float(
        string='YTD Income (K2)',
        digits=(16, 2),
        default=0.0,
        help='Total remuneration received year-to-date'
    )

    # -------------------------------------------------------------------------
    # HR REVIEW FIELDS
    # -------------------------------------------------------------------------
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        tracking=True
    )
    review_date = fields.Date(
        string='Review Date',
        tracking=True
    )
    review_notes = fields.Text(
        string='Review Notes'
    )
    rejection_reason = fields.Text(
        string='Rejection Reason'
    )

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Supporting Documents',
        help='Upload receipts for itemized deductions'
    )
    excel_file = fields.Binary(
        string='Generated AR-I Excel',
        attachment=True
    )
    excel_filename = fields.Char(
        string='Excel Filename'
    )

    # -------------------------------------------------------------------------
    # DEADLINE TRACKING
    # -------------------------------------------------------------------------
    next_deadline = fields.Date(
        string='Next Update Deadline',
        compute='_compute_next_deadline',
        store=True
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_is_overdue'
    )

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------
    def _get_default_employee(self):
        """Get current user's employee record."""
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid)
        ], limit=1)

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            if rec.employee_id:
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'open')
                ], limit=1)
                rec.contract_id = contract
            else:
                rec.contract_id = False

    @api.depends('income_employer_primary', 'income_employer_b',
                 'income_employer_c', 'income_employer_d')
    def _compute_income_total(self):
        for rec in self:
            rec.income_total = (
                rec.income_employer_primary +
                rec.income_employer_b +
                rec.income_employer_c +
                rec.income_employer_d
            )

    @api.depends('income_total', 'ut_value')
    def _compute_income_ut(self):
        for rec in self:
            if rec.ut_value > 0:
                rec.income_in_ut = rec.income_total / rec.ut_value
            else:
                rec.income_in_ut = 0.0

    @api.depends('deduction_education', 'deduction_insurance',
                 'deduction_medical', 'deduction_housing', 'deduction_type')
    def _compute_deductions(self):
        for rec in self:
            if rec.deduction_type == 'itemized':
                rec.deductions_total = (
                    rec.deduction_education +
                    rec.deduction_insurance +
                    rec.deduction_medical +
                    rec.deduction_housing
                )
            else:
                rec.deductions_total = 0.0

    @api.depends('deductions_total', 'ut_value')
    def _compute_deductions_ut(self):
        for rec in self:
            if rec.ut_value > 0 and rec.deduction_type == 'itemized':
                rec.deductions_in_ut = rec.deductions_total / rec.ut_value
            else:
                rec.deductions_in_ut = 0.0

    @api.depends('deduction_type')
    def _compute_deduction_unique(self):
        for rec in self:
            if rec.deduction_type == 'unique':
                rec.deduction_unique_ut = 774.0
            else:
                rec.deduction_unique_ut = 0.0

    @api.depends('rebaja_spouse', 'rebaja_children_under_25',
                 'rebaja_children_disabled', 'rebaja_parents')
    def _compute_cargas(self):
        for rec in self:
            count = 0
            if rec.rebaja_spouse:
                count += 1
            count += rec.rebaja_children_under_25
            count += rec.rebaja_children_disabled
            count += rec.rebaja_parents
            rec.cargas_familiares_count = count

    @api.depends('rebaja_personal', 'cargas_familiares_count',
                 'rebaja_prior_excess', 'ut_value')
    def _compute_rebajas(self):
        for rec in self:
            # Personal rebate (10 UT) + family dependents (10 UT each)
            rebajas_ut = rec.rebaja_personal + (rec.cargas_familiares_count * 10)
            # Add prior excess withholding converted to UT
            if rec.ut_value > 0 and rec.rebaja_prior_excess > 0:
                rebajas_ut += rec.rebaja_prior_excess / rec.ut_value
            rec.rebajas_total_ut = rebajas_ut

    @api.depends('income_in_ut', 'deductions_in_ut', 'deduction_unique_ut', 'deduction_type')
    def _compute_tax(self):
        """Calculate taxable income and estimated tax using progressive rates."""
        for rec in self:
            # Determine deduction to use
            if rec.deduction_type == 'unique':
                deduction = rec.deduction_unique_ut
            else:
                deduction = rec.deductions_in_ut

            # Taxable income (F) = Income (B) - Deductions (D or E)
            rec.taxable_income_ut = max(0, rec.income_in_ut - deduction)

            # Calculate tax using progressive rates (Art. 57 LISLR)
            taxable = rec.taxable_income_ut
            if taxable <= 0:
                tax = 0
            elif taxable <= 1000:
                tax = taxable * 0.06
            elif taxable <= 1500:
                tax = taxable * 0.09 - 30
            elif taxable <= 2000:
                tax = taxable * 0.12 - 75
            elif taxable <= 2500:
                tax = taxable * 0.16 - 155
            elif taxable <= 3000:
                tax = taxable * 0.20 - 255
            elif taxable <= 4000:
                tax = taxable * 0.24 - 375
            elif taxable <= 6000:
                tax = taxable * 0.29 - 575
            else:
                tax = taxable * 0.34 - 875

            rec.estimated_tax_ut = max(0, tax)

    @api.depends('estimated_tax_ut', 'rebajas_total_ut')
    def _compute_tax_to_withhold(self):
        for rec in self:
            rec.tax_to_withhold_ut = max(0, rec.estimated_tax_ut - rec.rebajas_total_ut)

    @api.depends('tax_to_withhold_ut', 'income_in_ut')
    def _compute_percentage(self):
        for rec in self:
            if rec.income_in_ut > 0:
                rec.withholding_percentage = (rec.tax_to_withhold_ut / rec.income_in_ut) * 100
            else:
                rec.withholding_percentage = 0.0

    @api.depends('fiscal_year', 'variation_month')
    def _compute_next_deadline(self):
        """Compute the next AR-I update deadline."""
        deadlines = {
            'january': (1, 15),
            'march': (3, 15),
            'june': (6, 15),
            'september': (9, 15),
            'december': (12, 15)
        }
        for rec in self:
            if rec.variation_month and rec.fiscal_year:
                month, day = deadlines.get(rec.variation_month, (1, 15))
                rec.next_deadline = date(rec.fiscal_year, month, day)
            else:
                rec.next_deadline = False

    def _compute_is_overdue(self):
        today = fields.Date.today()
        for rec in self:
            if rec.next_deadline and rec.state == 'draft':
                rec.is_overdue = today > rec.next_deadline
            else:
                rec.is_overdue = False

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    @api.onchange('employee_id')
    def _onchange_employee(self):
        """Auto-fill income from contract when employee is selected."""
        if self.employee_id:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            if contract:
                # Calculate annual income from contract
                # Monthly salary × 12 + estimated bonuses
                monthly_salary = contract.wage or 0
                # Include V2 fields if available
                if hasattr(contract, 'ueipab_salary_v2'):
                    monthly_salary = contract.ueipab_salary_v2 or contract.wage or 0

                # Estimate annual income (salary × 12 + aguinaldos + vacation bonus)
                annual_salary = monthly_salary * 12
                # Add estimated bonuses (roughly 4 months equivalent)
                estimated_bonuses = monthly_salary * 4
                self.income_employer_primary = annual_salary + estimated_bonuses

    @api.onchange('deduction_type')
    def _onchange_deduction_type(self):
        """Clear itemized deductions when switching to unique."""
        if self.deduction_type == 'unique':
            self.deduction_education = 0.0
            self.deduction_insurance = 0.0
            self.deduction_medical = 0.0
            self.deduction_housing = 0.0

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.employee.ari'
                ) or _('New')
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_submit(self):
        """Submit AR-I declaration for HR review."""
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_('Only draft declarations can be submitted.'))
            rec.write({
                'state': 'submitted',
                'submission_date': fields.Date.today()
            })
            # Notify HR
            rec._notify_hr_submission()
        return True

    def action_approve(self):
        """HR approves the AR-I declaration."""
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError(_('Only submitted declarations can be approved.'))
            rec.write({
                'state': 'approved',
                'reviewed_by': self.env.uid,
                'review_date': fields.Date.today()
            })
            # Update contract's ARI withholding rate
            rec._update_contract_ari_rate()
            # Notify employee
            rec._notify_employee_approved()
        return True

    def action_reject(self):
        """HR rejects the AR-I declaration."""
        return {
            'name': _('Reject AR-I Declaration'),
            'type': 'ir.actions.act_window',
            'res_model': 'ari.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ari_id': self.id}
        }

    def action_cancel(self):
        """Cancel the AR-I declaration."""
        for rec in self:
            rec.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        """Reset to draft for corrections."""
        for rec in self:
            if rec.state in ['rejected', 'cancelled']:
                rec.write({'state': 'draft'})
        return True

    def action_generate_excel(self):
        """Generate AR-I Excel file using SENIAT template."""
        self.ensure_one()
        generator = self.env['ari.excel.generator']
        excel_data, filename = generator.generate_ari_excel(self)
        self.write({
            'excel_file': excel_data,
            'excel_filename': filename
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/excel_file/{filename}?download=true',
            'target': 'self'
        }

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    def _update_contract_ari_rate(self):
        """Update the contract's ARI withholding rate."""
        for rec in self:
            if rec.contract_id and hasattr(rec.contract_id, 'ueipab_ari_withholding_rate'):
                # Round to whole number for the contract field
                rate = round(rec.withholding_percentage)
                rec.contract_id.write({
                    'ueipab_ari_withholding_rate': rate
                })

    def _notify_hr_submission(self):
        """Send notification to HR when AR-I is submitted."""
        template = self.env.ref(
            'ueipab_ari_portal.mail_template_ari_submitted',
            raise_if_not_found=False
        )
        if template:
            # Send to HR managers
            hr_managers = self.env.ref('hr.group_hr_manager').users
            for manager in hr_managers:
                if manager.email:
                    template.with_context(email_to=manager.email).send_mail(
                        self.id, force_send=True
                    )

    def _notify_employee_approved(self):
        """Send notification to employee when AR-I is approved."""
        template = self.env.ref(
            'ueipab_ari_portal.mail_template_ari_approved',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _notify_employee_rejected(self):
        """Send notification to employee when AR-I is rejected."""
        template = self.env.ref(
            'ueipab_ari_portal.mail_template_ari_rejected',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    # -------------------------------------------------------------------------
    # CRON METHODS
    # -------------------------------------------------------------------------
    @api.model
    def _cron_deadline_reminder(self):
        """
        Cron job to send AR-I deadline reminders.
        Runs daily and checks for upcoming deadlines.
        """
        today = fields.Date.today()

        # Deadline reminder schedule: remind 14 days before each deadline
        # Deadlines: Jan 15, Mar 15, Jun 15, Sep 15, Dec 15
        deadlines = [
            (1, 15, 'january'),   # January 15 - Initial
            (3, 15, 'march'),     # March 15
            (6, 15, 'june'),      # June 15
            (9, 15, 'september'), # September 15
            (12, 15, 'december'), # December 15
        ]

        for month, day, period in deadlines:
            deadline_date = date(today.year, month, day)
            reminder_date = deadline_date - relativedelta(days=14)

            if today == reminder_date:
                # Find employees without approved AR-I for this period
                self._send_deadline_reminders(today.year, period)

    def _send_deadline_reminders(self, fiscal_year, period):
        """Send reminder emails to employees without AR-I for the period."""
        # Get all active employees
        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('contract_ids.state', '=', 'open')
        ])

        template = self.env.ref(
            'ueipab_ari_portal.mail_template_ari_deadline_reminder',
            raise_if_not_found=False
        )

        for employee in employees:
            # Check if employee has approved AR-I for this period
            existing = self.search([
                ('employee_id', '=', employee.id),
                ('fiscal_year', '=', fiscal_year),
                ('variation_month', '=', period),
                ('state', '=', 'approved')
            ], limit=1)

            if not existing and template:
                # Create a placeholder record for the reminder email context
                # or use the latest draft/rejected one
                latest = self.search([
                    ('employee_id', '=', employee.id),
                    ('fiscal_year', '=', fiscal_year)
                ], order='create_date desc', limit=1)

                if latest:
                    template.send_mail(latest.id, force_send=False)

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------
    @api.constrains('fiscal_year')
    def _check_fiscal_year(self):
        current_year = fields.Date.today().year
        for rec in self:
            if rec.fiscal_year < current_year - 1 or rec.fiscal_year > current_year + 1:
                raise ValidationError(_(
                    'Fiscal year must be within one year of current year.'
                ))

    @api.constrains('deduction_housing', 'deduction_housing_type', 'ut_value')
    def _check_housing_limits(self):
        """Validate housing deduction limits."""
        for rec in self:
            if rec.deduction_type == 'itemized' and rec.deduction_housing > 0:
                if rec.ut_value > 0:
                    housing_ut = rec.deduction_housing / rec.ut_value
                    if rec.deduction_housing_type == 'mortgage' and housing_ut > 1000:
                        raise ValidationError(_(
                            'Mortgage interest deduction cannot exceed 1,000 UT.'
                        ))
                    elif rec.deduction_housing_type == 'rent' and housing_ut > 800:
                        raise ValidationError(_(
                            'Rent deduction cannot exceed 800 UT.'
                        ))
