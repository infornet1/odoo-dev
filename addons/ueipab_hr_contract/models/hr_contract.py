from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

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