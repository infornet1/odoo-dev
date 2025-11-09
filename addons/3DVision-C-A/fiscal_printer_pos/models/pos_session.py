from odoo import models, fields
from datetime import datetime


class PosSession(models.Model):
    _inherit = "pos.session"

    x_pos_z_report_number = fields.Char("Número Reporte Z")

    # campo el reporte z desde pos.report.z
    pos_report_z_id = fields.Many2one("pos.report.z", "Reporte Z")

    def set_z_report(self, number):
        # buscar si existe un reporte z en pos.report.z con el mismo número
        z_report = self.env['pos.report.z'].sudo().search(
            [('number', '=', number)])
        if z_report:
            # agregar la sesión al campo pos_session_ids many2many
            z_report.write({"pos_session_ids": [(4, self.id)]})
            z_report._onchange_pos_session_ids()
            self.sudo().write(
                {"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
        else:
            # crear un reporte z con el número
            z_report = self.env['pos.report.z'].sudo().create({
                "number": number,
                'date': datetime.today(),
                'x_fiscal_printer_id': self.config_id.x_fiscal_printer_id.id,
                "pos_session_ids": [(4, self.id)],
            })
            z_report.sudo()._onchange_pos_session_ids()
            self.sudo().write(
                {"x_pos_z_report_number": number, 'pos_report_z_id': z_report.id})
            activity = {
                'res_id': z_report.id,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'pos.report.z')]).id,
                'user_id': self.env.user.id,
                'summary': 'Verificar reporte Z',
                'note': 'Verifica si existe otra sesión para este reporte Z y validar el reporte Z',
                'activity_type_id': 4,
                'date_deadline': datetime.today(),
            }

            self.env['mail.activity'].sudo().create(activity)

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields'].extend([
            "x_printer_code",
            "currency_rate",
        ])
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        result['search_params']['fields'].append('x_tipo_alicuota')
        return result

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'].extend(
            ['company_type', 'city', 'ced_rif'])
        return result

    def _pos_ui_models_to_load(self):
        result = super(PosSession, self)._pos_ui_models_to_load()
        result.append('res.city')
        return result

    def _loader_params_res_company(self):
        result = super(PosSession, self)._loader_params_res_company()
        result['search_params']['fields'].append('city')
        return result

    def _loader_params_res_city(self):
        return {"search_params": {"domain": [("country_id.code", "=", "VE")], "fields": ["name", "country_id", "state_id"]}}

    def _get_pos_ui_res_city(self, params):
        result = self.env['res.city'].search_read(**params['search_params'])
        return result
