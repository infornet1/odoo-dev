from odoo import fields, api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Diarios de retención de proveedores
    iva_retention_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención IVA Proveedor",
        domain="[('type','=','general')]",
    )
    islr_retention_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención ISLR Proveedor",
        domain="[('type','=','general')]",
    )
    iae_retention_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención IAE Proveedor",
        domain="[('type','=','general')]",
    )

    # Diarios de retención de clientes
    iva_retention_customer_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención IVA Cliente",
        domain="[('type','=','general')]",
    )
    islr_retention_customer_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención ISLR Cliente",
        domain="[('type','=','general')]",
    )
    iae_retention_customer_journal_id = fields.Many2one(
        "account.journal",
        "Diario Retención IAE Cliente",
        domain="[('type','=','general')]",
    )

    # Cuentas de retención de proveedores
    iva_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención IVA Proveedor"
    )
    islr_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención ISLR Proveedor"
    )
    iae_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención IAE Proveedor"
    )

    # Cuentas de retención de clientes
    iva_customer_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención IVA Cliente"
    )
    islr_customer_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención ISLR Cliente"
    )
    iae_customer_account_id = fields.Many2one(
        "account.account", 
        "Cuenta Retención IAE Cliente"
    )

    retention_signature = fields.Image("Firma de Retención")
    active_retention_theoretical = fields.Boolean(
        "Activar teórico", default=False
    )

    def _get_retention_account_id(self, ret_type, retention_type='vendor'):
        ret_accounts = {
            'vendor': {
                "iva": self.iva_account_id,
                "islr": self.islr_account_id,
                "iae": self.iae_account_id,
            },
            'customer': {
                "iva": self.iva_customer_account_id,
                "islr": self.islr_customer_account_id,
                "iae": self.iae_customer_account_id,
            }
        }

        return ret_accounts[retention_type][ret_type]

    def _get_retention_journal_id(self, ret_type, retention_type='vendor'):
        retention_journals = {
            'vendor': {
                "iva": self.iva_retention_journal_id,
                "islr": self.islr_retention_journal_id,
                "iae": self.iae_retention_journal_id,
            },
            'customer': {
                "iva": self.iva_retention_customer_journal_id,
                "islr": self.islr_retention_customer_journal_id,
                "iae": self.iae_retention_customer_journal_id,
            }
        }

        return retention_journals[retention_type][ret_type]

    def _get_full_address(self):
        field_list = self._get_company_address_field_names()
        address_info = []

        for key in field_list:
            val = (
                self[key]
                if key not in ("state_id", "country_id")
                else self[key].name
            )
            address_info.append(val if val else "")

        return " ".join(address_info)
