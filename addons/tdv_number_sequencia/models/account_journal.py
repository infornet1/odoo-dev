from odoo import models, fields, api, _

class AccountJournal(models.Model):
    _inherit = "account.journal"

    fiscal_number_sequence = fields.Char(
       string="Secuencia Número Fiscal",)    
   
    fiscal_control_number_sequence = fields.Char(
       string="Secuencia Número de Control",)    
   