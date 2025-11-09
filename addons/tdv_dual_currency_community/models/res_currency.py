# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'
    
    is_conversion_currency = fields.Boolean(
        string='Es Moneda de Conversión',
        compute='_compute_is_conversion_currency',
        store=False
    )
    
    def _compute_is_conversion_currency(self):
        """Determina si la moneda actual es la moneda de conversión configurada"""
        conversion_currency_id = self.env.company.currency_conversion_id.id
        for currency in self:
            currency.is_conversion_currency = (currency.id == conversion_currency_id)
    
    def action_open_update_wizard(self):
        """Abre el wizard para seleccionar estados de contrato a actualizar"""
        self.ensure_one()
        return {
            'name': _('Actualizar salarios en moneda secundaria'),
            'type': 'ir.actions.act_window',
            'res_model': 'currency.salary.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_currency_id': self.id,
            }
        }
    
    def _update_salaries_by_state(self, state_list):
        """
        Actualiza wage_in_ves según estados de contrato seleccionados
        :param state_list: lista de estados a filtrar (ej: ['draft', 'open'])
        """
        self.ensure_one()
        
        company = self.env.company
        if self.id != company.currency_conversion_id.id:
            raise UserError(_("Solo ejecutar en moneda de conversión configurada"))
        
        main_currency = company.currency_id
        
        if self == main_currency:
            raise UserError(_("La moneda de conversión no puede ser la principal"))
        
        currency_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.id),
            ('company_id', '=', company.id)
        ], order='name desc', limit=1)
        
        if not currency_rate:
            raise UserError(_("No existe tasa de cambio para esta moneda"))
        
        # Buscar contratos con los estados seleccionados
        contracts = self.env['hr.contract'].search([
            ('company_id', '=', company.id),
            ('state', 'in', state_list)
        ])
        
        if not contracts:
            raise UserError(_("No se encontraron contratos con los estados seleccionados"))
        
        updated_count = 0
        for contract in contracts:
            current_base_wage = contract.wage  # NO se modifica
            new_secondary_wage = current_base_wage * currency_rate.company_rate
            
            contract.write({'wage_in_ves': new_secondary_wage})
            updated_count += 1
            
            _logger.info(f"Contrato {contract.id} ({contract.state}): {current_base_wage} {main_currency.name} → {new_secondary_wage} {self.name}")
        
        return updated_count

    def action_open_update_payslip_rate_wizard(self):
        self.ensure_one()
        return {
            'name': 'Actualizar tasa de cambio en recibos de nómina',
            'type': 'ir.actions.act_window',
            'res_model': 'currency.payslip.update.rate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_currency_id': self.id,
            }
        }

class CurrencySalaryUpdateWizard(models.TransientModel):
    _name = 'currency.salary.update.wizard'
    _description = 'Asistente para actualizar salarios en moneda secundaria'
    
    currency_id = fields.Many2one('res.currency', string='Moneda de Conversión', required=True)
    update_draft = fields.Boolean(string='Contratos en Borrador', default=True)
    update_open = fields.Boolean(string='Contratos Activos', default=True)
    update_close = fields.Boolean(string='Contratos Cerrados', default=False)
    update_cancel = fields.Boolean(string='Contratos Cancelados', default=False)
    
    def action_update_salaries(self):
        self.ensure_one()
        
        # Mapear las selecciones a estados de contrato
        selected_states = []
        if self.update_draft:
            selected_states.append('draft')
        if self.update_open:
            selected_states.append('open')
        if self.update_close:
            selected_states.append('close')
        if self.update_cancel:
            selected_states.append('cancel')
        
        if not selected_states:
            raise UserError(_("Debe seleccionar al menos un estado de contrato"))
        
        # Llamar a la función de actualización
        updated_count = self.currency_id._update_salaries_by_state(selected_states)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualización completada'),
                'message': _('Se actualizaron %s contratos en los estados seleccionados.') % updated_count,
                'type': 'success',
                'sticky': False,
            }
        }

class CurrencyPayslipUpdateRateWizard(models.TransientModel):
    _name = 'currency.payslip.update.rate.wizard'
    _description = 'Actualizar tasa de cambio en recibos de nómina por lotes'

    currency_id = fields.Many2one('res.currency', string='Moneda', required=True)
    payslip_run_ids = fields.Many2many('hr.payslip.run', string='Lotes de Nómina')

    def action_update_rates(self):
        self.ensure_one()
        updated_count = 0
        for payslip_run in self.payslip_run_ids:
            payslips = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', payslip_run.id),
                ('conversion_currency_id', '=', self.currency_id.id)
            ])
            for payslip in payslips:
                # Forzar recálculo de la tasa de cambio
                payslip._compute_currency_rate_id()
                payslip._compute_exchange_rate()
                payslip.write({'exchange_rate': payslip.exchange_rate})
                updated_count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Actualización completada',
                'message': f'Se actualizaron {updated_count} recibos de nómina.',
                'type': 'success',
                'sticky': False,
            }
        }