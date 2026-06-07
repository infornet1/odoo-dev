from odoo import models, fields, api
import xmlrpc.client
import json
import os


BUDGET_PARAMS = {
    # Budget 25-26: current period
    # Budget 26-27: starting Sep 1, 2026 — max 20% total increase
    #   6% to base salary, 14% to regular bonus
    'salary_increase_rate': 0.06,
    'bonus_increase_rate':  0.14,
    'budget_start_date':    '2026-09-01',
}


class RecruitmentWageRange(models.TransientModel):
    """Transient model: compute recommended wage range for a job position."""
    _name = 'hr.recruitment.wage.range'
    _description = 'Wage Range Advisor for Recruitment'

    job_id = fields.Many2one('hr.job', string='Cargo', required=True)
    budget_period = fields.Selection([
        ('25_26', 'Período 2025-2026 (actual)'),
        ('26_27', 'Período 2026-2027 (desde Sep 2026)'),
    ], string='Período Presupuestario', default='26_27')

    # Computed range
    salary_min = fields.Float('Salario Mínimo Sugerido', readonly=True)
    salary_max = fields.Float('Salario Máximo Sugerido', readonly=True)
    bonus_min  = fields.Float('Bono Mínimo Sugerido', readonly=True)
    bonus_max  = fields.Float('Bono Máximo Sugerido', readonly=True)
    total_min  = fields.Float('Total Mínimo', readonly=True)
    total_max  = fields.Float('Total Máximo', readonly=True)
    range_basis = fields.Text('Base del Cálculo', readonly=True)

    @api.onchange('job_id', 'budget_period')
    def _onchange_compute_range(self):
        if not self.job_id:
            return
        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('job_id', '=', self.job_id.id),
        ])
        if not contracts:
            # No matching contracts — fall back to global percentiles
            all_contracts = self.env['hr.contract'].search([('state', '=', 'open')])
            salaries = sorted([c.ueipab_salary_v2 for c in all_contracts if c.ueipab_salary_v2])
            bonuses  = sorted([c.ueipab_bonus_v2  for c in all_contracts if c.ueipab_bonus_v2])
            if not salaries:
                return
            p25 = salaries[len(salaries) // 4]
            p50 = salaries[len(salaries) // 2]
            b25 = bonuses[len(bonuses) // 4]
            b50 = bonuses[len(bonuses) // 2]
            basis = f"Sin contratos para este cargo. Usando P25–P50 global ({len(salaries)} contratos activos)."
        else:
            sals = sorted([c.ueipab_salary_v2 for c in contracts if c.ueipab_salary_v2])
            bons = sorted([c.ueipab_bonus_v2  for c in contracts if c.ueipab_bonus_v2])
            p25, p50 = (sals[0], sals[-1]) if len(sals) >= 2 else (sals[0], sals[0])
            b25, b50 = (bons[0], bons[-1]) if len(bons) >= 2 else (bons[0], bons[0])
            basis = f"Basado en {len(contracts)} contratos activos para {self.job_id.name}."

        s_rate = BUDGET_PARAMS['salary_increase_rate'] if self.budget_period == '26_27' else 0
        b_rate = BUDGET_PARAMS['bonus_increase_rate']  if self.budget_period == '26_27' else 0

        self.salary_min = round(p25 * (1 + s_rate), 2)
        self.salary_max = round(p50 * (1 + s_rate), 2)
        self.bonus_min  = round(b25 * (1 + b_rate), 2)
        self.bonus_max  = round(b50 * (1 + b_rate), 2)
        self.total_min  = round(self.salary_min + self.bonus_min, 2)
        self.total_max  = round(self.salary_max + self.bonus_max, 2)

        period_note = ""
        if self.budget_period == '26_27':
            period_note = (
                f" | Proyectado Sep 2026: +{s_rate*100:.0f}% salario, "
                f"+{b_rate*100:.0f}% bono (máx 20% total)"
            )
        self.range_basis = basis + period_note
