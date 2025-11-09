from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    commission_partner_id = fields.Many2one('res.partner', string='Commission')
    commission_line_ids = fields.One2many(
        'tdv.sale.commission.line', 'move_line_id', string='relation')

    @api.depends('commission_line_ids')
    def _compute_commission_line(self):
        for record in self:
            if record.commission_line_ids:
                record.commission_line_id = record.commission_line_ids[0]
            else:
                record.commission_line_id = False

    commission_line_id = fields.Many2one(
        'tdv.sale.commission.line', compute='_compute_commission_line',
        store=True
    )

    def create (self, vals):
        record = super().create(vals)
        if not record.commission_partner_id and record.move_id.invoice_user_id:
            invoice_user = record.move_id.invoice_user_id

            if invoice_user.has_commissions:
                record.commission_partner_id = invoice_user.partner_id

        return record


    def write(self, vals):
        result = super().write(vals)    
        for record in self:
            if not record.commission_partner_id and record.move_id.invoice_user_id:
                invoice_user = record.move_id.invoice_user_id

                if invoice_user.has_commissions:
                    record.commission_partner_id = invoice_user.partner_id
        return result 

    # def update_commission_partner(self):
    #     published_lines = self.search([('move_id.state', '=', 'posted')])

    #     for line in published_lines:
    #         if not line.commission_partner_id and line.move_id.invoice_user_id:
    #             invoice_user = line.move_id.invoice_user_id

    #             if invoice_user.has_commissions:
    #                 line.commission_partner_id = invoice_user

    #     return True
