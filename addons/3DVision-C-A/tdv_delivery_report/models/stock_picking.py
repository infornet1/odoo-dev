from odoo import models,fields

class Picking(models.Model):
    _inherit = 'stock.picking'

    enable_custom_delivery_print = fields.Boolean(
        related = "company_id.enable_custom_delivery_print",
    )

    chofer = fields.Many2one(
        comodel_name='res.partner',
        string='Chofer',
        help='Chofer que realiza la entrega',
        domain="[('category_id', '=', 'CHOFER')]",
    )

    vehiculo = fields.Many2one(
        comodel_name='vehicle',
        string='Vehículo',
        help='Vehículo utilizado para la entrega',
    )
    
    def action_print_delivery_report(self):
        return self.env.ref('tdv_delivery_report.action_custom_delivery_report').report_action(self)


