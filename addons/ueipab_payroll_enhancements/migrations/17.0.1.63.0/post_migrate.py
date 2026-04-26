# -*- coding: utf-8 -*-
"""
Migration 17.0.1.63.0 — Salary Advance / Loan Recovery Rules

Creates VE_LOAN_DED_V2 in VE_PAYROLL_V2 and LIQUID_LOAN_DED_V2 in LIQUID_VE_V2.
Updates VE_TOTAL_DED_V2 and LIQUID_NET_V2 to include the new deduction rules.
Idempotent — skips creation if rules already exist.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    nomina_v2 = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)
    liquid_v2 = env['hr.payroll.structure'].search([('code', '=', 'LIQUID_VE_V2')], limit=1)
    ded_cat = env.ref('hr_payroll_community.DED', raise_if_not_found=False)

    if not ded_cat:
        _logger.warning('migration 63.0: DED category not found — skipping loan rule creation')
        return

    # --- VE_LOAN_DED_V2 ---
    if nomina_v2 and not env['hr.salary.rule'].search([('code', '=', 'VE_LOAN_DED_V2')], limit=1):
        rule = env['hr.salary.rule'].create({
            'name': 'VE_LOAN_DED_V2 - Loan Recovery',
            'code': 'VE_LOAN_DED_V2',
            'category_id': ded_cat.id,
            'sequence': 106,
            'amount_select': 'code',
            'amount_python_compute': 'result = -(inputs.LO.amount) if inputs.LO else 0',
            'appears_on_payslip': True,
            'active': True,
        })
        nomina_v2.write({'rule_ids': [(4, rule.id)]})
        env['hr.rule.input'].create({
            'name': 'Loan Recovery',
            'code': 'LO',
            'input_id': rule.id,
        })
        _logger.info('migration 63.0: created VE_LOAN_DED_V2 in VE_PAYROLL_V2 (id=%d)', rule.id)
    else:
        _logger.info('migration 63.0: VE_LOAN_DED_V2 already exists — skipped')

    # --- LIQUID_LOAN_DED_V2 ---
    if liquid_v2 and not env['hr.salary.rule'].search([('code', '=', 'LIQUID_LOAN_DED_V2')], limit=1):
        rule2 = env['hr.salary.rule'].create({
            'name': 'LIQUID_LOAN_DED_V2 - Loan Recovery',
            'code': 'LIQUID_LOAN_DED_V2',
            'category_id': ded_cat.id,
            'sequence': 196,
            'amount_select': 'code',
            'amount_python_compute': 'result = -(inputs.LO.amount) if inputs.LO else 0',
            'appears_on_payslip': True,
            'active': True,
        })
        liquid_v2.write({'rule_ids': [(4, rule2.id)]})
        env['hr.rule.input'].create({
            'name': 'Loan Recovery',
            'code': 'LO',
            'input_id': rule2.id,
        })
        _logger.info('migration 63.0: created LIQUID_LOAN_DED_V2 in LIQUID_VE_V2 (id=%d)', rule2.id)
    else:
        _logger.info('migration 63.0: LIQUID_LOAN_DED_V2 already exists — skipped')

    # --- Update VE_TOTAL_DED_V2 to include loan ---
    total_ded = env['hr.salary.rule'].search([('code', '=', 'VE_TOTAL_DED_V2')], limit=1)
    if total_ded and 'VE_LOAN_DED_V2' not in (total_ded.amount_python_compute or ''):
        new_formula = (total_ded.amount_python_compute or '').rstrip()
        # Append loan block and update result line
        new_formula = new_formula.replace(
            'result = sso + paro + faov + ari + inces + other',
            '# Loan recovery deduction\ntry:\n    loan = VE_LOAN_DED_V2 or 0\nexcept:\n    loan = 0\n\nresult = sso + paro + faov + ari + inces + other + loan'
        )
        total_ded.write({'amount_python_compute': new_formula})
        _logger.info('migration 63.0: updated VE_TOTAL_DED_V2 to include VE_LOAN_DED_V2')
    else:
        _logger.info('migration 63.0: VE_TOTAL_DED_V2 already includes loan or not found — skipped')

    # --- Update LIQUID_NET_V2 to include loan ---
    liquid_net = env['hr.salary.rule'].search([('code', '=', 'LIQUID_NET_V2')], limit=1)
    if liquid_net and 'LIQUID_LOAN_DED_V2' not in (liquid_net.amount_python_compute or ''):
        old_formula = liquid_net.amount_python_compute or ''
        # Insert loan try/except before the result block, add loan_deduction to sum
        loan_block = (
            '\n# Loan recovery deduction (may not exist)\n'
            'try:\n    loan_deduction = LIQUID_LOAN_DED_V2 or 0\nexcept:\n    loan_deduction = 0\n'
        )
        # Insert before 'result = ('
        new_formula = old_formula.replace(
            'result = (',
            loan_block + 'result = ('
        )
        # Add loan_deduction to the sum (before closing paren)
        new_formula = new_formula.replace(
            '    prepaid_deduction\n)',
            '    prepaid_deduction +\n    loan_deduction\n)'
        )
        liquid_net.write({'amount_python_compute': new_formula})
        _logger.info('migration 63.0: updated LIQUID_NET_V2 to include LIQUID_LOAN_DED_V2')
    else:
        _logger.info('migration 63.0: LIQUID_NET_V2 already includes loan or not found — skipped')
