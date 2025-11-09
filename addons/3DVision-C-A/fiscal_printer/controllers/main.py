# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosController(http.Controller):
    @http.route("/fp3dv/get-invoices", auth="user", type="json")
    def get_invoices(self, debug=False, **kwargs):
        invoices = request.env["account.move"].tdv_fp_get_invoices(debug=debug)
        return invoices

    @http.route("/fp3dv/update-invoice", auth="user", type="json")
    def update_fiscal_invoice(self, invoice={}):
        move = None
        if invoice:
            move = request.env["account.move"].search(
                [("name", "like", invoice.get("name"))], limit=1
            )
            if move:
                move.update_fp_fiscal_info(
                    {
                        "ticket_ref": invoice.get("fiscalNumber"),
                        "cn_ticket_ref": invoice.get("creditNoteNumber"),
                        "num_report_z": invoice.get("zNumber"),
                        "fp_serial_num": invoice.get("machineSerial"),
                        "fp_serial_date": invoice.get("fiscalDate"),
                        "fp_state": "printed",
                    }
                )
                return {"message": "Se ha procesado con exito", "success": True}
            else:
                raise UserError("No se pudo encontrar el documento asociado")
        else:
            raise UserError("El formato recibido no es valido")

    @http.route('/fiscal_printer/print_invoice', type='json', auth='user')
    def print_invoice(self, invoice_id, invoice_data):
        """
        Print an invoice on the fiscal printer
        """
        try:
            # Get the printer record
            invoice = request.env['account.move'].browse(invoice_id)
            if not invoice.exists():
                return {'success': False, 'error': 'Factura no encontrada'}
            update_data = {}
            if "ticket_ref" in invoice_data:
                update_data["ticket_ref"] = invoice_data["ticket_ref"]
                update_data["fp_state"] = "printed"
            if "fp_serial_date" in invoice_data:
                update_data["fp_serial_date"] = invoice_data["fp_serial_date"]
            if "fp_serial_num" in invoice_data:
                update_data["fp_serial_num"] = invoice_data["fp_serial_num"]
            if "cn_ticket_ref" in invoice_data:
                update_data["cn_ticket_ref"] = invoice_data["cn_ticket_ref"]
                update_data["fp_state"] = "printed"
            if "num_report_z" in invoice_data:
                update_data["num_report_z"] = invoice_data["num_report_z"]
            invoice.write(update_data)

            return {
                'success': True,
                'message': 'Factura impresa exitosamente',
                'transaction_id': 'TXN_' + str(int(request.env['ir.sequence'].next_by_code('fiscal.printer.transaction')))
            }

        except Exception as e:
            _logger.error(f"Error printing invoice: {str(e)}")
            return {
                'success': False,
                'error': f'Error al imprimir factura: {str(e)}'
            }
