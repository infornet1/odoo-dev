# -*- coding: utf-8 -*-
"""
Calibracion Bonus Wizard

Allows HR to enter the number of Glenda calibration sessions per employee
when closing a payroll batch, then injects the corresponding payslip inputs
so the BONO_CALIBRACION salary rule fires automatically.

Flow:
    1. HR opens batch → clicks "Bonos Calibración Glenda"
    2. Wizard loads employees who have an acknowledged glenda_calibracion_v1
       notice and also have a draft payslip in this batch.
    3. HR enters session count per employee (default 0).
    4. "Apply Bonuses" button writes hr.payslip.input records (code=CALIBRACION_GLENDA)
       onto the matching draft payslips.
    5. Payslips must be recomputed after applying to reflect the new input.

Technical notes:
    - hr_payroll_community uses hr.payslip.input with a code field directly.
      There is NO hr.payslip.input.type model in the community edition.
    - Inputs already present for an employee are updated (not duplicated).
    - Only draft payslips are targeted; confirmed payslips are skipped with a warning.
"""

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CalibracionBonusWizard(models.TransientModel):
    """Wizard for entering Glenda calibration session counts per batch employee."""

    _name = 'calibracion.bonus.wizard'
    _description = 'Bonos Calibración Glenda — Wizard'

    # ========================================
    # HEADER FIELDS
    # ========================================

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        required=True,
        readonly=True,
    )

    line_ids = fields.One2many(
        'calibracion.bonus.wizard.line',
        'wizard_id',
        string='Employees',
    )

    registered_count = fields.Integer(
        string='Registered Employees',
        compute='_compute_registered_count',
        help='Employees in this batch with a confirmed Glenda calibration registration.',
    )

    not_registered_count = fields.Integer(
        string='Not Registered',
        compute='_compute_registered_count',
        help='Batch employees without a Glenda calibration acknowledgment.',
    )

    # ========================================
    # DEFAULT VALUES
    # ========================================

    @api.model
    def default_get(self, fields_list):
        """Populate wizard lines from batch payslips cross-referenced with
        glenda_calibracion_v1 notice acknowledgments."""
        res = super().default_get(fields_list)

        batch_id = self.env.context.get('default_payslip_run_id')
        if not batch_id:
            return res

        batch = self.env['hr.payslip.run'].browse(batch_id)

        # Build a map: employee_id -> draft payslip in this batch
        slip_map = {}
        for slip in batch.slip_ids:
            if slip.state == 'draft':
                slip_map[slip.employee_id.id] = slip

        # Gather all employee IDs in the batch (draft or otherwise)
        batch_employee_ids = batch.slip_ids.mapped('employee_id').ids

        # Fetch all acknowledged glenda_calibracion_v1 records for batch employees
        acks = self.env['hr.notice.acknowledgment'].search([
            ('notice_key', '=', 'glenda_calibracion_v1'),
            ('state', '=', 'acknowledged'),
            ('employee_id', 'in', batch_employee_ids),
        ])

        ack_map = {ack.employee_id.id: ack for ack in acks}

        # Existing CALIBRACION_GLENDA inputs already on draft payslips
        existing_input_map = {}
        for slip in batch.slip_ids.filtered(lambda s: s.state == 'draft'):
            for inp in slip.input_line_ids.filtered(lambda i: i.code == 'CALIBRACION_GLENDA'):
                existing_input_map[slip.employee_id.id] = inp.amount

        lines = []
        for emp_id, slip in sorted(slip_map.items(), key=lambda x: x[1].employee_id.name):
            ack = ack_map.get(emp_id)
            lines.append((0, 0, {
                'employee_id': emp_id,
                'payslip_id': slip.id,
                'wa_number': ack.wa_number if ack else '',
                'ack_date': ack.ack_date if ack else False,
                'is_registered': bool(ack),
                # Pre-fill sessions from any existing input on the payslip
                'sessions': int(existing_input_map.get(emp_id, 0)),
            }))

        res['line_ids'] = lines
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to populate lines if default_get did not (edge case)."""
        records = super().create(vals_list)
        for record in records:
            if not record.line_ids and record.payslip_run_id:
                record._populate_lines()
        return records

    def _populate_lines(self):
        """Fallback population when lines arrive empty after create."""
        self.ensure_one()
        batch = self.payslip_run_id
        slip_map = {s.employee_id.id: s for s in batch.slip_ids if s.state == 'draft'}
        batch_employee_ids = list(slip_map.keys())

        acks = self.env['hr.notice.acknowledgment'].search([
            ('notice_key', '=', 'glenda_calibracion_v1'),
            ('state', '=', 'acknowledged'),
            ('employee_id', 'in', batch_employee_ids),
        ])
        ack_map = {a.employee_id.id: a for a in acks}

        line_vals = []
        for emp_id, slip in sorted(slip_map.items(), key=lambda x: x[1].employee_id.name):
            ack = ack_map.get(emp_id)
            line_vals.append({
                'wizard_id': self.id,
                'employee_id': emp_id,
                'payslip_id': slip.id,
                'wa_number': ack.wa_number if ack else '',
                'ack_date': ack.ack_date if ack else False,
                'is_registered': bool(ack),
                'sessions': 0,
            })
        if line_vals:
            self.env['calibracion.bonus.wizard.line'].create(line_vals)

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    @api.depends('line_ids.is_registered')
    def _compute_registered_count(self):
        for wizard in self:
            wizard.registered_count = len(wizard.line_ids.filtered('is_registered'))
            wizard.not_registered_count = len(wizard.line_ids.filtered(lambda l: not l.is_registered))

    # ========================================
    # ACTIONS
    # ========================================

    def action_apply_bonuses(self):
        """Write CALIBRACION_GLENDA payslip inputs for all lines with sessions > 0.

        Business rules:
            - sessions == 0: remove any existing CALIBRACION_GLENDA input so the
              rule does not fire (keeps payslip clean).
            - sessions  > 0: upsert the CALIBRACION_GLENDA input; amount = sessions.
            - Only draft payslips are modified. If a payslip is already confirmed,
              raise UserError — HR must reset it to draft first.
        """
        self.ensure_one()

        confirmed_employees = []
        applied = 0

        for line in self.line_ids:
            slip = line.payslip_id
            if not slip or not slip.exists():
                continue

            if slip.state != 'draft':
                confirmed_employees.append(line.employee_id.name)
                continue

            # Find an existing CALIBRACION_GLENDA input on this payslip
            existing = slip.input_line_ids.filtered(
                lambda i: i.code == 'CALIBRACION_GLENDA'
            )

            if line.sessions > 0:
                if existing:
                    # Update in place — amount is the session count
                    existing[0].write({'amount': float(line.sessions)})
                else:
                    # Create new input record
                    self.env['hr.payslip.input'].create({
                        'payslip_id': slip.id,
                        'contract_id': slip.contract_id.id,
                        'name': 'Sesiones Calibración Glenda',
                        'code': 'CALIBRACION_GLENDA',
                        'amount': float(line.sessions),
                        'date_from': slip.date_from,
                        'date_to': slip.date_to,
                    })
                applied += 1
            else:
                # sessions == 0: remove existing input if any
                if existing:
                    existing.unlink()

        if confirmed_employees:
            names = ', '.join(confirmed_employees)
            raise UserError(_(
                "The following employees have already-confirmed payslips and were "
                "skipped. Reset them to Draft before applying calibration bonuses:\n%s"
            ) % names)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bonos Calibración Aplicados'),
                'message': _(
                    '%d payslip(s) updated with CALIBRACION_GLENDA input. '
                    'Recompute payslips to see the bonus line.'
                ) % applied,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_close(self):
        """Close the wizard without applying."""
        return {'type': 'ir.actions.act_window_close'}


class CalibracionBonusWizardLine(models.TransientModel):
    """One line per employee in the calibration bonus wizard."""

    _name = 'calibracion.bonus.wizard.line'
    _description = 'Calibración Bonus Wizard Line'
    _order = 'is_registered desc, employee_id'

    wizard_id = fields.Many2one(
        'calibracion.bonus.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True,
    )

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        readonly=True,
    )

    is_registered = fields.Boolean(
        string='Registered',
        readonly=True,
        help='Employee has an acknowledged glenda_calibracion_v1 notice.',
    )

    wa_number = fields.Char(
        string='WA Number',
        readonly=True,
        help='WhatsApp number from the calibration registration.',
    )

    ack_date = fields.Datetime(
        string='ACK Date',
        readonly=True,
        help='Date the employee acknowledged the Glenda calibration notice.',
    )

    sessions = fields.Integer(
        string='Sessions',
        default=0,
        help='Number of documented Glenda calibration sessions this period. '
             'Enter 0 to skip (no bonus). The bonus = sessions × (salary / 21.75).',
    )

    payslip_state = fields.Char(
        string='Payslip State',
        compute='_compute_payslip_state',
        help='Current state of the employee payslip in this batch.',
    )

    @api.depends('payslip_id.state')
    def _compute_payslip_state(self):
        state_labels = {
            'draft': 'Draft',
            'verify': 'Waiting',
            'done': 'Done',
            'cancel': 'Cancelled',
        }
        for line in self:
            if line.payslip_id:
                line.payslip_state = state_labels.get(
                    line.payslip_id.state, line.payslip_id.state
                )
            else:
                line.payslip_state = 'No Payslip'
