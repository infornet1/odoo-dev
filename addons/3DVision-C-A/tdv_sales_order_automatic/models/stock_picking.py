from odoo import models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        auto_validate_invoice = (self.env["ir.config_parameter"].sudo()
            .get_param("automatic_invoice_and_post.is_create_invoice_delivery_validate"))
        auto_send_invoice = (self.env["ir.config_parameter"].sudo()
            .get_param("automatic_invoice_and_post.is_auto_send_invoice"))
        if auto_validate_invoice:
            if any(rec.product_id.invoice_policy == 'delivery' for rec in
                   self.move_ids) or not self.sale_id.invoice_ids:
                # Call the _create_invoices function on the associated sale
                # to create the invoice
                invoice_created = self.sale_id._create_invoices(
                    self.sale_id) if self.sale_id else False
                # Post the created invoice
                if invoice_created:
                    invoice_created.action_post()
                    # If automatic invoice sending is enabled and the customer
                    # has an email address,send the invoice to the customer
                    if auto_send_invoice and invoice_created.partner_id.email:
                        template = self.env.ref(
                            'account.email_template_edi_invoice').sudo()
                        template.send_mail(invoice_created.id, force_send=True,
                                           email_values={
                                               'email_to': invoice_created.partner_id.email
                                           })
        return res



