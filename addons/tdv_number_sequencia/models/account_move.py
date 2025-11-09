from odoo import api, fields, models, _
from odoo.exceptions import UserError
import re
CUSTOMER_DOCUMENTS = ["out_invoice", "out_refund"]

class AccountMove(models.Model):
    _inherit = 'account.move'

    fiscal_check = fields.Boolean(string="Factura Fiscal", default=False)
    fiscal_correlative = fields.Char(string="Correlativo Fiscal", copy=False)
    control_number = fields.Char(string="Número de Control", copy=False)

# En models/account_move.py

    @api.onchange("fiscal_check")
    def onchange_fiscal_check(self):
        def get_next_sequence(sequence):
            if not sequence:
                return None
            flag = True
            sequence_elements = re.split(r"(\d+)", sequence)
            sequence_elements.reverse()
            new_sequence = []
            for element in sequence_elements:
                if flag and element.isdigit():
                    element_len = len(element)
                    next_val = str(int(element) + 1).zfill(element_len)
                    
                    # Si el número se desborda (ej: 99 -> 100), permite que crezca
                    if len(next_val) > element_len:
                        element = next_val
                    else:
                        element = next_val
                    flag = False
                new_sequence.append(element)
            new_sequence.reverse()
            return "".join(new_sequence)

        if self.fiscal_check and self.journal_id and not self.fp_serial_num:
            if self.move_type in CUSTOMER_DOCUMENTS:
                # --- LÓGICA CORREGIDA ---
                # Buscar la última factura fiscal CREADA para este diario.
                # Se ordena por fecha de creación descendente para obtener la más reciente.
                latest_move = self.env["account.move"].search([
                    ("fiscal_check", "=", True),
                    ("move_type", "=", self.move_type),
                    ("journal_id", "=", self.journal_id.id),
                    ("state", "in", ["posted", "draft"]), # Considerar solo facturas válidas
                    ("id", "!=", self._origin.id),
                ], order='create_date desc, id desc', limit=1)

                if latest_move:
                    # Si se encontró una factura reciente, continuar su secuencia
                    self.control_number = get_next_sequence(latest_move.control_number)
                    self.fiscal_correlative = get_next_sequence(latest_move.fiscal_correlative)
                else:
                    # Si no hay ninguna factura anterior, usar la secuencia del diario
                    self.control_number = self.journal_id.fiscal_control_number_sequence
                    self.fiscal_correlative = self.journal_id.fiscal_number_sequence
                # --- FIN DE LA LÓGICA CORREGIDA ---
        else:
            self.control_number = False
            self.fiscal_correlative = False