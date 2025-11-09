from odoo import fields, api, models


class ResConfig(models.TransientModel):
    _inherit = "res.config.settings"

    # Diarios de retención de proveedores
    iva_retention_journal_id = fields.Many2one(
        related="company_id.iva_retention_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )
    islr_retention_journal_id = fields.Many2one(
        related="company_id.islr_retention_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )
    iae_retention_journal_id = fields.Many2one(
        related="company_id.iae_retention_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )

    # Diarios de retención de clientes
    iva_retention_customer_journal_id = fields.Many2one(
        related="company_id.iva_retention_customer_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )
    islr_retention_customer_journal_id = fields.Many2one(
        related="company_id.islr_retention_customer_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )
    iae_retention_customer_journal_id = fields.Many2one(
        related="company_id.iae_retention_customer_journal_id",
        domain="[('type','=','general')]",
        readonly=False,
    )

    # Cuentas de retención de proveedores
    iva_account_id = fields.Many2one(
        related="company_id.iva_account_id",
        readonly=False,
    )
    islr_account_id = fields.Many2one(
        related="company_id.islr_account_id",
        readonly=False,
    )
    iae_account_id = fields.Many2one(
        related="company_id.iae_account_id",
        readonly=False,
    )

    # Cuentas de retención de clientes
    iva_customer_account_id = fields.Many2one(
        related="company_id.iva_customer_account_id",
        readonly=False,
    )
    islr_customer_account_id = fields.Many2one(
        related="company_id.islr_customer_account_id",
        readonly=False,
    )
    iae_customer_account_id = fields.Many2one(
        related="company_id.iae_customer_account_id",
        readonly=False,
    )

    retention_signature = fields.Image(
        related="company_id.retention_signature", 
        readonly=False
    )
    active_retention_theoretical = fields.Boolean(
        related="company_id.active_retention_theoretical", 
        readonly=False
    )
