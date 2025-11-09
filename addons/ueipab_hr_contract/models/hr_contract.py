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